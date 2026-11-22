"""Validated provider settings from explicit values, environment, and root .env."""

from collections.abc import Mapping
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore",
        populate_by_name=True, frozen=True, hide_input_in_errors=True,
    )

    provider: Literal["ollama", "openai"] = Field(default="ollama", validation_alias="LLM_PROVIDER")
    model: str = Field(default="llama3.1:8b", validation_alias="LLM_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434/v1", validation_alias="OLLAMA_BASE_URL")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY", repr=False)

    @field_validator("model", "ollama_base_url")
    @classmethod
    def nonempty_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Model and provider URL must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def validate_provider(self) -> Self:
        if self.provider == "openai":
            if "model" not in self.model_fields_set:
                raise ValueError("Set LLM_MODEL to a model available from OpenAI")
            if self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip():
                raise ValueError("OPENAI_API_KEY is required for OpenAI")
        return self

    @classmethod
    def from_env(
        cls, *, env_file: Path | str | None = ENV_FILE,
        environ: Mapping[str, str] | None = None,
    ) -> "Settings":
        """Load .env automatically; allow isolated source injection in unit tests.

        Real process variables override .env. Supplying environ replaces only
        that source without changing os.environ or monkeypatching module state.
        env_file=None disables dotenv loading explicitly.
        """
        if environ is None:
            return cls(_env_file=env_file)
        normalized = {key.upper(): value for key, value in environ.items()}
        supplied = {field.validation_alias: normalized[field.validation_alias.upper()]
                    for field in cls.model_fields.values()
                    if isinstance(field.validation_alias, str) and field.validation_alias.upper() in normalized}

        class InjectedSettings(cls):
            @classmethod
            def settings_customise_sources(
                cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings,
            ):
                return init_settings, lambda: supplied, dotenv_settings, file_secret_settings

        return InjectedSettings(_env_file=env_file)

    def create_model(self) -> OpenAIChatModel:
        if self.provider == "ollama":
            return OpenAIChatModel(self.model, provider=OllamaProvider(base_url=self.ollama_base_url))
        if self.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required for OpenAI")
        # A dotenv-loaded key is not exported into os.environ. Pass it explicitly
        # instead of relying on the OpenAI SDK to read process variables again.
        return OpenAIChatModel(self.model, provider=OpenAIProvider(api_key=self.openai_api_key.get_secret_value()))
