from typing import Any, AsyncGenerator, Generic, Type

from sqlalchemy import Result, asc, delete, desc, func, select, update
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.services.session import CTX_SESSION
from src.infrastructure.database.tables import ConcreteTable
from src.infrastructure.errors import (
    DatabaseError,
    NotFoundError,
    UnprocessableError,
)

__all__ = ("BaseRepository", "Session")


class Session:
    # All sqlalchemy errors that can be raised
    _ERRORS = (IntegrityError, PendingRollbackError)

    def __init__(self) -> None:
        self._session: AsyncSession = CTX_SESSION.get()

    async def execute(self, query) -> Result:
        try:
            result = await self._session.execute(query)
            return result
        except self._ERRORS:
            raise DatabaseError


# Mypy error: https://github.com/python/mypy/issues/13755
class BaseRepository(Session, Generic[ConcreteTable]):  # type: ignore
    schema_class: Type[ConcreteTable]

    def __init__(self) -> None:
        super().__init__()

        if not self.schema_class:
            raise UnprocessableError(
                message=(
                    "Can not initiate the class without schema_class attribute"
                )
            )

    async def _update(
        self, key: str, value: Any, payload: dict[str, Any]
    ) -> ConcreteTable:
        """Updates an existed instance of the model in the related table.
        If some data is not exist in the payload then the null value will
        be passed to the schema class."""

        query = (
            update(self.schema_class)
            .where(getattr(self.schema_class, key) == value)
            .values(payload)
            .returning(self.schema_class)
        )
        result: Result = await self.execute(query)
        await self._session.flush()

        if not (schema := result.scalar_one_or_none()):
            raise DatabaseError

        return schema

    async def _get(self, key: str, value: Any) -> ConcreteTable:
        """Return only one result by filters"""

        query = select(self.schema_class).where(
            getattr(self.schema_class, key) == value
        )
        result: Result = await self.execute(query)

        if not (_result := result.scalars().one_or_none()):
            raise NotFoundError

        return _result

    async def count(self) -> int:
        result: Result = await self.execute(func.count(self.schema_class.id))
        value = result.scalar()

        if not isinstance(value, int):
            raise UnprocessableError(
                message=(
                    "For some reason count function returned not an integer."
                    f"Value: {value}"
                ),
            )

        return value

    async def _first(self, by: str = "id") -> ConcreteTable:
        result: Result = await self.execute(
            select(self.schema_class).order_by(asc(by)).limit(1)
        )

        if not (_result := result.scalar_one_or_none()):
            raise NotFoundError

        return _result

    async def _last(self, by: str = "id") -> ConcreteTable:
        result: Result = await self.execute(
            select(self.schema_class).order_by(desc(by)).limit(1)
        )

        if not (_result := result.scalar_one_or_none()):
            raise NotFoundError

        return _result

    async def _save(self, schema: ConcreteTable) -> ConcreteTable:
        try:
            self._session.add(schema)
            await self._session.flush()
            await self._session.refresh(schema)
            return schema
        except self._ERRORS:
            raise DatabaseError

    async def _all(self) -> AsyncGenerator[ConcreteTable, None]:
        result: Result = await self.execute(select(self.schema_class))
        schemas = result.scalars().all()

        for schema in schemas:
            yield schema

    async def delete(self, id_: int) -> None:
        await self.execute(
            delete(self.schema_class).where(self.schema_class.id == id_)
        )
        await self._session.flush()
