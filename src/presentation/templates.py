from typing import AsyncGenerator

from fastapi import APIRouter, Request, status

from src.application.database import transaction
from src.domain.templates import (
    Template,
    TemplateCreateRequestBody,
    TemplatePublic,
    TemplatesRepository,
    TemplateUncommited,
)
from src.infrastructure.models import Response
from src.infrastructure.models.response import ResponseMulti

router = APIRouter(prefix="", tags=["Templates"])


@router.post(
    "/platforms/{platform_id}/templates", status_code=status.HTTP_201_CREATED
)
@transaction
async def template_create(
    _: Request, platform_id: int, schema: TemplateCreateRequestBody
) -> Response[TemplatePublic]:
    """Return the list of platforms that are provided."""

    # TODO: Move by building the request here.
    #       pydantic.validator should be used
    create_schema = TemplateUncommited.from_request(platform_id, schema)
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
async def template_retrieve(request: Request, template_id: int):
    """Return the list of sensors within the template."""

    template: Template = await TemplatesRepository().get(template_id)
    template_public = TemplatePublic(**template.dict())

    return Response[TemplatePublic](result=template_public)
