"""Narrow specialists whose only possible successful output executes their tool."""

from dataclasses import dataclass
from typing import Literal

from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput

from app.context import EvidenceError, RunState
from app.models.policy import PolicyDocument, PolicyLookupError
from app.models.workflow import SpecialistTask
from app.prompts import BOOKING_SPECIALIST, POLICY_SPECIALIST, REFUND_SPECIALIST
from app.tools import get_booking as lookup_booking
from app.tools import search_policies as lookup_policies
from app.tools.calculate_refund import calculate_refund as quote_refund


MODEL_SETTINGS = {"temperature": 0, "max_retries": 0, "timeout": 120, "max_tokens": 1024}


@dataclass
class SpecialistContext:
    state: RunState
    task: SpecialistTask
    catalogue: dict[str, list[str]] | None = None


def build_specialist(model, task: SpecialistTask, catalogue=None) -> Agent:
    kind = task.kind
    def get_booking(ctx: RunContext[SpecialistContext], booking_id: str):
        """Retrieve the assigned booking by its exact booking_id."""
        if booking_id != ctx.deps.task.booking_id:
            raise ModelRetry("Use the assigned booking_id exactly")
        return ctx.deps.state.execute(
            "get_booking", {"booking_id": booking_id},
            lambda: lookup_booking(booking_id, booking_loader=ctx.deps.state.deps.booking_loader), origin="model",
        )

    def calculate_refund(ctx: RunContext[SpecialistContext], booking_id: str):
        """Calculate the refund for the assigned booking_id."""
        if booking_id != ctx.deps.task.booking_id:
            raise ModelRetry("Use the assigned booking_id exactly")
        return ctx.deps.state.execute(
            "calculate_refund", {"booking_id": booking_id},
            lambda: quote_refund(booking_id, cancellation_time=ctx.deps.state.deps.cancellation_time,
                                 booking_loader=ctx.deps.state.deps.booking_loader), origin="model",
        )

    def search_policies(ctx: RunContext[SpecialistContext], policy: str, topics: list[str]):
        """Retrieve relevant exact topics from the assigned policy's catalogue."""
        if policy != ctx.deps.task.policy:
            raise ModelRetry("Use the assigned policy ID exactly")
        catalogue = ctx.deps.catalogue or {}
        if not topics or len(set(topics)) != len(topics) or any(topic not in catalogue.get(policy, []) for topic in topics):
            raise ModelRetry(f"Choose distinct exact topics from {catalogue.get(policy, [])}")
        result = ctx.deps.state.execute(
            "search_policies", {"policy": policy, "topics": topics},
            lambda: lookup_policies(policy, topics, policy_loader=ctx.deps.state.deps.policy_loader), origin="model",
        )
        if isinstance(result, PolicyLookupError) or not isinstance(result, PolicyDocument):
            raise EvidenceError("No policy evidence returned")
        return result

    tools = {"policy": (search_policies, POLICY_SPECIALIST),
             "booking": (get_booking, BOOKING_SPECIALIST),
             "refund": (calculate_refund, REFUND_SPECIALIST)}
    function, instructions = tools[kind]
    # Show the model exact choices in its native tool schema, not only prose.
    # Pydantic also rejects values outside these per-assignment enums.
    if kind == "policy":
        search_policies.__annotations__["policy"] = Literal[task.policy]
        search_policies.__annotations__["topics"] = list[Literal[tuple((catalogue or {})[task.policy])]]
    else:
        function.__annotations__["booking_id"] = Literal[task.booking_id]
    # Output functions force a native tool call; prose cannot finish a specialist.
    # Results go directly to Python/manager, avoiding an unused model paraphrase.
    return Agent(
        model, name=f"{kind}_specialist", deps_type=SpecialistContext,
        instructions=instructions, retries=1, model_settings=MODEL_SETTINGS,
        output_type=ToolOutput(function, name=function.__name__, sequential=True),
    )
