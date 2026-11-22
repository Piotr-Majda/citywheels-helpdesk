"""Per-question dependencies, audit events, and a shared execution budget."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
from time import perf_counter

from pydantic_ai import RunUsage, UsageLimits, capture_run_messages
from pydantic_ai.messages import ModelResponse

from app.db.booking_loader import BookingLoader, load_booking
from app.db.policy_loader import PolicyLoader, load_policies
from app.tools.calculate_refund import ASSIGNMENT_NOW


class EvidenceError(ValueError):
    """The workflow cannot support an answer with verified tool evidence."""


@dataclass
class AgentDependencies:
    booking_loader: BookingLoader = load_booking
    policy_loader: PolicyLoader = load_policies
    cancellation_time: datetime = ASSIGNMENT_NOW


@dataclass
class RunState:
    deps: AgentDependencies
    timeout: float
    request_limit: int
    tool_limit: int
    started: float = field(default_factory=perf_counter)
    usage: RunUsage = field(default_factory=RunUsage)
    calls: list[dict] = field(default_factory=list)
    stages: list[dict] = field(default_factory=list)
    messages: list = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    selections: set = field(default_factory=set)

    def execute(self, name: str, args: dict, operation: Callable, *, origin: str):
        """Record real business-tool execution, including application-forced calls."""
        if len(self.calls) >= self.tool_limit:
            raise EvidenceError("Shared business-tool budget exceeded")
        key = (name, json.dumps(args, sort_keys=True))
        if key in self.selections:
            raise EvidenceError("Repeated identical tool call blocked")
        self.selections.add(key)
        call = {"tool": name, "args": args, "origin": origin,
                "call_id": f"execution-{len(self.calls) + 1}", "returned": False,
                "result": None, "retry": False}
        self.calls.append(call)
        started = perf_counter()
        try:
            result = operation()
            call["result"] = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
            call["returned"] = True
            return result
        except (OSError, ValueError, TypeError) as error:
            call.update(returned=True, result={"result": "data_unavailable", "error": type(error).__name__})
            raise EvidenceError("Source data unavailable or invalid") from error
        finally:
            call["elapsed_seconds"] = round(perf_counter() - started, 6)

    async def run(self, agent, prompt: str, phase: str, *, deps=None):
        """Fresh context per stage; share usage and remaining time across agents."""
        remaining = self.timeout - (perf_counter() - self.started)
        if remaining <= 0:
            raise TimeoutError("Shared workflow deadline exceeded")
        stage = {"phase": phase, "error": None}
        self.stages.append(stage)
        started = perf_counter()
        requests_before = self.usage.requests
        with capture_run_messages() as messages:
            try:
                result = await agent.run(
                    prompt, deps=deps, usage=self.usage,
                    usage_limits=UsageLimits(request_limit=self.request_limit, tool_calls_limit=self.tool_limit),
                    timeout=remaining,
                )
                output = result.output
                stage["output"] = output.model_dump(mode="json") if hasattr(output, "model_dump") else str(type(output).__name__)
                return output
            except BaseException as error:
                stage["error"] = type(error).__name__
                raise
            finally:
                self.messages.extend(messages)
                stage["model_responses"] = [
                    [{"kind": part.part_kind, "tool": getattr(part, "tool_name", None),
                      "content": getattr(part, "content", None), "args": getattr(part, "args", None)}
                     for part in message.parts]
                    for message in messages if isinstance(message, ModelResponse)
                ]
                stage["requests"] = self.usage.requests - requests_before
                stage["elapsed_seconds"] = round(perf_counter() - started, 3)


@dataclass
class WorkflowResult:
    output: str
    state: RunState
    error: str | None = None
    guard_failures: list[str] = field(default_factory=list)

    @property
    def usage(self):
        return self.state.usage

    @property
    def calls(self):
        return self.state.calls

    @property
    def stages(self):
        return self.state.stages

    def all_messages(self):
        return self.state.messages
