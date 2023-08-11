from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

from src.infrastructure.contracts import ErrorResponse, ErrorResponseMulti
from src.infrastructure.errors.base import BaseError

__all__ = (
    "not_implemented_errors_handler",
    "custom_base_errors_handler",
    "python_base_error_handler",
    "pydantic_validation_errors_handler",
)


def not_implemented_errors_handler(
    _: Request, error: NotImplementedError
) -> JSONResponse:
    response = ErrorResponseMulti(
        results=[
            ErrorResponse(message="Currently this feature is not available")
        ]
    )

    return JSONResponse(response.dict(by_alias=True), status_code=500)


def custom_base_errors_handler(_: Request, error: BaseError) -> JSONResponse:
    response = ErrorResponseMulti(
        results=[ErrorResponse(message=error.message.capitalize())]
    )

    return JSONResponse(
        response.dict(by_alias=True),
        status_code=error.status_code,
    )


def python_base_error_handler(_: Request, error: Exception) -> JSONResponse:
    response = ErrorResponseMulti(
        results=[ErrorResponse(message=f"Unhandled error: {error}")]
    )

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)), status_code=500
    )


def pydantic_validation_errors_handler(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    """This function is called if the Pydantic validation error was raised."""

    response = ErrorResponseMulti(
        results=[
            ErrorResponse(
                message=err["msg"],
                path=list(err["loc"]),
            )
            for err in error.errors()
        ]
    )

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)), status_code=422
    )
