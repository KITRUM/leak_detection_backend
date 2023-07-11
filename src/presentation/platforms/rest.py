from fastapi import APIRouter, Request

__all__ = ("router",)

router = APIRouter(prefix="/platforms", tags=["Platforms"])


@router.get("")
def platforms_list(_: Request):
    """Provide the list platforms."""

    raise NotImplementedError
