from fastapi import APIRouter, Request

from src.infrastructure.constants import DEFAULT_OPENAPI_RESPONSE

__all__ = ("router",)

router = APIRouter(prefix="/platforms", tags=["Platforms"])


@router.get("", responses={**DEFAULT_OPENAPI_RESPONSE})
def platforms_list(_: Request):
    """Provide the list platforms."""

    raise NotImplementedError
