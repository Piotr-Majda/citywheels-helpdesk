"""Strict policy/topic lookup. No fuzzy matching, ranking, or generated text."""

from app.db.policy_loader import PolicyLoader, load_policies
from app.models.policy import PolicyDocument, PolicyLookupError


def list_policy_topics(
    *, policy_loader: PolicyLoader = load_policies,
) -> dict[str, list[str]]:
    """List exact policy IDs and topic headings accepted by search_policies."""
    return {
        name: [section.topic for section in document.sections]
        for name, document in policy_loader().items()
    }


def search_policies(
    policy: str,
    topics: list[str],
    *,
    policy_loader: PolicyLoader = load_policies,
) -> PolicyDocument | PolicyLookupError:
    """Return exact sections for one policy and a nonempty list of exact topics.

    Call list_policy_topics first. Names are case-sensitive. Unknown policies,
    unknown topics, empty selections, and repeated topics return a structured
    error with valid choices; no partial answer is returned. Requested order is
    preserved. The application injects the loader, not the model.
    """
    documents = policy_loader()
    available = {
        name: [section.topic for section in document.sections]
        for name, document in documents.items()
    }
    if policy not in documents:
        return PolicyLookupError(
            result="invalid_policy", message=f"Unknown policy: {policy}",
            available=available,
        )
    document = documents[policy]
    sections = {section.topic: section for section in document.sections}
    if not topics or len(set(topics)) != len(topics) or any(topic not in sections for topic in topics):
        return PolicyLookupError(
            result="invalid_topics",
            message="Choose one or more distinct, exact topics from the catalogue.",
            available=available,
        )
    return document.model_copy(update={"sections": [sections[topic] for topic in topics]})
