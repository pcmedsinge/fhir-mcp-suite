"""fhir-mcp-shared — internal utilities for the fhir-mcp-suite monorepo.

Public surface (intended for import by package servers):

    from fhir_mcp_shared.logging import configure_logging
    from fhir_mcp_shared.langfuse import span, generation, get_client
    from fhir_mcp_shared.models import ValidationIssue, ValidationReport, FhirResource
    from fhir_mcp_shared.eval import EvalRunner, GoldenCase, EvalResult
"""

from fhir_mcp_shared.logging import configure_logging

__all__ = ["configure_logging"]
