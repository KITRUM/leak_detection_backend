import asyncio
from functools import partial
from typing import Callable, Coroutine, Iterable

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.infrastructure.application import middlewares
from src.infrastructure.errors import (
    BaseError,
    custom_base_errors_handler,
    not_implemented_errors_handler,
    pydantic_validation_errors_handler,
    python_base_error_handler,
)

__all__ = ("create",)


def create(
    *_,
    routers: Iterable[APIRouter],
    middlewares: Iterable[middlewares.Middleware],
    startup_tasks: Iterable[Callable[[], Coroutine]],
    shutdown_tasks: Iterable[Callable[[], Coroutine]],
    **kwargs,
) -> FastAPI:
    """The FastAPI application factory.
    🎉 Only passing routes is mandatory to start.
    """

    # Initialize the base FastAPI application
    # -----------------------------------------------
    app = FastAPI(**kwargs)

    # Include routers
    # -----------------------------------------------
    for router in routers:
        app.include_router(router)

    # Define error handlers
    # -----------------------------------------------
    app.exception_handler(RequestValidationError)(
        pydantic_validation_errors_handler
    )
    app.exception_handler(BaseError)(custom_base_errors_handler)
    app.exception_handler(ValidationError)(pydantic_validation_errors_handler)
    app.exception_handler(NotImplementedError)(not_implemented_errors_handler)
    app.exception_handler(Exception)(python_base_error_handler)

    # Define startup tasks
    # -----------------------------------------------
    for task in startup_tasks:
        app.on_event("startup")(partial(asyncio.create_task, task()))

    # Define shutdown tasks
    # -----------------------------------------------
    for task in shutdown_tasks:
        app.on_event("shutdown")(partial(asyncio.create_task, task()))

    # Define middlewares
    # -----------------------------------------------
    for middleware in middlewares:
        app.add_middleware(
            middleware_class=middleware.class_,
            **middleware.payload,
        )

    return app
