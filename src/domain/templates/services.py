from src.infrastructure.database.services.transaction import transaction

from .repository import TemplatesRepository


@transaction
async def get_template_by_id(id_: int):
    """Get template from the database and close the session."""
    return await TemplatesRepository().get(template_id=id_)


@transaction
async def get_sensors_number(id_: int):
    """Get template's sensros number."""

    return TemplatesRepository().sensors_number(id_)
