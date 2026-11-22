"""Deterministic topic discovery and exact Markdown retrieval."""

import pytest

from app.db.policy_loader import load_policies, parse_policy
from app.models.policy import PolicyDocument, PolicyLookupError
from app.tools.search_policies import list_policy_topics, search_policies


INTRODUCTION = "\nAll prices are in EUR, including VAT.\n\n"
RENTAL_BODY = "\n| Bike | Price |\n| --- | --- |\n| City | 20 EUR |\n\n### Details\n- Per day.\n\n"
FEE_BODY = "\nOnline: 2 EUR. In shop: free.\n"
TEXT = "# Prices\n" + INTRODUCTION + "## Bike rental\n" + RENTAL_BODY + "## Booking fee\n" + FEE_BODY


@pytest.fixture
def policies():
    return {
        "prices": parse_policy(TEXT, policy="prices", source="data/policies/prices.md"),
        "faq": parse_policy(
            "# FAQ\n\n## When are you open?\n\n08:00–20:00.\n",
            policy="faq", source="data/policies/faq.md",
        ),
    }


def test_catalogue_contains_exact_topics(policies):
    assert list_policy_topics(policy_loader=lambda: policies) == {
        "prices": ["Bike rental", "Booking fee"],
        "faq": ["When are you open?"],
    }


def test_multiple_sections_with_sources(policies):
    result = search_policies(
        "prices", ["Bike rental", "Booking fee"], policy_loader=lambda: policies,
    )
    assert isinstance(result, PolicyDocument)
    assert result.policy == "prices"
    assert result.title == "Prices"
    assert result.source == "data/policies/prices.md"
    assert result.introduction == INTRODUCTION
    assert [section.content for section in result.sections] == [RENTAL_BODY, FEE_BODY]


def test_request_order_and_no_extra_sections(policies):
    result = search_policies("prices", ["Booking fee"], policy_loader=lambda: policies)
    assert [section.topic for section in result.sections] == ["Booking fee"]
    result = search_policies(
        "prices", ["Booking fee", "Bike rental"], policy_loader=lambda: policies,
    )
    assert [section.topic for section in result.sections] == ["Booking fee", "Bike rental"]
    assert len(policies["prices"].sections) == 2


@pytest.mark.parametrize("policy", ["unknown", "Prices", "../bookings.json", ""])
def test_invalid_policy_returns_choices(policies, policy):
    result = search_policies(policy, ["Bike rental"], policy_loader=lambda: policies)
    assert isinstance(result, PolicyLookupError)
    assert result.result == "invalid_policy"
    assert result.available == list_policy_topics(policy_loader=lambda: policies)


@pytest.mark.parametrize("topics", [[], ["bike rental"], ["Unknown"],
    ["Bike rental", "Unknown"], ["Bike rental", "Bike rental"]])
def test_invalid_topics_return_no_partial_result(policies, topics):
    result = search_policies("prices", topics, policy_loader=lambda: policies)
    assert isinstance(result, PolicyLookupError)
    assert result.result == "invalid_topics"
    assert result.available["prices"] == ["Bike rental", "Booking fee"]


def test_injected_sources_are_independent(policies):
    assert list_policy_topics(policy_loader=lambda: {}) == {}
    assert "prices" in list_policy_topics(policy_loader=lambda: policies)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_loader_preserves_original_content(tmp_path, newline):
    text = TEXT.replace("\n", newline)
    path = tmp_path / "prices.md"
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text)
    document = load_policies(tmp_path)["prices"]
    assert document.introduction == INTRODUCTION.replace("\n", newline)
    assert document.sections[0].content == RENTAL_BODY.replace("\n", newline)
    assert document.sections[1].content == FEE_BODY.replace("\n", newline)


@pytest.mark.parametrize("marker", ["```", "~~~"])
def test_fenced_headings_are_preserved_not_indexed(marker):
    body = f"\n{marker}text\n## Not a topic\n# Not a title\n{marker}\n"
    document = parse_policy(
        "# Title\n## Real topic\n" + body, policy="example", source="example.md",
    )
    assert [section.topic for section in document.sections] == ["Real topic"]
    assert document.sections[0].content == body


@pytest.mark.parametrize("text", ["", "## Topic\nBody", "# Title\nBody",
    "# Title\n## Topic\nOne\n## Topic\nTwo",
    "# Title\n## Topic\nBody\n# Another title\n"])
def test_invalid_documents_raise_data_error(text):
    with pytest.raises(ValueError):
        parse_policy(text, policy="invalid", source="invalid.md")


def test_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_policies(tmp_path / "missing")


def test_loader_orders_files_and_ignores_other_extensions(tmp_path):
    (tmp_path / "z.md").write_text("# Z\n## Topic\nZ", encoding="utf-8")
    (tmp_path / "a.md").write_text("# A\n## Topic\nA", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("Not a policy", encoding="utf-8")
    assert list(load_policies(tmp_path)) == ["a", "z"]


def test_source_error_propagates():
    def failing_loader():
        raise OSError("Source unavailable")

    with pytest.raises(OSError, match="Source unavailable"):
        list_policy_topics(policy_loader=failing_loader)
    with pytest.raises(OSError, match="Source unavailable"):
        search_policies("prices", ["Bike rental"], policy_loader=failing_loader)
