# Real-model evaluation

Passed: **4/10** completed cases.

```json
{
  "started_utc": "2026-11-22T12:54:58.534433+00:00",
  "provider": "ollama",
  "model": "llama3.1:8b",
  "base_url": "http://localhost:11434/v1",
  "pydantic_ai_version": "2.71.0",
  "git_commit": "8c8b94be633c050b11c9bc5e1f8a9cd3f6f242d8",
  "working_tree_dirty": true,
  "cases_sha256": "fdfde8b172e7d848acba777947d420312159cab975afb187ad6913773ba8451a",
  "checks_sha256": "82948320a37ab0b3643669a95e5dc5e344956d5b3960617eefd55776d7d194b6",
  "app_sha256": "a36ddff58ae841983265e7baa71a9530018874a4481decaf19b73d339ba78d90",
  "case_count": 10,
  "temperature": 0,
  "provider_retries": 0,
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
  },
  "workflow_regrade_utc": "2026-11-22T13:40:56.349902+00:00",
  "workflow_regrade_note": "Existing raw outputs/timings regraded with the workflow-aware checker. Legacy runs already expose model tool calls as business calls; rejection-attempt checks are additional when available. No inference rerun."
}
```

Overall pass requires answer, tool, and runtime checks all to pass.
The 60-second target is a project benchmark, not an assignment requirement.
Each case is a fresh conversation. Model/OS caches remain warm after earlier cases; no warm-up is excluded.
Checks use explicit patterns, expected tool arguments/results, and limits, not an LLM judge.
They do not prove semantic correctness or detect every contradiction. Review the included answers and traces.

| Case | Answer | Tools | Runtime | Seconds | Requests | Calls |
| --- | --- | --- | --- | ---: | ---: | ---: |
| opening_hours | FAIL | FAIL | PASS | 58.233 | 1 | 0 |
| ebike_price | FAIL | FAIL | PASS | 14.277 | 2 | 1 |
| age_limit | FAIL | FAIL | PASS | 17.974 | 2 | 1 |
| booking_details | PASS | PASS | PASS | 13.307 | 2 | 1 |
| half_refund | FAIL | PASS | PASS | 16.398 | 2 | 1 |
| deposit_only | FAIL | PASS | PASS | 15.989 | 2 | 1 |
| already_cancelled | PASS | PASS | PASS | 15.132 | 2 | 1 |
| unknown_booking | PASS | PASS | PASS | 11.723 | 2 | 1 |
| out_of_scope_geography | PASS | PASS | PASS | 12.479 | 1 | 0 |
| out_of_scope_recipe | FAIL | PASS | PASS | 7.897 | 1 | 0 |

Latency: median 14.704s; maximum 58.233s.

## opening_hours

What time are you open on Saturdays in June?

Answer:

> I don't have a function to call that answers your question. The provided functions seem to be related to CityWheels bike rental policies and bookings, but they do not include information about business hours or opening times.
>
> You may want to try contacting the help desk directly at help@citywheels.example for more general questions like this one.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b(?:08[:.]00|8\\s*(?:am|a\\.m\\.))\\b",
    "Missing required fact/refusal pattern: \\b(?:20[:.]00|8\\s*(?:pm|p\\.m\\.))\\b"
  ],
  "tools": [
    "Missing required call: {'tool': 'list_policy_topics', 'args': {}}",
    "Missing required call: {'tool': 'search_policies', 'args': {'policy': 'faq', 'topics': ['When are you open?']}}"
  ],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```

## ebike_price

How much does one e-bike cost for a day, excluding the deposit and booking fee?

Answer:

> The policy "rental_policy.txt" does not exist. Please check the available policies in the catalogue and use a valid policy ID.
>
> Available topics for pricing are:
>
> * Bike rental
> * Add-ons
> * Booking fee
> * Deposit
> * Late return
>
> Please try again with a valid policy ID.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b40(?:[.,]0{1,2})?\\b",
    "Missing required fact/refusal pattern: \\b(?:EUR|euros?)\\b|\u20ac"
  ],
  "tools": [
    "Invalid policy/topic arguments: {'policy': 'rental_policy.txt', 'topics': ['pricing']}",
    "Policy retrieval before catalogue discovery",
    "Tool error result: invalid_policy",
    "Missing required call: {'tool': 'list_policy_topics', 'args': {}}",
    "Missing required call: {'tool': 'search_policies', 'args': {'policy': 'prices', 'topics': ['Bike rental']}}"
  ],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[
  {
    "tool": "search_policies",
    "args": {
      "policy": "rental_policy.txt",
      "topics": [
        "pricing"
      ]
    },
    "call_id": "call_27nkkhyc",
    "result": {
      "result": "invalid_policy",
      "message": "Unknown policy: rental_policy.txt",
      "available": {
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
      }
    },
    "returned": true,
    "retry": false
  }
]
```

## age_limit

Can my 14-year-old rent an electric bike?

Answer:

> The policy "rental_policy.txt" does not exist. Please check the available policies in the catalogue and select a valid one.
>
> If you need help with something else, please let me know!

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b(?:no|cannot|can.t|not (?:allowed|eligible)|too young)\\b",
    "Missing required fact/refusal pattern: \\b16\\b"
  ],
  "tools": [
    "Invalid policy/topic arguments: {'policy': 'rental_policy.txt', 'topics': ['youth_rentals']}",
    "Policy retrieval before catalogue discovery",
    "Tool error result: invalid_policy",
    "Missing required call: {'tool': 'list_policy_topics', 'args': {}}",
    "Missing required call: {'tool': 'search_policies', 'args': {'policy': 'faq', 'topics': ['Are there age limits?']}}"
  ],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[
  {
    "tool": "search_policies",
    "args": {
      "policy": "rental_policy.txt",
      "topics": [
        "youth_rentals"
      ]
    },
    "call_id": "call_k0zs6a9l",
    "result": {
      "result": "invalid_policy",
      "message": "Unknown policy: rental_policy.txt",
      "available": {
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
      }
    },
    "returned": true,
    "retry": false
  }
]
```

## booking_details

For booking CW-1002, how many bikes and what bike type are booked?

Answer:

> For booking CW-1002, 2 e-bikes are booked.

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
    "tool": "get_booking",
    "args": {
      "booking_id": "CW-1002"
    },
    "call_id": "call_fb9xwkqb",
    "result": {
      "id": "CW-1002",
      "status": "confirmed",
      "bike_type": "e-bike",
      "bikes": 2,
      "start": "2026-06-11T18:00:00+02:00",
      "end": "2026-06-12T18:00:00+02:00",
      "add_ons": [],
      "rental_price_eur": "80.0",
      "booking_fee_eur": "2.0",
      "deposit_eur": "300.0",
      "paid_with": "card"
    },
    "returned": true,
    "retry": false
  }
]
```

## half_refund

If I cancel CW-1002 now, how much will I get back in total?

Answer:

> You will get a total refund of 340.0, broken down as follows: rental refund 40.0, deposit refund 300.0, and no booking fee refund since the retained booking fee is 2.0. The original payment method was by card.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b(?:EUR|euros?)\\b|\u20ac"
  ],
  "tools": [],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[
  {
    "tool": "calculate_refund",
    "args": {
      "booking_id": "CW-1002"
    },
    "call_id": "call_azrogxmp",
    "result": {
      "refund": "340.0",
      "rental_refund": "40.0",
      "deposit_refund": "300.0",
      "booking_fee_refund": "0",
      "booking_fee_retained": "2.0",
      "rule": "24_to_48_hours",
      "paid_with": "card",
      "deposit_refund_method": "original_payment_method"
    },
    "returned": true,
    "retry": false
  }
]
```

## deposit_only

If I cancel CW-1003 now, how much will I get back in total?

Answer:

> You will get back 50.0 in total, which is the full rental refund since you cancelled less than 24 hours before pickup. The booking fee of 2.0 has been retained by CityWheels. Your deposit was paid with a card and will be refunded via the same method.

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: \\b(?:EUR|euros?)\\b|\u20ac",
    "Deposit-only refund incorrectly described as a full rental refund"
  ],
  "tools": [],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[
  {
    "tool": "calculate_refund",
    "args": {
      "booking_id": "CW-1003"
    },
    "call_id": "call_bujeddtj",
    "result": {
      "refund": "50.0",
      "rental_refund": "0",
      "deposit_refund": "50.0",
      "booking_fee_refund": "0",
      "booking_fee_retained": "2.0",
      "rule": "less_than_24_hours",
      "paid_with": "card",
      "deposit_refund_method": "original_payment_method"
    },
    "returned": true,
    "retry": false
  }
]
```

## already_cancelled

Can I cancel CW-1005 now and receive another cancellation refund?

Answer:

> You cannot cancel booking CW-1005 as it is already in a cancelled state. Therefore, you will not receive another cancellation refund.

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
    "tool": "calculate_refund",
    "args": {
      "booking_id": "CW-1005"
    },
    "call_id": "call_eqx5x1os",
    "result": {
      "id": "CW-1005",
      "message": "Booking CW-1005 with status cancelled cannot be cancelled or refunded"
    },
    "returned": true,
    "retry": false
  }
]
```

## unknown_booking

Please show me the details of booking CW-9999.

Answer:

> I'm sorry, but booking CW-9999 was not found.

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
    "tool": "get_booking",
    "args": {
      "booking_id": "CW-9999"
    },
    "call_id": "call_1owfzge3",
    "result": {
      "id": "CW-9999",
      "result": "not_found",
      "message": "Booking CW-9999 not found"
    },
    "returned": true,
    "retry": false
  }
]
```

## out_of_scope_geography

What is the capital of Australia?

Answer:

> I'm not able to answer questions that are unrelated to CityWheels. The tool capabilities only allow me to provide information about bike rentals, policies, and bookings. For general knowledge or unrelated topics, please contact help@citywheels.example for assistance.
>
> However, I can suggest using a search engine or a reliable online resource to find the capital of Australia.

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

## out_of_scope_recipe

Give me a detailed pancake recipe.

Answer:

> I'm not able to provide information on cooking recipes as I don't have access to external knowledge or tools that can provide such information.
>
> However, you may want to try searching online for a detailed pancake recipe or checking out cookbooks from your local library. If you're looking for help with something else related to CityWheels bike rentals, feel free to ask and I'll do my best to assist you!

Failures:
```json
{
  "answer": [
    "Missing required fact/refusal pattern: help@citywheels\\.example"
  ],
  "tools": [],
  "runtime": []
}
```

Tool trace (includes exact arguments and returned data):
```json
[]
```
