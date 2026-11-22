"""Small deterministic conclusions supported by selected policy quotations."""

import re


def age_refusal(question: str, quotes: list[str]) -> str | None:
    """Explain a clear electric-bike age refusal without generated policy facts.

    Only handle an unambiguous age and rental question. Derive the minimum from
    a selected source quote; keep the full quotation and its conditions alongside
    the conclusion. Other phrasings continue to receive the quoted policy.
    """
    text = question.lower()
    ages = re.findall(r"\b(\d{1,3})[ -]+years?[ -]+old\b", text)
    if (len(ages) != 1 or not re.search(r"\belectric[ -]+bikes?\b", text)
            or not re.search(r"\brent(?:al)?\b", text)):
        return None
    minimums = {
        int(match)
        for quote in quotes
        for match in re.findall(r"\belectric bikes?:\s*from (\d{1,3}) years old\b", quote.lower())
    }
    if len(minimums) != 1:
        return None
    minimum = minimums.pop()
    age = int(ages[0])
    if age < minimum:
        return f"No. A {age}-year-old cannot rent an electric bike; the minimum age is {minimum}."
    # Meeting the age minimum alone does not establish eligibility to rent.
    return None
