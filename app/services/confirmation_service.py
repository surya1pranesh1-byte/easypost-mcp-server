from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.exceptions.app_errors import ConfirmationRequiredError

if TYPE_CHECKING:
    from app.services.elicitation_service import ElicitationService


class ConfirmationService:
    async def require_confirmed(
        self,
        input_data: Any,
        *,
        action: str,
        message: str,
        details: dict | None = None,
        typed_confirmation: str | None = None,
        context: dict | None = None,
    ) -> None:
        ctx = context or {}

        confirm_value = (
            input_data.get("confirm") if isinstance(input_data, dict)
            else getattr(input_data, "confirm", None)
        )
        if confirm_value is True:
            return

        elicitation: ElicitationService | None = ctx.get("elicitation")
        if elicitation:
            elicited = await elicitation.confirm(
                server=ctx.get("server"),
                message=message,
                title="Confirm operation",
                description="Required before this high-risk operation can continue.",
                typed_confirmation=typed_confirmation,
            )
            if elicited.get("confirmed"):
                if isinstance(input_data, dict):
                    input_data["confirm"] = True
                else:
                    try:
                        object.__setattr__(input_data, "confirm", True)
                    except (AttributeError, TypeError):
                        pass
                audit = ctx.get("audit")
                if audit:
                    audit.record("confirmation_elicited", {
                        "correlation_id": ctx.get("correlation_id"),
                        "action": action,
                    })
                return

        raise ConfirmationRequiredError(action=action, message=message, details=details)
