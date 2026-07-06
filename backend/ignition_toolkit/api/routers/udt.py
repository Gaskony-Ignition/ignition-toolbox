"""
UDT Builder API Router

Turns a device-class questionnaire (template metadata from
``ignition_toolkit.udt.builder.list_templates``) plus a user's answers into a
convention-conforming UDT type definition, returned as plain tag-export JSON
for the frontend to preview and download.

DELIVERY: download-JSON-only (Nigel-ratified 2026-07-06, see
``docs/plans/udt-builder-design.md``). Nothing here writes to disk or pushes
to a gateway — the response body *is* the deliverable; the frontend triggers
a browser download of it.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ignition_toolkit.udt.builder import TemplateMeta, UdtBuilderError, build, list_templates
from ignition_toolkit.udt.models import to_tag_export

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/udt", tags=["udt"])


# ============================================================================
# Response / request models
# ============================================================================


class QuestionnaireFieldSchema(BaseModel):
    """One entry in a template's questionnaire, mirroring ``builder.QuestionnaireField``."""

    name: str
    type: str
    required: bool
    default: Any = None
    description: str


class TemplateMetaSchema(BaseModel):
    """Template metadata + questionnaire schema, for the frontend's template picker + form."""

    id: str
    label: str
    description: str
    questionnaire: list[QuestionnaireFieldSchema]
    naming_styles: list[str]
    default_naming_style: str


class UdtBuildRequest(BaseModel):
    """Request body for ``POST /api/udt/build``."""

    template_id: str
    answers: dict[str, Any] = Field(default_factory=dict)
    naming_style: str | None = Field(
        default=None,
        description="One of the template's naming_styles; falls back to the builder's default when omitted.",
    )


class UdtBuildResponse(BaseModel):
    """Response body for ``POST /api/udt/build``: wire-format UDT JSON + a suggested filename."""

    udt: dict[str, Any]
    filename: str


def _to_schema(meta: TemplateMeta) -> TemplateMetaSchema:
    return TemplateMetaSchema(
        id=meta.id,
        label=meta.label,
        description=meta.description,
        questionnaire=[
            QuestionnaireFieldSchema(
                name=field.name,
                type=field.type,
                required=field.required,
                default=field.default,
                description=field.description,
            )
            for field in meta.questionnaire
        ],
        naming_styles=list(meta.naming_styles),
        default_naming_style=meta.default_naming_style,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/templates", response_model=list[TemplateMetaSchema])
async def get_templates() -> list[TemplateMetaSchema]:
    """List every available UDT template's metadata + questionnaire schema."""
    return [_to_schema(meta) for meta in list_templates()]


@router.post("/build", response_model=UdtBuildResponse)
async def build_udt(request: UdtBuildRequest) -> UdtBuildResponse:
    """
    Build a convention-conforming UDT from a template + questionnaire answers.

    Never writes anything to disk or a gateway — the response *is* the
    deliverable JSON (download-JSON-only delivery, ratified 2026-07-06).
    """
    known_ids = {meta.id for meta in list_templates()}
    if request.template_id not in known_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown template '{request.template_id}'. "
                f"Available: {', '.join(sorted(known_ids))}"
            ),
        )

    build_kwargs: dict[str, str] = {}
    if request.naming_style is not None:
        build_kwargs["naming_style"] = request.naming_style

    try:
        udt = build(request.template_id, request.answers, **build_kwargs)
    except UdtBuilderError as exc:
        # Invalid/missing answers, unknown naming_style, or a template bug
        # surfaced by the conventions self-check — all client-correctable
        # (or at least client-visible) input problems, not server errors.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return UdtBuildResponse(udt=to_tag_export(udt), filename=f"{udt.name}.json")
