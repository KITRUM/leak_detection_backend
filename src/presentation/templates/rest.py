from typing import AsyncGenerator

from fastapi import APIRouter, Request, status

from src.domain.templates import (
    Template,
    TemplatePartialUpdateSchema,
    TemplatesRepository,
    TemplateUncommited,
)
from src.domain.templates import services as templates_services
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.database import transaction

from .contracts import (
    TemplateCreateRequestBody,
    TemplatePublic,
    TemplateUpdateRequestBody,
)

router = APIRouter(prefix="", tags=["Templates"])


@router.post(
    "/platforms/{platform_id}/templates", status_code=status.HTTP_201_CREATED
)
@transaction
async def template_create(
    _: Request, platform_id: int, schema: TemplateCreateRequestBody
) -> Response[TemplatePublic]:
    """Return the list of platforms that are provided."""

    create_schema: TemplateUncommited = schema.build_template_uncommited(
        platform_id
    )
    template: Template = await TemplatesRepository().create(create_schema)
    template_public = TemplatePublic(**template.dict())

    return Response[TemplatePublic](result=template_public)


@router.get("/platforms/{platform_id}/templates")
@transaction
async def templates_list(
    _: Request, platform_id: int
) -> ResponseMulti[TemplatePublic]:
    """Return the list of platforms that are provided."""

    templates: AsyncGenerator[
        Template, None
    ] = TemplatesRepository().by_platform(platform_id)

    templates_public = [
        TemplatePublic(**template.dict()) async for template in templates
    ]

    return ResponseMulti[TemplatePublic](result=templates_public)


@router.get("/templates/{template_id}")
@transaction
async def template_retrieve(_: Request, template_id: int):
    """Return the list of sensors within the template."""

    template: Template = await TemplatesRepository().get(template_id)
    template_public = TemplatePublic(**template.dict())

    return Response[TemplatePublic](result=template_public)


@router.patch("/templates/{template_id}")
async def template_update(
    _: Request, template_id: int, schema: TemplateUpdateRequestBody
):
    """Partial update of a template."""

    template: Template = await templates_services.update(
        template_id, TemplatePartialUpdateSchema(**schema.dict())
    )
    template_public = TemplatePublic(**template.dict())

    return Response[TemplatePublic](result=template_public)


@router.delete("/templates/{template_id}")
async def template_delete(_: Request, template_id: int):
    """Delete a template."""

    raise NotImplementedError
