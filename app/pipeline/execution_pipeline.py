from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from app.constants.tool_risk import ToolRisk, risk_for_tool
from app.exceptions.app_errors import AntiHallucinationError, ValidationError
from app.elicitation.fallback import create_fallback_response
from app.validators.validate import validate_input

if TYPE_CHECKING:
    from app.audit.audit_logger import AuditLogger
    from app.resources.resource_manager import ResourceManager
    from app.services.elicitation_service import ElicitationService
    from app.services.workflow_state_store import WorkflowStateStore
    from app.tools.definition import ToolDefinition


def _extract_missing_fields(issues: list[dict]) -> list[str]:
    fields: list[str] = []
    for issue in issues:
        is_missing = issue.get("code") in ("missing", "invalid_type") and (
            issue.get("received") == "undefined" or issue.get("input") is None
        )
        if not is_missing:
            continue
        path = issue.get("path", "")
        fields.extend(_expand_required_path(path.split(".") if path else []))
    return list(dict.fromkeys(fields))


def _expand_required_path(path: list[str]) -> list[str]:
    joined = ".".join(path)
    if joined in ("from_address", "to_address", "address"):
        return [f"{joined}.{f}" for f in ("street1", "city", "state", "zip", "country")]
    if joined == "parcel":
        return [f"parcel.{f}" for f in ("length", "width", "height", "weight")]
    if not joined:
        return []
    return [joined]


def _set_path(input_data: dict, path: str, value: Any) -> dict:
    output = copy.deepcopy(input_data or {})
    parts = str(path).split(".")
    target = output
    for part in parts[:-1]:
        if not isinstance(target.get(part), dict):
            target[part] = {}
        target = target[part]
    target[parts[-1]] = value
    return output


def _strip_workflow_id(input_data: dict) -> dict:
    if not isinstance(input_data, dict):
        return input_data
    return {k: v for k, v in input_data.items() if k != "workflow_id"}


class ExecutionPipeline:
    def __init__(
        self,
        *,
        resource_manager: "ResourceManager | None" = None,
        elicitation_service: "ElicitationService | None" = None,
        workflow_state: "WorkflowStateStore | None" = None,
        audit_logger: "AuditLogger",
    ) -> None:
        self._resource_manager = resource_manager
        self._elicitation = elicitation_service
        self._workflow_state = workflow_state
        self._audit_logger = audit_logger

    async def run(self, tool: "ToolDefinition", args: dict, context: dict) -> dict[str, Any]:
        risk = tool.risk or risk_for_tool(tool.name)
        self._audit_logger.record("intent_extracted", {
            "correlation_id": context.get("correlation_id"),
            "tool_name": tool.name,
            "risk": risk,
        })

        if self._resource_manager:
            await self._resource_manager.ensure_fresh(context)

        original_args = args or {}
        workflow_id = original_args.get("workflow_id")
        merged_args = self._workflow_state.merge(workflow_id, original_args) if self._workflow_state else original_args

        result = await self._validate_or_elicit(tool, merged_args, {**context, "risk": risk, "workflow_id": workflow_id})

        if isinstance(result, dict) and "_elicitation_fallback" in result:
            return result["_elicitation_fallback"]

        self._audit_logger.record("validation_succeeded", {
            "correlation_id": context.get("correlation_id"),
            "tool_name": tool.name,
            "risk": risk,
        })

        if risk == ToolRisk.HIGH:
            confirm = result.confirm if hasattr(result, "confirm") else (result or {}).get("confirm")
            if confirm is not True:
                self._audit_logger.record("confirmation_missing", {
                    "correlation_id": context.get("correlation_id"),
                    "tool_name": tool.name,
                })

        final_context = {
            **context,
            "risk": risk,
            "resources": self._resource_manager,
            "elicitation": self._elicitation,
            "audit": self._audit_logger,
        }
        outcome = await tool.handler(result, final_context)

        self._audit_logger.record("execution_completed", {
            "correlation_id": context.get("correlation_id"),
            "tool_name": tool.name,
            "risk": risk,
            "ok": isinstance(outcome, dict) and outcome.get("ok") is True,
        })
        return outcome

    async def _validate_or_elicit(self, tool: "ToolDefinition", args: dict, context: dict) -> Any:
        stripped_args = _strip_workflow_id(args)
        try:
            return validate_input(
                tool.schema_cls,
                stripped_args,
                resource_manager=self._resource_manager,
                tool_name=tool.name,
                risk=context.get("risk"),
            )
        except ValidationError as exc:
            return await self._handle_validation_failure(tool, args, stripped_args, context, exc)
        except AntiHallucinationError as exc:
            return await self._handle_ambiguity_failure(tool, args, stripped_args, context, exc)

    async def _handle_validation_failure(
        self,
        tool: "ToolDefinition",
        args: dict,
        stripped_args: dict,
        context: dict,
        error: ValidationError,
    ) -> Any:
        missing_fields = _extract_missing_fields(error.details or [])
        if not missing_fields:
            raise error

        workflow_id = context.get("workflow_id")
        if not workflow_id and self._workflow_state:
            workflow_id = self._workflow_state.create(
                tool_name=tool.name,
                input=stripped_args,
                reason="MISSING_FIELDS",
                correlation_id=context.get("correlation_id"),
            )

        self._audit_logger.record("missing_fields_detected", {
            "correlation_id": context.get("correlation_id"),
            "tool_name": tool.name,
            "missing_fields": missing_fields,
            "workflow_id": workflow_id,
        })

        elicited = None
        if self._elicitation:
            elicited = await self._elicitation.request_missing_fields(
                server=context.get("server"),
                tool_name=tool.name,
                missing_fields=missing_fields,
                partial_input=stripped_args,
            )

        if elicited and elicited.get("completed"):
            if workflow_id and self._workflow_state:
                self._workflow_state.update(workflow_id, elicited["input"])
            return await self._validate_or_elicit(tool, elicited["input"], {**context, "workflow_id": workflow_id})

        return {
            "_elicitation_fallback": create_fallback_response(
                error_code="MISSING_REQUIRED_FIELDS",
                message="Required fields are missing. Provide only the missing fields and retry with workflow_id to resume.",
                missing_fields=missing_fields,
                workflow_id=workflow_id,
                next_action="Provide missing_fields and include workflow_id in the next call, or use a client that supports elicitation.form.",
            )
        }

    async def _handle_ambiguity_failure(
        self,
        tool: "ToolDefinition",
        args: dict,
        stripped_args: dict,
        context: dict,
        error: AntiHallucinationError,
    ) -> Any:
        details = error.details or {}
        ambiguous_fields = [
            {
                "path": issue["path"],
                "code": issue["code"],
                "message": issue["message"],
                "suggestions": issue.get("suggestions", []),
            }
            for issue in (details.get("issues") or [])
            if issue.get("suggestions")
        ]
        if not ambiguous_fields:
            raise error

        workflow_id = context.get("workflow_id")
        if not workflow_id and self._workflow_state:
            workflow_id = self._workflow_state.create(
                tool_name=tool.name,
                input=stripped_args,
                reason="AMBIGUOUS_FIELDS",
                correlation_id=context.get("correlation_id"),
            )

        first = ambiguous_fields[0]
        self._audit_logger.record("ambiguity_detected", {
            "correlation_id": context.get("correlation_id"),
            "tool_name": tool.name,
            "ambiguous_fields": ambiguous_fields,
            "workflow_id": workflow_id,
        })

        clarified = None
        if self._elicitation:
            clarified = await self._elicitation.clarify(
                server=context.get("server"),
                field=first["path"],
                suggestions=first["suggestions"],
                message=first["message"] or f"Clarify {first['path']}",
            )

        if clarified and clarified.get("selected"):
            clarified_input = _set_path(stripped_args, first["path"], clarified["value"])
            if workflow_id and self._workflow_state:
                self._workflow_state.update(workflow_id, clarified_input)
            return await self._validate_or_elicit(tool, clarified_input, {**context, "workflow_id": workflow_id})

        return {
            "_elicitation_fallback": create_fallback_response(
                error_code="AMBIGUOUS_OR_UNSUPPORTED_VALUES",
                message="One or more values are ambiguous or unsupported. Choose an exact suggested value or provide a different exact value.",
                ambiguous_fields=ambiguous_fields,
                available_options=[s for f in ambiguous_fields for s in (f.get("suggestions") or [])],
                workflow_id=workflow_id,
                next_action="Confirm one suggestion explicitly and include workflow_id in the next call, or use a client that supports elicitation.form.",
            )
        }
