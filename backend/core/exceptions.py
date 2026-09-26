from typing import Any


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500, code: str = "internal_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class BadRequestError(AppError):
    def __init__(self, message: str, code: str = "bad_request"):
        super().__init__(message=message, status_code=400, code=code)


class NotFoundError(AppError):
    def __init__(self, message: str, code: str = "not_found"):
        super().__init__(message=message, status_code=404, code=code)


class ValidationError(AppError):
    def __init__(self, message: str, code: str = "validation_error"):
        super().__init__(message=message, status_code=422, code=code)


class DependencyError(AppError):
    def __init__(self, message: str, code: str = "dependency_error"):
        super().__init__(message=message, status_code=503, code=code)


def error_payload(error: AppError) -> dict[str, Any]:
    return {
        "error": {
            "code": error.code,
            "message": error.message,
        }
    }
