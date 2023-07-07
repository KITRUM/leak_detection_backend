from typing import AsyncGenerator

from sqlalchemy import Result, Select, select

from src.domain.templates.models import Template, TemplateUncommited
from src.infrastructure.database import BaseRepository, TemplatesTable
from src.infrastructure.errors import NotFoundError

all = ("TemplatesRepository",)


class TemplatesRepository(BaseRepository[TemplatesTable]):
    schema_class = TemplatesTable

    async def create(self, schema: TemplateUncommited) -> Template:
        """Create a new record in database."""

        _schema: TemplatesTable = await self._save(
            TemplatesTable(**schema.dict())
        )
        return Template.from_orm(_schema)

    async def all(self) -> AsyncGenerator[Template, None]:
        """Fetch all templates from database."""
        async for schema in self._all():
            yield Template.from_orm(schema)

    async def by_platform(
        self, platform_id: int
    ) -> AsyncGenerator[Template, None]:
        """Fetch all templates by platform from database."""

        query: Select = select(self.schema_class).where(
            getattr(self.schema_class, "platform_id") == platform_id
        )
        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield Template.from_orm(schema)

    async def get(self, template_id: int) -> Template:
        """Fetch all templates by platform from database."""

        schema = await self._get("id", template_id)
        return Template.from_orm(schema)
