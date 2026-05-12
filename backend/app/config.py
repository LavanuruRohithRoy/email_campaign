from __future__ import annotations
import sys
import json
from typing import Any
from pydantic import field_validator, ValidationError
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict

class EmailPlatformSettingsSource(EnvSettingsSource):
    def prepare_field_value(
        self,
        field_name: str,
        field: Any,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        if field_name == "ALLOWED_ORIGINS" and isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return super().prepare_field_value(field_name, field, value, value_is_complex)

class Settings(BaseSettings):
    # Application environment
    APP_ENV: str  # development, test, production
    APP_BASE_URL: str
    
    # Security & secrets
    SECRET_KEY: str
    JWT_SECRET: str
    
    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    
    # Redis
    REDIS_URL: str
    
    # AWS credentials & config
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str
    AWS_SQS_SEND_QUEUE_URL: str
    AWS_SQS_EVENTS_QUEUE_URL: str
    AWS_SES_CONFIG_SET: str
    
    # Email sending
    MAX_SES_SEND_RATE: int = 14
    SQS_POLL_WAIT_SECONDS: int = 20
    SQS_MAX_MESSAGES: int = 10
    WORKER_CONCURRENCY: int = 5
    WORKER_MAX_RETRIES: int = 5
    
    # Rate limiting
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 900
    RATE_LIMIT_TEST_EMAIL_PER_HOUR: int = 10
    RATE_LIMIT_WEBHOOK_PER_MINUTE: int = 60
    
    # Frontend & CORS
    ALLOWED_ORIGINS: list[str]
    VITE_API_BASE_URL: str
    AWS_SQS_DLQ_URL: str | None = None
    
    # Logging & observability
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT_JSON: bool = False
    REQUEST_TIMEOUT_SECONDS: int = 30
    
    # Feature flags
    ENABLE_HEALTHCHECKS: bool = True
    ENABLE_METRICS: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        return (
            init_settings,
            EmailPlatformSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        valid_envs = {"development", "test", "production"}
        if v not in valid_envs:
            raise ValueError(f"APP_ENV must be one of {valid_envs}, got: {v}")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", "development")
        
        # Production must have real secrets
        if app_env == "production":
            if not v or len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters in production. "
                    "Generate with: openssl rand -hex 32"
                )
            if "placeholder" in v.lower() or "dev" in v.lower():
                raise ValueError("SECRET_KEY contains placeholder value in production")
        
        return v

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", "development")
        
        # Production must have real secrets
        if app_env == "production":
            if not v or len(v) < 32:
                raise ValueError(
                    "JWT_SECRET must be at least 32 characters in production. "
                    "Generate with: openssl rand -hex 32"
                )
            if "placeholder" in v.lower() or "dev" in v.lower():
                raise ValueError("JWT_SECRET contains placeholder value in production")
        
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", "development")
        
        if not v or "postgresql" not in v:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL async connection string")
        
        if "asyncpg" not in v:
            raise ValueError("DATABASE_URL must use asyncpg driver")
        
        if app_env == "production":
            if "localhost" in v or "127.0.0.1" in v:
                raise ValueError("DATABASE_URL cannot use localhost in production")
        
        return v

    @field_validator("DATABASE_URL_SYNC")
    @classmethod
    def validate_database_url_sync(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", "development")
        
        if not v or "postgresql" not in v:
            raise ValueError("DATABASE_URL_SYNC must be a valid PostgreSQL sync connection string")
        
        if app_env == "production":
            if "localhost" in v or "127.0.0.1" in v:
                raise ValueError("DATABASE_URL_SYNC cannot use localhost in production")
        
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", "development")
        
        if not v or "redis" not in v:
            raise ValueError("REDIS_URL must be a valid Redis connection string")
        
        if app_env == "production":
            if "localhost" in v or "127.0.0.1" in v:
                raise ValueError("REDIS_URL cannot use localhost in production")
        
        return v

    @field_validator("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
    @classmethod
    def validate_aws_credentials(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", "development")
        
        if not v:
            raise ValueError("AWS credentials cannot be empty")
        
        if app_env == "production":
            if v.startswith("PLACEHOLDER") or "EXAMPLE" in v:
                raise ValueError("AWS credentials contain placeholder values in production")
        
        return v

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_allowed_origins(cls, v: list[str], info) -> list[str]:
        app_env = info.data.get("APP_ENV", "development")
        
        if not v or len(v) == 0:
            raise ValueError("ALLOWED_ORIGINS cannot be empty")
        
        if app_env == "production":
            # Production must not allow localhost
            for origin in v:
                if "localhost" in origin or "127.0.0.1" in origin or "0.0.0.0" in origin:
                    raise ValueError(f"ALLOWED_ORIGINS cannot contain localhost in production: {origin}")
        
        return v

    @field_validator("VITE_API_BASE_URL")
    @classmethod
    def validate_vite_api_base_url(cls, v: str, info) -> str:
        if not v:
            raise ValueError("VITE_API_BASE_URL cannot be empty")
        
        if not v.startswith(("http://", "https://")):
            raise ValueError("VITE_API_BASE_URL must start with http:// or https://")
        
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    @field_validator("RATE_LIMIT_LOGIN_ATTEMPTS", "RATE_LIMIT_LOGIN_WINDOW_SECONDS",
                    "RATE_LIMIT_TEST_EMAIL_PER_HOUR", "RATE_LIMIT_WEBHOOK_PER_MINUTE")
    @classmethod
    def validate_rate_limits(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Rate limit values must be >= 1")
        return v

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"

    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.APP_ENV == "test"


try:
    settings = Settings()  # type: ignore[call-arg]
except ValidationError as e:
    print("\n" + "="*80)
    print("CONFIGURATION ERROR - Application cannot start")
    print("="*80)
    for error in e.errors():
        print(f"\n❌ {error['loc'][0]}: {error['msg']}")
    print("\n" + "="*80)
    print("Please fix the above configuration errors and restart the application.")
    print("="*80 + "\n")
    sys.exit(1)

