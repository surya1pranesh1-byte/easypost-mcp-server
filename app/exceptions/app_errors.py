from __future__ import annotations


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: dict | None = None,
        retryable: bool = False,
        safe_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.details = details
        self.retryable = retryable
        self.safe_message = safe_message or message


class ValidationError(AppError):
    def __init__(self, message: str, details: list | dict | None = None) -> None:
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
            safe_message="Input validation failed",
        )


class AntiHallucinationError(AppError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(
            message,
            code="SUSPICIOUS_INPUT",
            status_code=400,
            details=details,
            safe_message=message,
        )


class ExternalServiceError(AppError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "EASYPOST_ERROR",
        status_code: int = 502,
        details: dict | None = None,
        retryable: bool = False,
        safe_message: str | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            status_code=status_code,
            details=details,
            retryable=retryable,
            safe_message=safe_message or "Shipping provider request failed",
        )


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            f"{resource} not found",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": resource_id},
        )


class ConfirmationRequiredError(AppError):
    def __init__(self, *, action: str, message: str, details: dict | None = None) -> None:
        super().__init__(
            message,
            code="CONFIRMATION_REQUIRED",
            status_code=409,
            details={
                "action": action,
                "confirmation_required": True,
                "confirmation_field": "confirm",
                "expected_value": True,
                **(details or {}),
            },
            safe_message=message,
        )


class RateLimitError(AppError):
    def __init__(self, reset_at: str) -> None:
        super().__init__(
            "MCP rate limit exceeded",
            code="RATE_LIMITED",
            status_code=429,
            retryable=True,
            details={"reset_at": reset_at},
        )


class UnknownToolError(AppError):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Unknown tool: {name}",
            code="UNKNOWN_TOOL",
            status_code=404,
            safe_message=f"Unknown tool: {name}",
        )
