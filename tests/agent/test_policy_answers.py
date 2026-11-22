import pytest

from app.policy_answers import age_refusal


@pytest.mark.parametrize("question, quotes, expected", [
    ("Can my 14-year-old rent an electric bike?", ["Electric bikes: from 16 years old."],
     "No. A 14-year-old cannot rent an electric bike; the minimum age is 16."),
    ("Can a 15 year old rent an electric bike?", ["Electric bikes: from 18 years old."],
     "No. A 15-year-old cannot rent an electric bike; the minimum age is 18."),
    ("Can my 16-year-old rent an electric bike?", ["Electric bikes: from 16 years old."], None),
    ("Can my 18-year-old rent an electric bike?", ["Electric bikes: from 16 years old."], None),
    ("Can my 14-year-old rent a city bike?", ["Electric bikes: from 16 years old."], None),
    ("Does my 14-year-old need a helmet on an electric bike?", ["Electric bikes: from 16 years old."], None),
    ("Can my child rent an electric bike?", ["Electric bikes: from 16 years old."], None),
    ("Can my 14-year-old rent an electric bike?", ["City bikes: from 13 years old."], None),
    ("Can my 14-year-old rent an electric bike?", [], None),
    ("Can my 14-year-old and 17-year-old rent an electric bike?", ["Electric bikes: from 16 years old."], None),
    ("Can my 14-year-old rent an electric bike?", ["Electric bikes: from 16 years old.",
                                              "Electric bikes: from 18 years old."], None),
])
def test_age_conclusion_requires_unambiguous_question_and_selected_rule(question, quotes, expected):
    assert age_refusal(question, quotes) == expected
