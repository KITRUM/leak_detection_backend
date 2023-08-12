from typing import Any

from src.infrastructure.contracts import ErrorResponseMulti, _Response

__all__ = ("DEFAULT_OPENAPI_RESPONSE",)


# NOTE: This constant represents the default error response for each request
#       Uses only for OpenAPI
__DEFAULT_ERROR_RESPONSE_MULTI: dict[str, Any] = {"model": ErrorResponseMulti}

DEFAULT_OPENAPI_RESPONSE: _Response = {
    500: __DEFAULT_ERROR_RESPONSE_MULTI,
    400: __DEFAULT_ERROR_RESPONSE_MULTI,
    422: __DEFAULT_ERROR_RESPONSE_MULTI,
    404: __DEFAULT_ERROR_RESPONSE_MULTI,
}
