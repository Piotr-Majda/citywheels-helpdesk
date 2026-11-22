# Real-model evaluation

Passed: **3/10** completed cases.

```json
{
  "started_utc": "2026-11-22T13:42:50.109764+00:00",
  "provider": "ollama",
  "model": "llama3.1:8b",
  "base_url": "http://localhost:11434/v1",
  "pydantic_ai_version": "2.71.0",
  "git_commit": "8c8b94be633c050b11c9bc5e1f8a9cd3f6f242d8",
  "working_tree_dirty": true,
  "cases_sha256": "fdfde8b172e7d848acba777947d420312159cab975afb187ad6913773ba8451a",
  "checks_sha256": "82948320a37ab0b3643669a95e5dc5e344956d5b3960617eefd55776d7d194b6",
  "app_sha256": "887eea16aea03234f4638dd1383554de0e7c2b52c46a46a303c4d671d037fddd",
  "case_count": 10,
  "temperature": 0,
  "provider_retries": 0,
  "architecture": "manager-specialists-v1",
  "fixed_now": "2026-06-10T09:00:00+02:00",
  "limits": {
    "opening_hours": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "ebike_price": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "age_limit": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "booking_details": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "half_refund": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "deposit_only": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "already_cancelled": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "unknown_booking": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "out_of_scope_geography": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    },
    "out_of_scope_recipe": {
      "max_seconds": 60,
      "timeout_seconds": 120,
      "max_requests": 5,
      "max_tool_calls": 4,
      "max_repeated_calls": 0
    }
  }
}
```

Overall pass requires answer, tool, and runtime checks all to pass.
The 60-second target is a project benchmark, not an assignment requirement.
Each case is a fresh conversation. Model/OS caches remain warm after earlier cases; no warm-up is excluded.
Checks use explicit patterns, expected tool arguments/results, and limits, not an LLM judge.
They do not prove semantic correctness or detect every contradiction. Review the included answers and traces.

| Case | Answer | Tools | Runtime | Seconds | Requests | Calls |
| --- | --- | --- | --- | ---: | ---: | ---: |
| opening_hours | PASS | PASS | PASS | 19.084 | 3 | 2 |
| ebike_price | FAIL | FAIL | FAIL | 5.313 | 1 | 0 |
| age_limit | FAIL | FAIL | PASS | 2.221 | 1 | 0 |
| booking_details | FAIL | FAIL | FAIL | 5.379 | 1 | 0 |
| half_refund | FAIL | FAIL | FAIL | 6.479 | 1 | 0 |
| deposit_only | FAIL | FAIL | FAIL | 7.204 | 1 | 0 |
| already_cancelled | FAIL | FAIL | FAIL | 5.634 | 1 | 0 |
| unknown_booking | FAIL | FAIL | PASS | 2.311 | 1 | 0 |
| out_of_scope_geography | PASS | PASS | PASS | 1.510 | 1 | 0 |
| out_of_scope_recipe | PASS | PASS | PASS | 2.022 | 1 | 0 |

Latency: median 5.346s; maximum 19.084s.

## opening_hours

What time are you open on Saturdays in June?

Answer:

> Policy information:
> Source: data/policies/faq.md (When are you open?)
> > April to October: every day, 08:00–20:00.
> Source: data/policies/faq.md (When are you open?)
> > November to March: Monday to Saturday, 09:00–17:00
> Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [],
  "tools": [],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[
  {
    "tool": "list_policy_topics",
    "args": {},
    "origin": "application",
    "call_id": "execution-1",
    "returned": true,
    "result": {
      "cancellations": [
        "Cancelling a booking",
        "How the money comes back",
        "Changing a booking",
        "Bad weather",
        "Contact the staff"
      ],
      "faq": [
        "When are you open?",
        "Where are you?",
        "What do I need to rent a bike?",
        "How can I pay?",
        "Are there age limits?",
        "Do I have to wear a helmet?",
        "Can I take my dog?",
        "Can I take the bike on a train or outside the city?",
        "What if the bike breaks or I have an accident?",
        "What if the bike is stolen or lost?",
        "Do you sell bikes?"
      ],
      "prices": [
        "Bike rental",
        "Add-ons",
        "Booking fee",
        "Deposit",
        "Late return"
      ]
    },
    "retry": false,
    "elapsed_seconds": 0.001949
  },
  {
    "tool": "search_policies",
    "args": {
      "policy": "faq",
      "topics": [
        "When are you open?"
      ]
    },
    "origin": "model",
    "call_id": "execution-2",
    "returned": true,
    "result": {
      "policy": "faq",
      "title": "Frequently asked questions",
      "source": "data/policies/faq.md",
      "introduction": "\r\n",
      "sections": [
        {
          "topic": "When are you open?",
          "content": "\r\n- April to October: every day, 08:00–20:00.\r\n- November to March: Monday to Saturday, 09:00–17:00. Closed on Sundays.\r\n- Closed on 25 and 26 December and on 1 January.\r\n\r\nBikes can only be picked up and returned while the shop is open.\r\n\r\n"
        }
      ]
    },
    "retry": false,
    "elapsed_seconds": 0.002036
  }
]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": null,
    "output": {
      "scope": "supported",
      "tasks": [
        {
          "kind": "policy",
          "policy": "faq",
          "booking_id": null
        }
      ]
    },
    "requests": 1,
    "elapsed_seconds": 4.559
  },
  {
    "phase": "policy_specialist",
    "error": null,
    "output": {
      "policy": "faq",
      "title": "Frequently asked questions",
      "source": "data/policies/faq.md",
      "introduction": "\r\n",
      "sections": [
        {
          "topic": "When are you open?",
          "content": "\r\n- April to October: every day, 08:00–20:00.\r\n- November to March: Monday to Saturday, 09:00–17:00. Closed on Sundays.\r\n- Closed on 25 and 26 December and on 1 January.\r\n\r\nBikes can only be picked up and returned while the shop is open.\r\n\r\n"
        }
      ]
    },
    "requests": 1,
    "elapsed_seconds": 2.884
  },
  {
    "phase": "manager_summary",
    "error": null,
    "output": {
      "citations": [
        {
          "source_id": "policy:faq",
          "quote": "April to October: every day, 08:00–20:00."
        },
        {
          "source_id": "policy:faq",
          "quote": "November to March: Monday to Saturday, 09:00–17:00"
        }
      ]
    },
    "requests": 1,
    "elapsed_seconds": 11.627
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[
  {
    "tool": "search_policies",
    "args": {
      "policy": "faq",
      "topics": [
        "When are you open?"
      ]
    },
    "call_id": "call_vs7cljk0",
    "result": "Final result processed.",
    "returned": true,
    "retry": false
  }
]
```

## ebike_price

How much does one e-bike cost for a day, excluding the deposit and booking fee?

Answer:

> I could not verify a complete answer from the shop data. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b40(?:[.,]0{1,2})?\\b",
    "Missing required fact/refusal pattern: \\b(?:EUR|euros?)\\b|\u20ac"
  ],
  "tools": [
    "Missing required call: {'tool': 'list_policy_topics', 'args': {}}",
    "Missing required call: {'tool': 'search_policies', 'args': {'policy': 'prices', 'topics': ['Bike rental']}}"
  ],
  "runtime": [
    "Run failed: UnexpectedModelBehavior"
  ]
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": "UnexpectedModelBehavior",
    "requests": 1,
    "elapsed_seconds": 5.308
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```

## age_limit

Can my 14-year-old rent an electric bike?

Answer:

> Please provide your booking ID or clarify your CityWheels question. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b(?:no|cannot|can.t|not (?:allowed|eligible)|too young)\\b",
    "Missing required fact/refusal pattern: \\b16\\b"
  ],
  "tools": [
    "Missing required call: {'tool': 'list_policy_topics', 'args': {}}",
    "Missing required call: {'tool': 'search_policies', 'args': {'policy': 'faq', 'topics': ['Are there age limits?']}}"
  ],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": null,
    "output": {
      "scope": "clarify",
      "tasks": []
    },
    "requests": 1,
    "elapsed_seconds": 2.217
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```

## booking_details

For booking CW-1002, how many bikes and what bike type are booked?

Answer:

> I could not verify a complete answer from the shop data. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b(?:2|two)\\b",
    "Missing required fact/refusal pattern: electric|e[- ]?bikes?"
  ],
  "tools": [
    "Missing required call: {'tool': 'get_booking', 'args': {'booking_id': 'CW-1002'}}"
  ],
  "runtime": [
    "Run failed: UnexpectedModelBehavior"
  ]
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": "UnexpectedModelBehavior",
    "requests": 1,
    "elapsed_seconds": 5.373
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```

## half_refund

If I cancel CW-1002 now, how much will I get back in total?

Answer:

> I could not verify a complete answer from the shop data. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b340(?:[.,]0{1,2})?\\b",
    "Missing required fact/refusal pattern: \\b(?:EUR|euros?)\\b|\u20ac",
    "Expected amount not identified as refund/total"
  ],
  "tools": [
    "Missing required call: {'tool': 'calculate_refund', 'args': {'booking_id': 'CW-1002'}}",
    "Refund tool field refund must equal 340",
    "Refund tool field rental_refund must equal 40",
    "Refund tool field deposit_refund must equal 300",
    "Refund tool field booking_fee_refund must equal 0",
    "Refund tool field booking_fee_retained must equal 2"
  ],
  "runtime": [
    "Run failed: UnexpectedModelBehavior"
  ]
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": "UnexpectedModelBehavior",
    "requests": 1,
    "elapsed_seconds": 6.474
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```

## deposit_only

If I cancel CW-1003 now, how much will I get back in total?

Answer:

> I could not verify a complete answer from the shop data. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b50(?:[.,]0{1,2})?\\b",
    "Missing required fact/refusal pattern: \\b(?:EUR|euros?)\\b|\u20ac",
    "Expected amount not identified as refund/total"
  ],
  "tools": [
    "Missing required call: {'tool': 'calculate_refund', 'args': {'booking_id': 'CW-1003'}}",
    "Refund tool field refund must equal 50",
    "Refund tool field rental_refund must equal 0",
    "Refund tool field deposit_refund must equal 50",
    "Refund tool field booking_fee_refund must equal 0",
    "Refund tool field booking_fee_retained must equal 2"
  ],
  "runtime": [
    "Run failed: UnexpectedModelBehavior"
  ]
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": "UnexpectedModelBehavior",
    "requests": 1,
    "elapsed_seconds": 7.199
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```

## already_cancelled

Can I cancel CW-1005 now and receive another cancellation refund?

Answer:

> I could not verify a complete answer from the shop data. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: cancelled|canceled",
    "Missing required fact/refusal pattern: \\b(?:cannot|can.t|no (?:additional |further |new )?refund|not (?:eligible|possible)|nothing)\\b"
  ],
  "tools": [
    "Missing required call: {'tool': 'calculate_refund', 'args': {'booking_id': 'CW-1005'}}",
    "Expected an ineligible cancellation result"
  ],
  "runtime": [
    "Run failed: UnexpectedModelBehavior"
  ]
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": "UnexpectedModelBehavior",
    "requests": 1,
    "elapsed_seconds": 5.631
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```

## unknown_booking

Please show me the details of booking CW-9999.

Answer:

> Please provide your booking ID or clarify your CityWheels question. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: not found|could not find|couldn.t find|does not exist|no booking"
  ],
  "tools": [
    "Missing required call: {'tool': 'get_booking', 'args': {'booking_id': 'CW-9999'}}",
    "Expected not_found tool result"
  ],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": null,
    "output": {
      "scope": "clarify",
      "tasks": []
    },
    "requests": 1,
    "elapsed_seconds": 2.308
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```

## out_of_scope_geography

What is the capital of Australia?

Answer:

> I can only help with CityWheels bike rentals. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [],
  "tools": [],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": null,
    "output": {
      "scope": "unsupported",
      "tasks": []
    },
    "requests": 1,
    "elapsed_seconds": 1.506
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```

## out_of_scope_recipe

Give me a detailed pancake recipe.

Answer:

> I can only help with CityWheels bike rentals. Please contact our staff at help@citywheels.example.

Failures:
```json
{
  "answer": [],
  "tools": [],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

Agent stages (separate contexts, shared budget):
```json
[
  {
    "phase": "manager_route",
    "error": null,
    "output": {
      "scope": "unsupported",
      "tasks": []
    },
    "requests": 1,
    "elapsed_seconds": 2.019
  }
]
```

All model tool-call attempts (including rejected arguments):
```json
[]
```
