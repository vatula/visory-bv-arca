from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(default="arcra.db", description="Path to the SQLite database file")

    # AWS / Bedrock
    aws_access_key_id: str = Field(default="", description="AWS access key ID")
    aws_secret_access_key: str = Field(default="", description="AWS secret access key")
    aws_default_region: str = Field(default="ap-southeast-2", description="AWS region")
    bedrock_model_id: str = Field(default="amazon.nova-lite-v1:0", description="Bedrock model identifier")

    # Slack
    slack_signing_secret: str = Field(default="", description="Slack signing secret for webhook verification")

    # Synthesis
    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="Minimum confidence score before escalation")

    # API
    frontend_origin: str = Field(default="http://localhost:3000", description="Allowed CORS origin for the Next.js frontend")
    log_level: str = Field(default="INFO", description="Structlog minimum log level")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
