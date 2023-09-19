from fastapi import APIRouter, Request, status

from src.application import templates
from src.domain.templates import Template, TemplatePartialUpdateSchema
from src.infrastructure.contracts import Response, ResponseMulti

from .contracts import (
    TemplateCreateRequestBody,
    TemplatePublic,
    TemplateUpdateRequestBody,
)

router = APIRouter(prefix="", tags=["Templates"])


@router.post(
    "/fields/{field_id}/templates", status_code=status.HTTP_201_CREATED
)
async def template_create(
    _: Request, field_id: int, schema: TemplateCreateRequestBody
) -> Response[TemplatePublic]:
    """Template creation within the field."""

    template: Template = await templates.create(
        schema.build_template_uncommited(field_id)
    )
    template_public = TemplatePublic(**template.dict())

    return Response[TemplatePublic](result=template_public)


@router.get("/fields/{field_id}/templates")
async def templates_list(
    _: Request, field_id: int
) -> ResponseMulti[TemplatePublic]:
    """Return the list of templates within the field."""

    templates_internal: list[Template] = await templates.retrieve_by_field_id(
        field_id
    )

    templates_public = [
        TemplatePublic(**template.dict()) for template in templates_internal
    ]

    return ResponseMulti[TemplatePublic](result=templates_public)


@router.get("/templates/{template_id}")
async def template_retrieve(_: Request, template_id: int):
    """Return the list of sensors within the template."""

    template: Template = await templates.get_by_id(template_id)
    template_public = TemplatePublic(**template.dict())

    return Response[TemplatePublic](result=template_public)


@router.patch("/templates/{template_id}")
async def template_update(
    _: Request, template_id: int, schema: TemplateUpdateRequestBody
):
    """Partial update of a template."""

    template: Template = await templates.update(
        template_id, TemplatePartialUpdateSchema(**schema.dict())
    )
    template_public = TemplatePublic(**template.dict())

    return Response[TemplatePublic](result=template_public)


@router.delete("/templates/{template_id}")
async def template_delete(_: Request, template_id: int):
    """Delete a template."""

    raise NotImplementedError
