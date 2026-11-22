"""Manager -> validated plan -> narrow specialists -> checked evidence -> answer."""

import asyncio
from dataclasses import dataclass
import json
import re

from pydantic_ai import Agent, NativeOutput
from pydantic_ai.models import Model

from app.context import AgentDependencies, EvidenceError, RunState, WorkflowResult
from app.models.booking import BookingNotFound, BookingRead
from app.models.policy import PolicyDocument
from app.models.workflow import PolicySummary, RoutePlan, route_schema
from app.prompts import MANAGER, SUMMARIZER
from app.specialists import MODEL_SETTINGS, SpecialistContext, build_specialist
from app.tools import list_policy_topics
from app.tools.calculate_refund import BookingStatusNotConfirmed, CalculateRefundResult


STAFF = "Please contact our staff at help@citywheels.example."
OUT_OF_SCOPE = "I can only help with CityWheels bike rentals. " + STAFF


def validate_plan(plan: RoutePlan, question: str) -> None:
    """Prevent routing to IDs that were never supplied by the customer."""
    ids = set(re.findall(r"\bCW-\d+\b", question.upper()))
    for task in plan.tasks:
        if task.booking_id is not None and task.booking_id not in ids:
            raise EvidenceError("Manager selected a booking ID absent from the question")


def policy_text(document: PolicyDocument) -> str:
    return document.introduction + "\n".join(
        f"## {section.topic}\n{section.content}" for section in document.sections
    )


def validate_summary(summary: PolicySummary, evidence: list[dict]) -> None:
    """Only exact retrieved excerpts can appear in the final policy summary.

    This prevents fabricated/paraphrased facts, but does not prove the model
    selected the best topic or included every relevant condition.
    """
    sources = {item["source_id"]: item["text"].replace("\r\n", "\n") for item in evidence}
    cited = set()
    for citation in summary.citations:
        quote = citation.quote.replace("\r\n", "\n").strip()
        if citation.source_id not in sources or not quote or quote not in sources[citation.source_id]:
            raise EvidenceError("Manager citation is not an exact retrieved quote")
        cited.add(citation.source_id)
    if cited != set(sources):
        raise EvidenceError("Manager summary did not cite every requested source")


def render_booking(record, booking_id: str) -> str:
    if isinstance(record, BookingNotFound):
        return f"Booking {booking_id} was not found. {STAFF}"
    if isinstance(record, BookingStatusNotConfirmed):
        return record.message + ". No additional cancellation refund is due."
    if isinstance(record, CalculateRefundResult):
        method = "Rental refund goes to the original card." if record.paid_with == "card" else "Rental refund is a new voucher, not cash."
        return (
            f"Booking {booking_id}. Total refund: {record.refund} EUR. "
            f"Rental refund: {record.rental_refund} EUR. Deposit refund: {record.deposit_refund} EUR. "
            f"Booking fee retained: {record.booking_fee_retained} EUR. "
            + ("There is no rental refund; only the deposit is returned. " if record.rental_refund == 0 else "")
            + method + " The deposit follows its original payment method."
        )
    if isinstance(record, BookingRead):
        return (
            f"Booking {record.id}: {record.status.value}. Bikes: {record.bikes} {record.bike_type}. "
            f"Start: {record.start.isoformat()}. End: {record.end.isoformat()}. "
            f"Add-ons: {', '.join(record.add_ons) or 'none'}. "
            f"Rental price: {record.rental_price_eur} EUR. Booking fee: {record.booking_fee_eur} EUR. "
            f"Deposit: {record.deposit_eur} EUR. Paid with: {record.paid_with}."
        )
    raise EvidenceError("Unexpected booking evidence type")


@dataclass
class HelpDeskWorkflow:
    model: Model

    async def run(self, question: str, state: RunState) -> WorkflowResult:
        policy_evidence = []
        rendered = []
        try:
            async with asyncio.timeout(state.timeout):
                manager = Agent(self.model, name="manager_router", instructions=MANAGER,
                                output_type=NativeOutput(route_schema(question)), retries=0, model_settings=MODEL_SETTINGS)
                plan = await state.run(manager, question, "manager_route")
                validate_plan(plan, question)
                if plan.scope == "unsupported":
                    return WorkflowResult(OUT_OF_SCOPE, state)
                if plan.scope == "clarify":
                    return WorkflowResult("Please provide your booking ID or clarify your CityWheels question. " + STAFF, state)

                catalogue = None
                for task in plan.tasks:
                    if task.kind == "policy" and catalogue is None:
                        catalogue = state.execute(
                            "list_policy_topics", {},
                            lambda: list_policy_topics(policy_loader=state.deps.policy_loader), origin="application",
                        )
                    if task.kind == "policy" and task.policy not in (catalogue or {}):
                        raise EvidenceError("Assigned policy is unavailable")
                    context = SpecialistContext(state, task, catalogue)
                    assignment = task.model_dump(mode="json")
                    if task.kind == "policy":
                        assignment["available_topics"] = catalogue[task.policy]
                    prompt = json.dumps({"question": question, "assignment": assignment})
                    record = await state.run(build_specialist(self.model, task, catalogue), prompt,
                                             f"{task.kind}_specialist", deps=context)
                    source_id = f"{task.kind}:{task.policy or task.booking_id}"
                    if task.kind == "policy":
                        if not isinstance(record, PolicyDocument) or record.policy != task.policy or not record.sections:
                            raise EvidenceError("Policy specialist returned no retrieved sections")
                        item = {"source_id": source_id, "source": record.source,
                                "text": policy_text(record), "topics": [section.topic for section in record.sections]}
                        policy_evidence.append(item)
                    else:
                        expected = (BookingRead, BookingNotFound) if task.kind == "booking" else (
                            CalculateRefundResult, BookingNotFound, BookingStatusNotConfirmed)
                        if not isinstance(record, expected):
                            raise EvidenceError("Specialist returned no verified booking evidence")
                        item = {"source_id": source_id, "data": record.model_dump(mode="json")}
                        rendered.append(render_booking(record, task.booking_id))
                    state.evidence.append(item)

                if policy_evidence:
                    summarizer = Agent(self.model, name="manager_summarizer", instructions=SUMMARIZER,
                                       output_type=NativeOutput(PolicySummary), retries=0, model_settings=MODEL_SETTINGS)
                    summary = await state.run(
                        summarizer, json.dumps({"question": question, "evidence": policy_evidence}), "manager_summary",
                    )
                    validate_summary(summary, policy_evidence)
                    references = []
                    for citation in summary.citations:
                        source = next(item for item in policy_evidence if item["source_id"] == citation.source_id)
                        references.append(f"Source: {source['source']} ({', '.join(source['topics'])})\n> {citation.quote}")
                    introductions = []
                    for task_record in state.calls:
                        if task_record["tool"] == "search_policies" and task_record["returned"]:
                            introduction = task_record["result"].get("introduction", "").strip()
                            if introduction and introduction not in introductions:
                                introductions.append(introduction)
                    rendered.insert(0, "Policy information:\n" + "\n".join(introductions + references) + "\n" + STAFF)
                return WorkflowResult("\n\n".join(rendered), state)
        except Exception as error:
            # Fail closed: no unchecked model answer and no silent partial success.
            return WorkflowResult(
                "I could not verify a complete answer from the shop data. " + STAFF,
                state, error=type(error).__name__, guard_failures=[str(error)] if isinstance(error, EvidenceError) else [],
            )


def build_agent(model: Model) -> HelpDeskWorkflow:
    return HelpDeskWorkflow(model)


def ask(
    agent: HelpDeskWorkflow, question: str, *, deps: AgentDependencies | None = None,
    timeout: float = 180, request_limit: int = 6, tool_calls_limit: int = 8,
) -> WorkflowResult:
    if not question.strip():
        raise ValueError("Question must not be empty")
    if timeout <= 0 or request_limit <= 0 or tool_calls_limit <= 0:
        raise ValueError("Execution limits must be positive")
    state = RunState(deps if deps is not None else AgentDependencies(), timeout, request_limit, tool_calls_limit)
    return asyncio.run(agent.run(question, state))
