"""Website HTTP endpoints — minimal bootstrap for frontend URL → website_id."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.dependencies.db import DbSession
from app.domain.exceptions import DomainValidationError
from app.domain.website import validate_website_url
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate, WebsiteResponse

router = APIRouter(prefix="/websites", tags=["websites"])

_DEFAULT_ORG_SLUG = "sitepilot-local"
_DEFAULT_PROJECT_SLUG = "default"


class WebsiteBootstrapRequest(BaseModel):
    """Public URL only — org/project are auto-provisioned for unauthenticated MVP."""

    url: str = Field(..., description="Public website URL (http/https)")


@router.post(
    "",
    response_model=WebsiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a website from a public URL",
)
async def create_website(
    body: WebsiteBootstrapRequest,
    session: DbSession,
) -> WebsiteResponse:
    """
    Ensure a default local org/project exists, then create (or return) the website.

    Idempotent per canonical URL within the default project.
    """
    try:
        parsed = validate_website_url(body.url)
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_URL", "message": str(exc)},
        ) from exc

    orgs = OrganizationRepository(session)
    projects = ProjectRepository(session)
    websites = WebsiteRepository(session)

    org = await orgs.get_by_slug(_DEFAULT_ORG_SLUG)
    if org is None:
        org = await orgs.create(
            OrganizationCreate(
                name="SitePilot Local",
                slug=_DEFAULT_ORG_SLUG,
                plan_tier="free",
                status="active",
            )
        )

    project = await projects.get_by_org_slug(org.id, _DEFAULT_PROJECT_SLUG)
    if project is None:
        project = await projects.create(
            ProjectCreate(
                organization_id=org.id,
                name="Default",
                slug=_DEFAULT_PROJECT_SLUG,
                status="active",
            )
        )

    existing = await websites.get_by_canonical(project.id, parsed.canonical_url)
    if existing is not None:
        return WebsiteResponse.model_validate(existing)

    website = await websites.create(
        WebsiteCreate(project_id=project.id, url=body.url)
    )
    return WebsiteResponse.model_validate(website)
