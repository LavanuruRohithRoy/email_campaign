from __future__ import annotations
from typing import Any
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
                 import json
                 try:
                     return json.loads(value)
                 except:
                     pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return super().prepare_field_value(field_name, field, value, value_is_complex)

class Settings(BaseSettings):
    APP_ENV: str
    APP_BASE_URL: str
    SECRET_KEY: str
    JWT_SECRET: str
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    REDIS_URL: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str
    AWS_SQS_SEND_QUEUE_URL: str
    AWS_SQS_EVENTS_QUEUE_URL: str
    AWS_SES_CONFIG_SET: str
    MAX_SES_SEND_RATE: int = 14
    SQS_POLL_WAIT_SECONDS: int = 20
    SQS_MAX_MESSAGES: int = 10
    WORKER_CONCURRENCY: int = 5
    ALLOWED_ORIGINS: list[str]

    # Read from .env file by default. The `.env` value for `ALLOWED_ORIGINS`
    # should be a JSON array (e.g. ["http://localhost:5173"]) so Pydantic's
    # dotenv parser can decode it into a list[string].
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

settings = Settings()
