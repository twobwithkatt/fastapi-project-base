from typing import Any, TypeVar, Generic, Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")

class CustomResponse(GenericModel, Generic[T]):
    success: bool
    code: int
    error: Optional[str] = None
    data: Optional[T] = None


def ok_response(data: Any = None, code: int = 0):
    return CustomResponse(success=True, code=code, data=data)


def error_response(message: str, code: int = 400):
    return CustomResponse(success=False, code=code, error=message)


def internal_error_response(message: str = "Internal Server Error", code: int = 500):
    return CustomResponse(success=False, code=code, error=message)


def custom_json_response(
    success: bool,
    code: int,
    data: Any = None,
    error: Optional[str] = None,
    status_code: Optional[int] = None
):
    response = CustomResponse(
        success=success,
        code=code,
        data=data,
        error=error
    )
    return JSONResponse(
        status_code=status_code or code,
        content=response.dict()
    )