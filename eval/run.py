"""Run from the repository root: uv run python -m eval.run."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter

from pydantic_ai import capture_run_messages
from pydantic_ai.messages import ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

from app.agent import ask, build_agent
from app.config import Settings
from app.tools.search_policies import list_policy_topics
from eval.checks import validate


ROOT = Path(__file__).resolve().parents[1]


def source_metadata(*, command=subprocess.check_output):
    """A packaged image has no Git executable/history; never invent a revision."""
    try:
        commit = command(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(command(["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL))
        return {"git_commit": commit, "working_tree_dirty": dirty, "git_metadata_available": True}
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "working_tree_dirty": None, "git_metadata_available": False}


def extract_calls(messages):
    calls = []
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                calls.append({"tool": part.tool_name, "args": part.args_as_dict(),
                              "call_id": part.tool_call_id, "result": None,
                              "returned": False, "retry": False})
            elif isinstance(part, (ToolReturnPart, RetryPromptPart)):
                for call in reversed(calls):
                    if call["call_id"] == part.tool_call_id and not call["returned"]:
                        call.update(result=part.content, returned=True,
                                    retry=isinstance(part, RetryPromptPart))
                        break
    return calls


def run_case(agent, case, catalogue):
    started = perf_counter()
    answer, error, usage = "", None, None
    workflow = None
    with capture_run_messages() as messages:
        try:
            result = ask(
                agent, case["question"], timeout=case["timeout_seconds"],
                request_limit=case["max_requests"], tool_calls_limit=case["max_tool_calls"],
            )
            answer, usage = result.output, result.usage
            if hasattr(result, "calls"):
                workflow = result
                error = result.error
                messages = result.all_messages()
        except Exception as exception:
            # Record failure type without potentially sensitive provider payloads.
            error = type(exception).__name__
    run = {
        "id": case["id"], "question": case["question"], "answer": answer,
        "error": error, "elapsed_seconds": round(perf_counter() - started, 3),
        "requests": usage.requests if usage else sum(isinstance(message, ModelResponse) for message in messages),
        "tokens": usage.total_tokens if usage else None,
        "calls": workflow.calls if workflow is not None else extract_calls(messages),
        "model_tool_calls": extract_calls(messages),
        "stages": workflow.stages if workflow is not None else [],
        "guard_failures": workflow.guard_failures if workflow is not None else [],
    }
    run["failures"] = validate(case, run, catalogue)
    run["passed"] = not any(run["failures"].values())
    return run


def write_report(metadata, runs, output):
    output.mkdir(parents=True, exist_ok=True)
    payload = {"metadata": metadata, "passed": sum(run["passed"] for run in runs),
               "completed": len(runs), "results": runs}
    (output / "results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    lines = ["# Real-model evaluation", "", f"Passed: **{payload['passed']}/{len(runs)}** completed cases.", "",
             "```json", json.dumps(metadata, indent=2), "```", "",
             "Overall pass requires answer, tool, and runtime checks all to pass.",
             "The 60-second target is a project benchmark, not an assignment requirement.",
             "Each case is a fresh conversation. Model/OS caches remain warm after earlier cases; no warm-up is excluded.",
             "Checks use explicit patterns, expected tool arguments/results, and limits, not an LLM judge.",
             "They do not prove semantic correctness or detect every contradiction. Review the included answers and traces.", "",
             "| Case | Answer | Tools | Runtime | Seconds | Requests | Calls |",
             "| --- | --- | --- | --- | ---: | ---: | ---: |"]
    for run in runs:
        flags = ["FAIL" if run["failures"][group] else "PASS" for group in ("answer", "tools", "runtime")]
        lines.append(f"| {run['id']} | {' | '.join(flags)} | {run['elapsed_seconds']:.3f} | {run['requests']} | {len(run['calls'])} |")
    if runs:
        times = [run["elapsed_seconds"] for run in runs]
        lines += ["", f"Latency: median {statistics.median(times):.3f}s; maximum {max(times):.3f}s."]
    for run in runs:
        lines += ["", f"## {run['id']}", "", run["question"], "", "Answer:", ""]
        lines += [("> " + line).rstrip() for line in (run["answer"] or "(No final answer)").splitlines()]
        lines += ["", "Failures:", "```json", json.dumps(run["failures"], indent=2), "```", "",
                  "Tool trace (includes exact arguments and returned data):", "```json",
                  json.dumps(run["calls"], indent=2, ensure_ascii=False, default=str), "```"]
        if "stages" in run:
            lines += ["", "Agent stages (separate contexts, shared budget):", "```json",
                      json.dumps(run["stages"], indent=2, ensure_ascii=False, default=str), "```",
                      "", "All model tool-call attempts (including rejected arguments):", "```json",
                      json.dumps(run.get("model_tool_calls", []), indent=2, ensure_ascii=False, default=str), "```"]
    (output / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "eval/cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "eval")
    args = parser.parse_args()
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    cases_bytes = args.cases.read_bytes()
    cases = json.loads(cases_bytes)
    settings = Settings.from_env()
    catalogue = list_policy_topics()
    agent = build_agent(settings.create_model())
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "provider": settings.provider, "model": settings.model,
        "base_url": settings.ollama_base_url if settings.provider == "ollama" else "provider default",
        "pydantic_ai_version": version("pydantic-ai-slim"),
        **source_metadata(),
        "cases_sha256": hashlib.sha256(cases_bytes).hexdigest(),
        "checks_sha256": hashlib.sha256((ROOT / "eval/checks.py").read_bytes()).hexdigest(),
        "app_sha256": hashlib.sha256(b"".join(file.relative_to(ROOT).as_posix().encode() + file.read_bytes()
                                             for file in sorted((ROOT / "app").rglob("*.py")))).hexdigest(),
        "case_count": len(cases), "temperature": 0, "provider_retries": 0,
        "architecture": "manager-specialists-v1",
        "max_output_tokens_per_request": 1024,
        "fixed_now": "2026-06-10T09:00:00+02:00",
        "limits": {case["id"]: {key: case[key] for key in ("max_seconds", "timeout_seconds", "max_requests", "max_tool_calls", "max_repeated_calls")} for case in cases},
    }
    runs = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']} ...", flush=True)
        run = run_case(agent, case, catalogue)
        runs.append(run)
        write_report(metadata, runs, args.output)
        print(f"  {'PASS' if run['passed'] else 'FAIL'} {run['elapsed_seconds']:.2f}s "
              f"requests={run['requests']} calls={len(run['calls'])} failures={run['failures']}", flush=True)
    print(f"Passed {sum(run['passed'] for run in runs)}/{len(runs)}. Results: {args.output / 'results.md'}")
    return 0 if all(run["passed"] for run in runs) else 1


if __name__ == "__main__":
    sys.exit(main())
