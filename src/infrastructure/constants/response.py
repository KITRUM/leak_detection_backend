from typing import Any

from starlette import status

from src.infrastructure.contracts import ErrorResponseMulti, _Response

# NOTE: This constant represents the default error response for each request
#       Uses only for OpenAPI
__DEFAULT_ERROR_RESPONSE: dict[str, Any] = {"model": ErrorResponseMulti}

NO_CONTENT_ERROR_RESPONSES: _Response = {
    status.HTTP_404_NOT_FOUND: {},
}
DEFAULT_OPENAPI_RESPONSE: _Response = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: __DEFAULT_ERROR_RESPONSE,
    status.HTTP_400_BAD_REQUEST: __DEFAULT_ERROR_RESPONSE,
    status.HTTP_422_UNPROCESSABLE_ENTITY: {},
}
