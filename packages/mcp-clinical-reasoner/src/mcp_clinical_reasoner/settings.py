"""Settings for mcp-clinical-reasoner, loaded from environment / .env."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # RxNav REST API
    rxnav_base_url: str = Field(
        default="https://rxnav.nlm.nih.gov/REST",
        description="Base URL for the NLM RxNav REST API (no trailing slash).",
    )
    rxnav_timeout_s: float = Field(
        default=30.0,
        description="HTTP timeout for RxNav requests in seconds.",
    )

    # MCP transport
    mcp_transport: str = Field(
        default="stdio",
        description="MCP transport: 'stdio' (default) or 'sse'.",
        pattern="^(stdio|sse)$",
    )
    mcp_host: str = Field(default="0.0.0.0", description="Host for SSE transport.")  # noqa: S104
    mcp_port: int = Field(default=8002, description="Port for SSE transport.")

    # LangFuse observability (optional)
    langfuse_public_key: str = Field(default="", description="LangFuse public key.")
    langfuse_secret_key: str = Field(default="", description="LangFuse secret key.")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="LangFuse host URL.",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level (DEBUG/INFO/WARNING/ERROR).")
    log_format: str = Field(
        default="console",
        description="Log format: 'console' (dev) or 'json' (prod).",
        pattern="^(console|json)$",
    )


settings = Settings()
