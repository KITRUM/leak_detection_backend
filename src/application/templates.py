from src.domain.templates import (
    Template,
    TemplatePartialUpdateSchema,
    TemplatesRepository,
    TemplateUncommited,
)
from src.infrastructure.database import transaction

__all__ = ("get_by_id", "update", "create", "retrieve_by_field_id")


@transaction
async def get_by_id(id_: int):
    """Get template from the database and close the session."""
    return await TemplatesRepository().get(template_id=id_)


@transaction
async def update(
    template_id: int, schema: TemplatePartialUpdateSchema
) -> Template:
    """Partially update the template."""

    return await TemplatesRepository().update_partially(template_id, schema)


@transaction
async def create(schema: TemplateUncommited) -> Template:
    """Create a new database record."""

    return await TemplatesRepository().create(schema)


@transaction
async def retrieve_by_field_id(field_id: int) -> list[Template]:
    """Retrieve the template by field id."""

    return [
        template async for template in TemplatesRepository().by_field(field_id)
    ]
