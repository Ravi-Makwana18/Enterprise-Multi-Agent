import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE, override=True)


def _get_bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _get_list_env(name: str, default: str) -> list[str]:
    raw_value = os.getenv(name, default)
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


_ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
_LOCAL_MODE = _get_bool_env("LOCAL_MODE", False)


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Enterprise Multi-Agent Platform")
    environment: str = _ENVIRONMENT
    debug: bool = _get_bool_env("DEBUG", _ENVIRONMENT in {"local", "development"})
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8001"))
    cors_origins: list[str] = _get_list_env(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    )
    local_mode: bool = _LOCAL_MODE
    allow_demo_auth: bool = _get_bool_env("ALLOW_DEMO_AUTH", False)
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID",
        "anthropic.claude-3-sonnet-20240229-v1:0",
    )
    max_message_length: int = int(os.getenv("MAX_MESSAGE_LENGTH", "5000"))
    max_request_bytes: int = int(os.getenv("MAX_REQUEST_BYTES", str(1024 * 1024)))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    secret_name: str = os.getenv("AWS_SECRET_NAME", "enterprise-multi-agent")
    use_aws_secrets_manager: bool = _get_bool_env("USE_AWS_SECRETS_MANAGER", False)
    aws_access_key_id: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token: str | None = os.getenv("AWS_SESSION_TOKEN")
    api_tokens: str | None = os.getenv("API_TOKENS")
    rate_limit_requests_per_minute: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./enterprise_multi_agent.db")
    database_echo: bool = _get_bool_env("DATABASE_ECHO", False)
    huggingface_api_token: str | None = os.getenv("HUGGINGFACE_API_TOKEN")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")


settings = Settings()
