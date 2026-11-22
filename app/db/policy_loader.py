"""Load local Markdown policies without ranking or rewriting their contents."""

from collections.abc import Callable, Mapping
from pathlib import Path
import re

from app.models.policy import PolicyDocument, PolicySection


POLICIES_PATH = Path(__file__).resolve().parents[2] / "data" / "policies"


def parse_policy(text: str, *, policy: str, source: str) -> PolicyDocument:
    """Parse ATX # title and ## topics; preserve section bodies verbatim.

    Nested headings stay in their section. Headings inside fenced code blocks
    are ignored. This parser targets the supplied policy format, not all Markdown.
    """
    headings = []
    offset = 0
    fence_character = None
    fence_length = 0
    for line in text.splitlines(keepends=True):
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence:
            marker, suffix = fence.groups()
            if fence_character is None:
                fence_character, fence_length = marker[0], len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length and not suffix.strip():
                fence_character = None
        elif fence_character is None:
            heading = re.match(r"^(#{1,2})[ \t]+(.+?)\s*$", line)
            if heading:
                headings.append((len(heading[1]), heading[2], offset, offset + len(line)))
        offset += len(line)

    if not headings or headings[0][0] != 1:
        raise ValueError(f"Policy {policy} must start with a # title")
    if any(level == 1 for level, *_ in headings[1:]):
        raise ValueError(f"Policy {policy} must have only one # title")
    if len(headings) == 1:
        raise ValueError(f"Policy {policy} has no ## topics")

    sections = []
    seen = set()
    for index, (_, topic, _, body_start) in enumerate(headings[1:], start=1):
        if topic in seen:
            raise ValueError(f"Duplicate topic in {policy}: {topic}")
        seen.add(topic)
        body_end = headings[index + 1][2] if index + 1 < len(headings) else len(text)
        sections.append(PolicySection(topic=topic, content=text[body_start:body_end]))

    return PolicyDocument(
        policy=policy,
        title=headings[0][1],
        source=source,
        introduction=text[headings[0][3]:headings[1][2]],
        sections=sections,
    )


def load_policies(path: Path = POLICIES_PATH) -> dict[str, PolicyDocument]:
    """Load all .md documents in filename order; source errors propagate."""
    if not path.is_dir():
        raise FileNotFoundError(f"Policy directory not found: {path}")
    documents = {}
    for file in sorted(path.glob("*.md")):
        # Disable newline conversion to preserve the original Markdown bodies.
        with file.open(encoding="utf-8", newline="") as stream:
            documents[file.stem] = parse_policy(
                stream.read(), policy=file.stem, source=f"data/policies/{file.name}"
            )
    return documents


PolicyLoader = Callable[[], Mapping[str, PolicyDocument]]
