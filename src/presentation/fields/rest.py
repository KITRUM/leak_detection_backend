from fastapi import APIRouter, Request

__all__ = ("router",)

router = APIRouter(prefix="/fields", tags=["Fields"])


@router.get("")
def fields_list(_: Request):
    """Provide the list fields."""

    raise NotImplementedError
