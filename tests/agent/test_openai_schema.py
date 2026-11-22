"""Check the actual OpenAI request with an injected HTTP transport, offline."""

import asyncio
import json

import httpx2 as httpx
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agent import ask, build_agent


def test_router_sends_strict_schema_with_required_arrays_and_policy_file_enum():
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "offline-test", "object": "chat.completion", "created": 0, "model": "gpt-5.4-nano",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": json.dumps({
                    "scope": "unsupported", "policies": [], "bookings": [], "refunds": [],
                }),
            }}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    client = AsyncOpenAI(api_key="dummy-offline-key", http_client=httpx.AsyncClient(
        transport=httpx.MockTransport(respond),
    ))
    try:
        model = OpenAIChatModel("gpt-5.4-nano", provider=OpenAIProvider(openai_client=client))
        result = ask(build_agent(model), "Write me a recipe")
        assert result.error is None
        assert len(requests) == 1
        output = requests[0]["response_format"]["json_schema"]
        assert output["strict"] is True
        schema = output["schema"]
        assert set(schema["required"]) == {"scope", "policies", "bookings", "refunds"}
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]["policies"]["items"]["enum"]) == {"faq", "prices", "cancellations"}
    finally:
        asyncio.run(client.close())
