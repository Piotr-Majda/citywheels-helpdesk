"""Structured policy documents and deterministic lookup results."""

from typing import Literal

from pydantic import BaseModel


class PolicySection(BaseModel):
    topic: str
    content: str


class PolicyDocument(BaseModel):
    policy: str
    title: str
    source: str
    introduction: str
    sections: list[PolicySection]


class PolicyLookupError(BaseModel):
    result: Literal["invalid_policy", "invalid_topics"]
    message: str
    available: dict[str, list[str]]
