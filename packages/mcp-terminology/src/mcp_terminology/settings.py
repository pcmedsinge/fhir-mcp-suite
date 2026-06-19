"""Settings for mcp-terminology, loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Terminology server (FHIR R4 $tx endpoint)
    terminology_base_url: str = Field(
        default="https://tx.fhir.org/r4",
        description="Base URL of the FHIR R4 terminology server.",
    )
    terminology_timeout_s: float = Field(default=30.0)
    terminology_max_results: int = Field(
        default=20,
        description="Default maximum results returned by search / expand operations.",
    )

    # MCP transport
    mcp_transport: str = Field(
        default="stdio",
        description="MCP transport: 'stdio' (Claude Desktop) or 'sse'.",
    )
    mcp_host: str = Field(default="0.0.0.0")  # noqa: S104
    mcp_port: int = Field(default=8001, description="Port for SSE transport.")

    # Observability
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json", description="'json' (prod) or 'console' (dev).")
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = Field(default="https://cloud.langfuse.com")


settings = Settings()
