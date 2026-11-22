import asyncio
import os

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_missing_dotenv_keeps_ollama_defaults(tmp_path):
    settings = Settings.from_env(env_file=tmp_path / ".env", environ={})
    assert settings.provider == "ollama"
    assert settings.model == "llama3.1:8b"
    assert settings.ollama_base_url == "http://localhost:11434/v1"


def test_dotenv_is_loaded_without_exporting_variables(tmp_path):
    path = tmp_path / ".env"
    path.write_text("LLM_PROVIDER=ollama\nLLM_MODEL=file-model\nOLLAMA_BASE_URL=http://ollama:11434/v1\n", encoding="utf-8")
    settings = Settings.from_env(env_file=path, environ={})
    assert settings.model == "file-model"
    assert settings.ollama_base_url == "http://ollama:11434/v1"


def test_environment_overrides_dotenv(tmp_path):
    path = tmp_path / ".env"
    path.write_text("LLM_MODEL=file-model\n", encoding="utf-8")
    settings = Settings.from_env(env_file=path, environ={"LLM_MODEL": "environment-model"})
    assert settings.model == "environment-model"


def test_unrelated_compose_variables_are_ignored(tmp_path):
    path = tmp_path / ".env"
    path.write_text("LLM_MODEL=file-model\nDOCKER_OLLAMA_BASE_URL=http://host:11434/v1\nOLLAMA_MODEL=other\n", encoding="utf-8")
    assert Settings.from_env(env_file=path, environ={}).model == "file-model"


def test_dotenv_openai_key_is_passed_to_provider_without_changing_process_environment(tmp_path):
    path = tmp_path / ".env"
    key = "dummy-dotenv-test-key"
    path.write_text(f"LLM_PROVIDER=openai\nLLM_MODEL=test-model\nOPENAI_API_KEY={key}\n", encoding="utf-8")
    previous = os.environ.get("OPENAI_API_KEY")
    settings = Settings.from_env(env_file=path, environ={})
    model = settings.create_model()
    try:
        assert model.provider.client.api_key == key
        assert settings.provider == "openai"
        assert os.environ.get("OPENAI_API_KEY") == previous
        assert key not in repr(settings)
        assert key not in settings.model_dump_json()
    finally:
        asyncio.run(model.provider.client.close())


@pytest.mark.parametrize("environ, message", [
    ({"LLM_PROVIDER": "unsupported"}, "LLM_PROVIDER"),
    ({"LLM_MODEL": " "}, "must not be empty"),
    ({"OLLAMA_BASE_URL": ""}, "must not be empty"),
    ({"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "dummy-test-key"}, "Set LLM_MODEL"),
    ({"LLM_PROVIDER": "openai", "LLM_MODEL": "test-model"}, "OPENAI_API_KEY"),
    ({"LLM_PROVIDER": "openai", "LLM_MODEL": "test-model", "OPENAI_API_KEY": " "}, "OPENAI_API_KEY"),
])
def test_invalid_provider_configuration(environ, message):
    with pytest.raises(ValidationError, match=message):
        Settings.from_env(env_file=None, environ=environ)


def test_validation_errors_do_not_expose_keys():
    key = "dummy-private-test-key"
    with pytest.raises(ValidationError) as error:
        Settings.from_env(env_file=None, environ={"LLM_PROVIDER": "openai", "LLM_MODEL": "", "OPENAI_API_KEY": key})
    assert key not in str(error.value)


def test_separate_injected_environments_do_not_share_state():
    first = Settings.from_env(env_file=None, environ={"LLM_MODEL": "first"})
    second = Settings.from_env(env_file=None, environ={"LLM_MODEL": "second"})
    assert first.model == "first"
    assert second.model == "second"
