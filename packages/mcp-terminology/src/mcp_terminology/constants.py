"""Shared constants for mcp-terminology.

System URI aliases map user-friendly names to canonical FHIR system URIs.
ValueSet URIs map each system to a ValueSet suitable for $expand text search.
"""

from __future__ import annotations

# Canonical FHIR system URIs
SYSTEM_ALIASES: dict[str, str] = {
    "loinc":       "http://loinc.org",
    "snomed":      "http://snomed.info/sct",
    "snomed-ct":   "http://snomed.info/sct",
    "rxnorm":      "http://www.nlm.nih.gov/research/umls/rxnorm",
    "icd-10":      "http://hl7.org/fhir/sid/icd-10",
    "icd-10-cm":   "http://hl7.org/fhir/sid/icd-10-cm",
    "icd-10-pcs":  "http://www.cms.gov/Medicare/Coding/ICD10",
    "ndc":         "http://hl7.org/fhir/sid/ndc",
    "cpt":         "http://www.ama-assn.org/go/cpt",
    "cvx":         "http://hl7.org/fhir/sid/cvx",
    "nucc":        "http://nucc.org/provider-taxonomy",
    "ucum":        "http://unitsofmeasure.org",
}

# ValueSet canonical URLs used by $expand for free-text search.
# Only systems where tx.fhir.org supports free-text $expand are listed.
SYSTEM_VALUESET: dict[str, str] = {
    "http://loinc.org":                               "http://loinc.org/vs",
    "http://snomed.info/sct":                         "http://snomed.info/sct?fhir_vs",
    "http://www.nlm.nih.gov/research/umls/rxnorm":    "http://www.nlm.nih.gov/research/umls/rxnorm",
    "http://hl7.org/fhir/sid/cvx":                    "http://hl7.org/fhir/us/core/ValueSet/us-core-vaccines-cvx",
    "http://unitsofmeasure.org":                      "http://hl7.org/fhir/ValueSet/ucum-bodylength",
}

# Human-readable display names for known system URIs
SYSTEM_DISPLAY: dict[str, str] = {
    "http://loinc.org":                               "LOINC",
    "http://snomed.info/sct":                         "SNOMED CT",
    "http://www.nlm.nih.gov/research/umls/rxnorm":    "RxNorm",
    "http://hl7.org/fhir/sid/icd-10":                 "ICD-10",
    "http://hl7.org/fhir/sid/icd-10-cm":              "ICD-10-CM",
    "http://www.cms.gov/Medicare/Coding/ICD10":        "ICD-10-PCS",
    "http://hl7.org/fhir/sid/ndc":                    "NDC",
    "http://www.ama-assn.org/go/cpt":                 "CPT",
    "http://hl7.org/fhir/sid/cvx":                    "CVX",
    "http://unitsofmeasure.org":                      "UCUM",
}
