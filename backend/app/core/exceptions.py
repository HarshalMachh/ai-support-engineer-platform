class AppError(Exception):
    """Base class for expected, user-facing errors raised by the service layer."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "forbidden"


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthorized"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_error"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
