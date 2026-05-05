"""Settings for mcp-fhir, loaded from environment variables.

All settings have safe defaults so the server starts without any
configuration (pointing at public HAPI demo servers).
"""

from __future__ import annotations

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # FHIR server
    fhir_base_url: str = Field(
        default="https://hapi.fhir.org/baseR4",
        description="Base URL of the FHIR R4 server (no trailing slash).",
    )
    fhir_timeout_s: float = Field(default=30.0, description="HTTP timeout for FHIR requests.")
    fhir_max_results: int = Field(
        default=50,
        description="Maximum _count to request per search (capped server-side too).",
    )

    # HAPI validator sidecar
    hapi_validator_url: str = Field(
        default="http://localhost:8080",
        description="Base URL of the markiantorno/validator-wrapper sidecar.",
    )
    hapi_validator_timeout_s: float = Field(default=60.0)

    # MCP transport
    mcp_transport: str = Field(
        default="stdio",
        description="MCP transport: 'stdio' (default, for Claude Desktop) or 'sse'.",
    )
    mcp_host: str = Field(default="0.0.0.0", description="Host for SSE transport.")
    mcp_port: int = Field(default=8000, description="Port for SSE transport.")

    # Observability
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json", description="'json' or 'console'")
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = Field(default="https://cloud.langfuse.com")


settings = Settings()
