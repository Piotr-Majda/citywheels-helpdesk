"""Offline tests for the manager/specialist workflow and enforced evidence."""

import asyncio
import json

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel

from app.agent import AgentDependencies, ask, build_agent
from app.db.policy_loader import parse_policy
from app.models.workflow import Citation, PolicySummary, RoutePlan, route_schema
from app.agent import validate_summary
from app.context import EvidenceError


def scripted(responses):
    steps = iter(responses)
    def model(messages, info):
        response = next(steps)
        if callable(response):
            return response(messages, info)
        return ModelResponse(parts=[TextPart(json.dumps(response))])
    return FunctionModel(model)


def plan(kind, *, policy=None, booking_id=None):
    return {"scope": "supported", "policies": [policy] if policy else [],
            "bookings": [booking_id] if kind == "booking" else [],
            "refunds": [booking_id] if kind == "refund" else []}


def tool(name, **args):
    def response(messages, info):
        assert not info.function_tools
        assert [item.name for item in info.output_tools] == [name]
        assert not {"ctx", "booking_loader", "policy_loader", "cancellation_time"} & set(
            info.output_tools[0].parameters_json_schema.get("properties", {})
        )
        return ModelResponse(parts=[ToolCallPart(name, args)])
    return response


def test_refund_specialist_calls_tool_and_python_renders_amounts(booking_data):
    model = scripted([plan("refund", booking_id="CW-1002"), tool("calculate_refund", booking_id="CW-1002")])
    result = ask(build_agent(model), "Cancel CW-1002: how much do I get back?",
                 deps=AgentDependencies(booking_loader=lambda: booking_data))
    assert result.error is None
    assert "340.0 EUR" in result.output
    assert "300.0 EUR" in result.output
    assert [call["tool"] for call in result.calls] == ["calculate_refund"]
    assert result.calls[0]["result"]["refund"] == "340.0"
    assert result.usage.requests == 2
    assert [stage["phase"] for stage in result.stages] == ["manager_route", "refund_specialist"]


def test_policy_requires_catalogue_and_real_section_before_summary():
    policies = {"prices": parse_policy("# Prices\nAll in EUR.\n## Booking fee\nOnline: 2 EUR.\n",
                                       policy="prices", source="data/policies/prices.md")}
    def synthesize(messages, info):
        prompt = next(part.content for part in messages[-1].parts if isinstance(part, UserPromptPart))
        evidence = json.loads(prompt)["evidence"]
        assert evidence[0]["source_id"] == "policy:prices"
        assert "Online: 2 EUR." in evidence[0]["text"]
        assert not info.function_tools and not info.output_tools
        return ModelResponse(parts=[TextPart(json.dumps({
            "citations": [{"source_id": "policy:prices", "quote": "Online: 2 EUR."}],
        }))])

    model = scripted([
        plan("policy", policy="prices"),
        tool("search_policies", policy="prices", topics=["Booking fee"]),
        synthesize,
    ])
    result = ask(build_agent(model), "What is the online booking fee?",
                 deps=AgentDependencies(policy_loader=lambda: policies))
    assert result.error is None
    assert "Online: 2 EUR." in result.output
    assert "data/policies/prices.md" in result.output
    assert [call["tool"] for call in result.calls] == ["list_policy_topics", "search_policies"]
    assert result.calls[0]["origin"] == "application"
    assert result.calls[1]["origin"] == "model"
    assert result.usage.requests == 3
    assert result.stages[-1]["phase"] == "manager_summary"


@pytest.mark.parametrize("unknown", [False, True])
def test_booking_results_are_not_paraphrased_into_invented_status(booking_data, unknown):
    booking_id = "CW-9999" if unknown else "CW-1005"
    model = scripted([plan("booking", booking_id=booking_id), tool("get_booking", booking_id=booking_id)])
    result = ask(build_agent(model), f"Show {booking_id}",
                 deps=AgentDependencies(booking_loader=lambda: booking_data))
    assert result.error is None
    assert ("not found" if unknown else "cancelled") in result.output


def test_unsupported_request_never_runs_specialists_or_sources():
    def forbidden_source():
        raise AssertionError("Sources should not be touched")
    result = ask(build_agent(scripted([{"scope": "unsupported", "policies": [], "bookings": [], "refunds": []}])), "Write a recipe",
                 deps=AgentDependencies(booking_loader=forbidden_source, policy_loader=forbidden_source))
    assert result.error is None
    assert "help@citywheels.example" in result.output
    assert result.calls == []
    assert result.usage.requests == 1


def test_hallucinated_booking_id_in_plan_is_blocked():
    result = ask(build_agent(scripted([plan("booking", booking_id="CW-1001")])), "Show CW-9999")
    assert result.error in {"EvidenceError", "UnexpectedModelBehavior"}
    assert result.calls == []


def test_specialist_prose_cannot_replace_tool_execution():
    responses = [plan("booking", booking_id="CW-1001"), "unverified", "unverified"]
    model = scripted([responses[0], lambda m, i: ModelResponse(parts=[TextPart("It is confirmed")]),
                      lambda m, i: ModelResponse(parts=[TextPart("It is confirmed")])])
    result = ask(build_agent(model), "Show CW-1001")
    assert result.error is not None
    assert "It is confirmed" not in result.output
    assert result.calls == []


def test_wrong_specialist_booking_id_cannot_access_other_record(booking_data):
    model = scripted([plan("booking", booking_id="CW-1001"),
                      tool("get_booking", booking_id="CW-1002"), tool("get_booking", booking_id="CW-1001")])
    result = ask(build_agent(model), "Show CW-1001", deps=AgentDependencies(booking_loader=lambda: booking_data))
    assert result.error is None
    assert [call["args"] for call in result.calls] == [{"booking_id": "CW-1001"}]
    assert result.usage.requests == 3


def test_shared_request_limit_applies_across_manager_and_specialist():
    model = scripted([plan("booking", booking_id="CW-1001")])
    result = ask(build_agent(model), "Show CW-1001", request_limit=1)
    assert result.error == "UsageLimitExceeded"
    assert result.usage.requests == 1
    assert result.calls == []


def test_source_error_fails_closed():
    def source():
        raise OSError("Unavailable")
    model = scripted([plan("booking", booking_id="CW-1001"), tool("get_booking", booking_id="CW-1001")])
    result = ask(build_agent(model), "Show CW-1001", deps=AgentDependencies(booking_loader=source))
    assert result.error == "EvidenceError"
    assert result.calls[0]["result"]["result"] == "data_unavailable"
    assert "help@citywheels.example" in result.output


@pytest.mark.parametrize("summary", [
    PolicySummary(citations=[Citation(source_id="p", quote="Fee: 999 EUR.")]),
    PolicySummary(citations=[Citation(source_id="other", quote="Fee: 2 EUR.")]),
])
def test_manager_cannot_use_missing_sources_or_invented_quotes(summary):
    with pytest.raises(EvidenceError):
        validate_summary(summary, [{"source_id": "p", "text": "Fee: 2 EUR."}])


def test_incoherent_plan_is_rejected():
    with pytest.raises(ValidationError):
        RoutePlan.model_validate({"scope": "unsupported", "bookings": ["CW-1001"]})


def test_free_form_policy_answer_is_not_a_valid_summary():
    with pytest.raises(ValidationError):
        PolicySummary.model_validate({
            "answer": "We are closed even though the quote says open",
            "citations": [{"source_id": "p", "quote": "Open daily."}],
        })


def test_duplicate_tasks_are_rejected():
    with pytest.raises(ValidationError):
        RoutePlan.model_validate({"scope": "supported", "bookings": ["CW-1001", "CW-1001"]})


def test_mixed_request_uses_separate_specialists_and_shared_usage(booking_data):
    policies = {"prices": parse_policy("# Prices\n## Booking fee\nOnline: 2 EUR.\n",
                                       policy="prices", source="data/policies/prices.md")}
    route = {"scope": "supported", "policies": ["prices"], "bookings": [], "refunds": ["CW-1002"]}
    model = scripted([route, tool("search_policies", policy="prices", topics=["Booking fee"]),
                      tool("calculate_refund", booking_id="CW-1002"),
                      {"citations": [{"source_id": "policy:prices", "quote": "Online: 2 EUR."}]}])
    result = ask(build_agent(model), "Explain the booking fee and my refund for CW-1002",
                 deps=AgentDependencies(booking_loader=lambda: booking_data, policy_loader=lambda: policies))
    assert result.error is None
    assert result.usage.requests == 4
    assert "340.0 EUR" in result.output and "Online: 2 EUR." in result.output
    assert [stage["phase"] for stage in result.stages] == [
        "manager_route", "policy_specialist", "refund_specialist", "manager_summary",
    ]


def test_policy_tool_budget_includes_forced_catalogue():
    policies = {"prices": parse_policy("# Prices\n## Booking fee\nOnline: 2 EUR.\n",
                                       policy="prices", source="data/policies/prices.md")}
    model = scripted([plan("policy", policy="prices"), tool("search_policies", policy="prices", topics=["Booking fee"])])
    result = ask(build_agent(model), "What is the booking fee?", tool_calls_limit=1,
                 deps=AgentDependencies(policy_loader=lambda: policies))
    assert result.error == "EvidenceError"
    assert [call["tool"] for call in result.calls] == ["list_policy_topics"]


def test_invalid_topic_is_retried_without_executing_it():
    policies = {"prices": parse_policy("# Prices\n## Booking fee\nOnline: 2 EUR.\n",
                                       policy="prices", source="data/policies/prices.md")}
    model = scripted([plan("policy", policy="prices"),
                      tool("search_policies", policy="prices", topics=["invented"]),
                      tool("search_policies", policy="prices", topics=["Booking fee"]),
                      {"citations": [{"source_id": "policy:prices", "quote": "Online: 2 EUR."}]}])
    result = ask(build_agent(model), "What is the booking fee?", deps=AgentDependencies(policy_loader=lambda: policies))
    assert result.error is None
    assert result.usage.requests == 4
    assert result.calls[-1]["args"]["topics"] == ["Booking fee"]
    assert len(result.calls) == 2


def test_summary_missing_one_requested_source_is_rejected():
    summary = PolicySummary(citations=[Citation(source_id="p", quote="Fee: 2 EUR.")])
    with pytest.raises(EvidenceError, match="every requested source"):
        validate_summary(summary, [{"source_id": "p", "text": "Fee: 2 EUR."},
                                   {"source_id": "other", "text": "Another rule."}])


def test_shared_timeout_stops_delayed_model():
    async def delayed_model(messages, info):
        await asyncio.sleep(10)
        return ModelResponse(parts=[TextPart('{"scope":"unsupported","policies":[],"bookings":[],"refunds":[]}')])
    result = ask(build_agent(FunctionModel(delayed_model)), "Hello", timeout=0.02)
    assert result.error is not None
    assert "help@citywheels.example" in result.output
    assert result.calls == []


def test_manager_schema_limits_ids_to_question_and_disallows_details():
    schema = route_schema("Show CW-1002")
    good = schema.model_validate({"scope": "supported", "bookings": ["CW-1002"]})
    assert good.tasks[0].booking_id == "CW-1002"
    for invented in ("CW-1001", "Mountain bike, quantity 1"):
        with pytest.raises(ValidationError):
            schema.model_validate({"scope": "supported", "bookings": [invented]})


def test_manager_schema_without_ids_only_allows_policy_or_clarification():
    schema = route_schema("What are your prices?")
    assert schema.model_validate({"scope": "supported", "policies": ["prices"]}).tasks
    with pytest.raises(ValidationError):
        schema.model_validate({"scope": "supported", "refunds": ["CW-1001"]})
