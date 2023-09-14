"""
This module includes the router that is used by all submodules in this folder.
The router variable is used by factory in order to specify the root router.
"""

from fastapi import APIRouter

__all__ = ("router",)

router = APIRouter(prefix="/events")
