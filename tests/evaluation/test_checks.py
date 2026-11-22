import copy
import json
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from app.agent import build_agent
from eval.checks import validate
from eval.run import run_case


@pytest.fixture
def case():
    cases = json.loads((Path(__file__).resolve().parents[2] / "eval/cases.json").read_text())
    return next(case for case in cases if case["id"] == "half_refund")


@pytest.fixture
def run(case):
    return {"answer": "Your total refund is 340 EUR: rental 40, deposit 300; fee 2 retained.",
            "error": None, "elapsed_seconds": 2, "requests": 2,
            "calls": [{"tool": "calculate_refund", "args": {"booking_id": "CW-1002"},
                       "returned": True, "retry": False, "call_id": "refund",
                       "result": copy.deepcopy(case["expected_refund"])}]}


def test_correct_answer_and_trace_pass(case, run):
    assert not any(validate(case, run, {}).values())


@pytest.mark.parametrize("fault", ["no_tool", "wrong_id", "wrong_amount", "wrong_answer", "contradiction", "repeat", "slow", "timeout", "unreturned", "retry", "too_many_requests"])
def test_evaluator_rejects_faults(case, run, fault):
    if fault == "no_tool":
        run["calls"] = []
    elif fault == "wrong_id":
        run["calls"][0]["args"]["booking_id"] = "CW-1001"
    elif fault == "wrong_amount":
        run["calls"][0]["result"]["refund"] = "999"
    elif fault == "wrong_answer":
        run["answer"] = "Your total refund is 999 EUR."
    elif fault == "contradiction":
        run["answer"] += " Your total is 999 EUR."
    elif fault == "repeat":
        run["calls"].append(copy.deepcopy(run["calls"][0]))
    elif fault == "slow":
        run["elapsed_seconds"] = 61
    elif fault == "timeout":
        run["error"] = "RunTimedOut"
    elif fault == "unreturned":
        run["calls"][0]["returned"] = False
    elif fault == "retry":
        run["calls"][0]["retry"] = True
    elif fault == "too_many_requests":
        run["requests"] = 6
    assert any(validate(case, run, {}).values())


def test_real_runner_blocks_an_unplanned_tool_call(case):
    def model(messages, info):
        return ModelResponse(parts=[ToolCallPart("get_booking", {"booking_id": "CW-9999"})])

    result = run_case(build_agent(FunctionModel(model)), case, {})
    assert not result["passed"]
    assert result["calls"] == []
    assert result["model_tool_calls"][0]["args"] == {"booking_id": "CW-9999"}
    assert result["failures"]["tools"]


def test_invalid_policy_arguments_fail_without_crashing(case, run):
    run["calls"] = [{"tool": "search_policies", "args": {"policy": [], "topics": None},
                     "returned": True, "retry": True, "result": "Invalid args"}]
    assert validate(case, run, {"prices": ["Bike rental"]})["tools"]


def test_deposit_must_not_be_called_full_rental_refund(case, run):
    case["expected_refund"]["rental_refund"] = "0"
    run["answer"] += " This is a full rental refund."
    assert any("Deposit-only" in failure for failure in validate(case, run, {})["answer"])


def test_negated_full_rental_refund_does_not_trigger_label_check(case, run):
    case["expected_refund"]["rental_refund"] = "0"
    run["answer"] += " This is not a full rental refund."
    assert not any("Deposit-only" in failure for failure in validate(case, run, {})["answer"])
