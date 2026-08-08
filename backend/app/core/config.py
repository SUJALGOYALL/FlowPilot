from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "FlowPilot"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = ""

    EMBEDDING_PROVIDER: str = ""
    EMBEDDING_MODEL: str = ""

    PROVISIONING_MCP_URL: str = "http://localhost:8001"
    POLICY_MCP_URL: str = "http://localhost:8002"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()