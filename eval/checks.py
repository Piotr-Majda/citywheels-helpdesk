"""Explicit, inspectable checks; no LLM judge and no exact-answer comparison."""

from collections import Counter
from decimal import Decimal, InvalidOperation
import json
import re


def validate(case: dict, run: dict, catalogue: dict[str, list[str]]) -> dict[str, list[str]]:
    failures = {"answer": [], "tools": [], "runtime": []}
    answer = run["answer"]
    calls = run["calls"]
    for attempt in run.get("model_tool_calls", []):
        if not any(call["tool"] == attempt["tool"] and call["args"] == attempt["args"] for call in calls):
            failures["tools"].append(f"Rejected or unexecuted model tool choice: {attempt['tool']} {attempt['args']}")
    if run["error"]:
        failures["runtime"].append(f"Run failed: {run['error']}")
    if not answer.strip():
        failures["answer"].append("No final answer")
    for pattern in case.get("answer_patterns", []):
        if not re.search(pattern, answer, re.IGNORECASE):
            failures["answer"].append(f"Missing required fact/refusal pattern: {pattern}")
    for pattern in case.get("forbidden_patterns", []):
        if re.search(pattern, answer, re.IGNORECASE):
            failures["answer"].append(f"Forbidden answer pattern: {pattern}")

    for call in calls:
        name, args = call["tool"], call["args"]
        if name not in case["allowed_tools"]:
            failures["tools"].append(f"Unexpected tool: {name}")
        if name in {"get_booking", "calculate_refund"}:
            if args != {"booking_id": case.get("booking_id")}:
                failures["tools"].append(f"Wrong booking arguments: {args}")
        elif name == "list_policy_topics":
            if args:
                failures["tools"].append(f"Unexpected catalogue arguments: {args}")
        elif name == "search_policies":
            policy, topics = args.get("policy"), args.get("topics")
            valid = (set(args) == {"policy", "topics"} and isinstance(policy, str) and policy in catalogue
                     and isinstance(topics, list) and bool(topics)
                     and all(isinstance(topic, str) for topic in topics))
            if not valid or len(topics) != len(set(topics)) or any(
                topic not in catalogue.get(policy, []) for topic in topics
            ):
                failures["tools"].append(f"Invalid policy/topic arguments: {args}")
            elif policy not in case.get("allowed_policies", []):
                failures["tools"].append(f"Unrelated policy selected: {policy}")
            if not any(previous["tool"] == "list_policy_topics" for previous in calls[:calls.index(call)]):
                failures["tools"].append("Policy retrieval before catalogue discovery")
        if not call["returned"]:
            failures["tools"].append(f"Tool returned no result: {name}")
        if call.get("retry"):
            failures["tools"].append(f"Tool validation/execution retry: {name}")
        if isinstance(call["result"], dict) and call["result"].get("result") in {
            "invalid_policy", "invalid_topics", "data_unavailable",
        }:
            failures["tools"].append(f"Tool error result: {call['result']['result']}")

    for expected in case["required_calls"]:
        def matches(call):
            if call["tool"] != expected["tool"]:
                return False
            for key, value in expected["args"].items():
                actual = call["args"].get(key)
                if key == "topics":
                    if not isinstance(actual, list) or not all(topic in actual for topic in value):
                        return False
                elif actual != value:
                    return False
            return True

        if not any(matches(call) for call in calls):
            failures["tools"].append(f"Missing required call: {expected}")

    refunds = [call for call in calls if call["tool"] == "calculate_refund" and call["returned"]]
    if "expected_refund" in case:
        for field, expected in case["expected_refund"].items():
            try:
                actual = refunds[-1]["result"][field]
                if Decimal(str(actual)) != Decimal(expected):
                    raise ValueError()
            except (IndexError, KeyError, TypeError, InvalidOperation, ValueError):
                failures["tools"].append(f"Refund tool field {field} must equal {expected}")
        # The expected amount must be described as the refund/total, not merely
        # occur somewhere in a contradictory answer. Other numbers may describe
        # components, dates, hours, or a booking ID and cannot all be forbidden.
        total = re.escape(case["expected_refund"]["refund"])
        if not re.search(
            rf"(?:refund|total|back)[^\n]{{0,70}}\b{total}(?:[.,]0{{1,2}})?\b"
            rf"|\b{total}(?:[.,]0{{1,2}})?\s*(?:EUR|euros?|€)", answer, re.IGNORECASE,
        ):
            failures["answer"].append("Expected amount not identified as refund/total")
        explicit_totals = re.findall(
            r"\btotal(?:\s+refund|\s+amount)?\s*(?:is|of|:|=|will be)?\s*€?\s*(\d+(?:[.,]\d+)?)",
            answer, re.IGNORECASE,
        )
        if any(Decimal(value.replace(",", ".")) != Decimal(case["expected_refund"]["refund"]) for value in explicit_totals):
            failures["answer"].append("Contradictory explicit total in answer")
        if Decimal(case["expected_refund"]["rental_refund"]) == 0:
            for match in re.finditer(r"\bfull\s+rental\s+refund\b", answer, re.IGNORECASE):
                prefix = answer[max(0, match.start() - 30):match.start()]
                if not re.search(r"\b(?:not|no|isn't|never)\s+(?:a\s+)?$", prefix, re.IGNORECASE):
                    failures["answer"].append("Deposit-only refund incorrectly described as a full rental refund")
    if case.get("expected_ineligible"):
        if not refunds or not isinstance(refunds[-1]["result"], dict) or "cannot" not in refunds[-1]["result"].get("message", ""):
            failures["tools"].append("Expected an ineligible cancellation result")
    if case.get("expected_not_found"):
        if not any(isinstance(call["result"], dict) and call["result"].get("result") == "not_found" for call in calls):
            failures["tools"].append("Expected not_found tool result")

    if run["elapsed_seconds"] > case["max_seconds"]:
        failures["runtime"].append(f"Latency exceeds {case['max_seconds']} seconds")
    if run["requests"] > case["max_requests"]:
        failures["runtime"].append("Too many model responses")
    if len(calls) > case["max_tool_calls"]:
        failures["runtime"].append("Too many tool calls")
    counts = Counter((call["tool"], json.dumps(call["args"], sort_keys=True)) for call in calls)
    repeated = sum(count - 1 for count in counts.values())
    if repeated > case["max_repeated_calls"]:
        failures["runtime"].append(f"Repeated identical tool calls: {repeated}")
    return failures
