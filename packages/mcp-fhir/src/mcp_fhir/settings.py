"""Settings for mcp-fhir, loaded from environment variables.

All settings have safe defaults so the server starts without any
configuration (pointing at public HAPI demo servers).
"""

from __future__ import annotations

from pydantic import Field, SecretStr
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

    # ── SMART-on-FHIR auth (v1.1) ────────────────────────────────────────────
    smart_enabled: bool = Field(
        default=False,
        description=(
            "Enable SMART-on-FHIR authentication. When True, a Bearer token is "
            "added to every FHIR request. Requires smart_client_id + "
            "smart_client_secret + smart_token_url (or auto-discovery)."
        ),
    )
    smart_client_id: str = Field(
        default="",
        description="SMART app client ID (from Epic/Cerner app registration).",
    )
    smart_client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="SMART app client secret.",
    )
    smart_token_url: str = Field(
        default="",
        description=(
            "OAuth 2.0 token endpoint URL. "
            "Leave empty to auto-discover from {fhir_base_url}/.well-known/smart-configuration."
        ),
    )
    smart_scopes: str = Field(
        default="system/*.read",
        description="Space-separated OAuth scopes for client_credentials grant.",
    )
    smart_grant_type: str = Field(
        default="client_credentials",
        description="OAuth grant type: 'client_credentials' (default) or 'authorization_code'.",
    )
    smart_token_timeout_s: float = Field(
        default=15.0,
        description="HTTP timeout for SMART token requests.",
    )


settings = Settings()
