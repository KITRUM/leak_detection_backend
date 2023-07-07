from fastapi import Request

from src.presentation.routers import platforms as router


@router.get("")
def platforms_list(request: Request):
    """Provide the list platforms."""

    raise NotImplementedError
