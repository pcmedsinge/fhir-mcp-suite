"""FHIR resource and search models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class FhirResource(BaseModel):
    """A single FHIR resource as returned by the server."""

    resource_type: str = Field(alias="resourceType")
    id: str | None = None
    meta: dict[str, Any] | None = None
    # All remaining fields stored as-is; avoids re-modelling the full FHIR spec.
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True, "extra": "allow"}


class FhirSearchParams(BaseModel):
    """Parameters for a FHIR search request."""

    resource_type: str = Field(description="FHIR resource type, e.g. 'Patient', 'Observation'")
    params: dict[str, str] = Field(
        default_factory=dict,
        description="FHIR search parameters, e.g. {'family': 'Smith', '_count': '10'}",
    )
    base_url: HttpUrl | None = Field(
        default=None,
        description="Override the default FHIR server base URL for this request.",
    )
