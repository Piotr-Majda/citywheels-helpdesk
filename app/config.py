"""Provider configuration read from environment variables."""

from dataclasses import dataclass
import os

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider


@dataclass(frozen=True)
class Settings:
    provider: str = "ollama"
    model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434/v1"

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.environ.get("LLM_PROVIDER", "ollama")
        if provider not in {"ollama", "openai"}:
            raise ValueError("LLM_PROVIDER must be ollama or openai")
        model = os.environ.get("LLM_MODEL", "llama3.1:8b" if provider == "ollama" else "")
        if not model.strip():
            raise ValueError("Set LLM_MODEL to a model available from your provider")
        if provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required for OpenAI")
        return cls(provider, model, os.environ.get("OLLAMA_BASE_URL", cls.ollama_base_url))

    def create_model(self) -> OpenAIChatModel:
        if self.provider == "ollama":
            return OpenAIChatModel(self.model, provider=OllamaProvider(base_url=self.ollama_base_url))
        if self.provider == "openai":
            return OpenAIChatModel(self.model)
        raise ValueError("Unsupported provider")
