import json
import pytest
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from app.core.errors import (
    error_handler,
    http_exception_handler,
    validation_exception_handler,
    error_response,
    ErrorCodes,
)
from app.core.logging import configure_logging, get_logger


@pytest.mark.asyncio
async def test_http_exception_handler_maps_codes():
    class FakeReq: ...

    for code, expected in [
        (status.HTTP_404_NOT_FOUND, ErrorCodes.RESOURCE_NOT_FOUND),
        (status.HTTP_401_UNAUTHORIZED, ErrorCodes.UNAUTHORIZED),
        (status.HTTP_403_FORBIDDEN, ErrorCodes.FORBIDDEN),
        (status.HTTP_409_CONFLICT, ErrorCodes.CONFLICT),
        (status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorCodes.VALIDATION_ERROR),
        (status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCodes.SERVER_ERROR),
    ]:
        res = await http_exception_handler(FakeReq(), HTTPException(status_code=code, detail="x"))
        payload = res.body.decode()
        data = json.loads(payload)
        assert data["error"]["code"] == expected


@pytest.mark.asyncio
async def test_error_handler_wraps_exception():
    class FakeReq: ...

    res = await error_handler(FakeReq(), Exception("boom"))
    data = json.loads(res.body.decode())
    assert data["error"]["code"] == ErrorCodes.SERVER_ERROR


@pytest.mark.asyncio
async def test_validation_exception_handler_formats_errors():
    class M(BaseModel):
        a: int

    try:
        M(a="bad")
    except ValidationError as ve:
        rve = RequestValidationError(ve.errors())
        res = await validation_exception_handler(object(), rve)
        body = json.loads(res.body.decode())
        assert body["error"]["code"] == ErrorCodes.VALIDATION_ERROR


def test_error_response_helper():
    res = error_response(418, ErrorCodes.SERVER_ERROR, "teapot", details={"x": 1})
    body = json.loads(res.body.decode())
    assert body["error"]["message"] == "teapot"


def test_configure_logging_and_get_logger():
    configure_logging()
    logger = get_logger("x")
    logger.debug("ok")
    assert logger.name == "x"
