from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel


class ErrorCodes:
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    SERVER_ERROR = "SERVER_ERROR"


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: dict | None = None


async def error_handler(_: Request, exc: Exception) -> JSONResponse:
    envelope = ErrorEnvelope(code=ErrorCodes.SERVER_ERROR, message=str(exc))
    return JSONResponse(status_code=500, content={"error": envelope.model_dump()})


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    code = ErrorCodes.SERVER_ERROR
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = ErrorCodes.RESOURCE_NOT_FOUND
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = ErrorCodes.UNAUTHORIZED
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = ErrorCodes.FORBIDDEN
    elif exc.status_code == status.HTTP_409_CONFLICT:
        code = ErrorCodes.CONFLICT
    elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        code = ErrorCodes.VALIDATION_ERROR
    env = ErrorEnvelope(code=code, message=str(exc.detail) if exc.detail else "Error", details=None)
    headers = getattr(exc, "headers", None)
    return JSONResponse(status_code=exc.status_code, headers=headers, content={"error": env.model_dump()})


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    env = ErrorEnvelope(code=ErrorCodes.VALIDATION_ERROR, message="Validation error", details={"errors": exc.errors()})
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"error": env.model_dump()})


def error_response(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": ErrorEnvelope(code=code, message=message, details=details).model_dump()})
