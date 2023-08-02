from dataclasses import dataclass
from typing import Any, Protocol, Type

from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Receive, Scope, Send


class _HttpMiddleware(Protocol):
    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        ...


@dataclass
class Middleware:
    class_: Type[_HttpMiddleware]
    payload: dict[str, Any]


# TODO: Move origins and methods to the settings
cors = Middleware(
    class_=CORSMiddleware,
    payload={
        "allow_origins": [
            "http://localhost",
            "http://localhost:5173",
        ],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    },
)
