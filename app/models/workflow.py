"""Validated manager plans and source references."""

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator


class SpecialistTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["policy", "booking", "refund"]
    policy: Literal["prices", "faq", "cancellations"] | None = None
    booking_id: str | None = None

    @model_validator(mode="after")
    def coherent_task(self) -> Self:
        if self.kind == "policy":
            if self.policy is None or self.booking_id is not None:
                raise ValueError("Policy tasks require only a policy ID")
        elif not self.booking_id or self.policy is not None:
            raise ValueError("Booking/refund tasks require only a booking ID")
        return self


class RoutePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: Literal["supported", "unsupported", "clarify"]
    policies: list[Literal["prices", "faq", "cancellations"]] = Field(default_factory=list, max_length=3)
    bookings: list[str] = Field(default_factory=list, max_length=2)
    refunds: list[str] = Field(default_factory=list, max_length=2)

    @property
    def tasks(self) -> list[SpecialistTask]:
        return ([SpecialistTask(kind="policy", policy=policy) for policy in self.policies]
                + [SpecialistTask(kind="booking", booking_id=booking_id) for booking_id in self.bookings]
                + [SpecialistTask(kind="refund", booking_id=booking_id) for booking_id in self.refunds])

    @model_validator(mode="after")
    def coherent_scope(self) -> Self:
        if (self.scope == "supported") != bool(self.tasks):
            raise ValueError("Only supported plans have tasks; supported plans must have tasks")
        if len(self.tasks) > 4:
            raise ValueError("At most four specialist tasks are allowed")
        keys = [(task.kind, task.policy, task.booking_id) for task in self.tasks]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate tasks are not allowed")
        return self


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    quote: str = Field(min_length=1)


class PolicySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    citations: list[Citation] = Field(min_length=1)


def route_schema(question: str) -> type[RoutePlan]:
    """Restrict manager ID selections to actual IDs from this question."""
    ids = tuple(sorted(set(re.findall(r"\bCW-\d+\b", question.upper()))))
    choices = list[Literal[ids]] if ids else list[str]
    maximum = min(2, len(ids))
    return create_model(
        "QuestionRoutePlan", __base__=RoutePlan,
        bookings=(choices, Field(default_factory=list, max_length=maximum,
                                 description="Exact customer booking IDs for detail lookups; never booking facts")),
        refunds=(choices, Field(default_factory=list, max_length=maximum,
                                description="Exact customer booking IDs for cancellation amounts or eligibility")),
    )
