from src.infrastructure.database.services.transaction import transaction

from .models import Template, TemplatePartialUpdateSchema
from .repository import TemplatesRepository


@transaction
async def get_template_by_id(id_: int):
    """Get template from the database and close the session."""
    return await TemplatesRepository().get(template_id=id_)


@transaction
async def update(
    template_id: int, schema: TemplatePartialUpdateSchema
) -> Template:
    """Partially update the template."""

    return await TemplatesRepository().update_partially(template_id, schema)
