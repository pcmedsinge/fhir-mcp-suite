"""Validation report models — HAPI validator output, normalised.

Ported from P1 (fhir-mapping-agent) with minor adaptations for P3.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ValidationSeverity(StrEnum):
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


class ValidationIssue(BaseModel):
    severity: ValidationSeverity
    code: str = Field(description="HAPI/FHIR issue code, e.g. 'required', 'code-invalid'")
    location: str | None = Field(default=None, description="FHIRPath of the offending element")
    message: str


class ValidationReport(BaseModel):
    profile: str
    resource_type: str
    is_conformant: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0

    def model_post_init(self, _ctx: object, /) -> None:
        self.error_count = sum(
            1
            for i in self.issues
            if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.FATAL)
        )
        self.warning_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
