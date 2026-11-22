# CityWheels solution and architecture decisions

This document records decisions as the project develops. Planned behavior is
identified explicitly; it should not be read as implemented functionality.

## Current status

The repository contains the original data, a CLI skeleton, booking lookup and
refund calculation tools, deterministic policy lookup, and pytest tests. The
agent, provider integration, and evaluation are not implemented yet.

## Setup and commands

The project currently requires Python 3.14 or newer and uses uv for dependencies.

```bash
uv sync --locked
uv run python -m app.main
uv run pytest
```

The CLI currently displays help only. The latest test run has 80 passing tests
and no skipped templates. Evaluation commands and provider
environment variables will be documented when implemented.

## Architecture decision log

### 2026-11-20: Focus on a CLI

**Decision:** Use `app/main.py` as the CLI entry point. Defer FastAPI.

**Reason:** The assignment requires command-line access. Implementing an HTTP API
now would add an interface that is not needed to meet that requirement.

**Consequence:** The unused FastAPI starter files have been removed. The FastAPI
dependency remains for now, but the CLI does not use it. Review unused dependencies
before the final submission.

### 2026-11-20: Separate tools from the interface

**Decision:** Keep each tool in its own module under `app/tools/`:

- `get_booking.py`: booking lookup and a clear not-found result.
- `search_policies.py`: relevant policy text with source references.
- `calculate_refund.py`: deterministic refund calculation.

**Reason:** Each tool can be developed and tested independently of the CLI or LLM.

**Consequence:** All three required tools are implemented, along with a policy
topic catalogue tool. Models live under `app/models/` and injectable file loaders
under `app/db/`. The agent and CLI question flow remain to be implemented.

### 2026-11-20: Inject the booking data source

**Decision:** `get_booking` accepts a keyword-only `booking_loader` callable,
defaulting to the JSON loader. Unit tests inject fake loaders directly, without
monkeypatching module globals. Remove the shared global booking cache.

**Reason:** Explicit dependencies keep tests isolated and prevent a fake source
from hiding problems with the production data. For ten bookings, a cache adds
unnecessary state and complexity.

**Consequence:** Keep `BookingBase` for shared validation and `BookingRead` for
read results. The read model prevents field reassignment, but its nested lists
remain mutable. Fields use the four supplied statuses, timezone-aware datetimes,
non-negative finite Decimal amounts, positive integer bike counts, and restricted
bike/payment types. Rental end must be after start. JSON decimal numbers are
parsed directly as Decimal. Loading errors propagate separately from not-found
results. The future agent adapter must inject the loader in Python rather than
expose it as a model-supplied tool argument.

**Evidence:** 32 tests pass across lookup, injected source isolation, field
validation, and loader behavior. All ten real records were also loaded in a
separate smoke check. The missing-file, malformed-JSON, failed-load recovery,
and duplicate-ID tests are implemented using temporary files. Missing files and
invalid data raise errors rather than returning a not-found result. Duplicate
IDs now raise an explicit ValueError instead of overwriting earlier entries.
No booking tests remain skipped.

### 2026-11-20: Use pytest only and group tests by feature

**Decision:** Use pytest as a development dependency and place tests under
`tests/<feature>/test_<feature>.py`. Configure pytest to discover the `tests/`
directory.

**Reason:** This follows the requested structure and keeps each tool's behavior
easy to find. All tests can be run with `uv run pytest`.

**Consequence:** Test templates use explicit pytest skip markers until real
assertions and implementation are added. Remove the markers as features are built.

### Planned: Pydantic AI with one configurable provider

**Decision:** Use a Pydantic AI agent with one active provider per run. Support
configuration for OpenAI or Ollama.

**Reason:** Keep tool orchestration in one agent while allowing the model provider
to change without rewriting tool logic.

**Consequence:** Pydantic AI is not installed or integrated yet. The exact model,
default provider, configuration variables, and tool-calling compatibility must be
selected and verified during implementation. No real-provider evaluation has run.

### 2026-11-22: Calculate refunds in Python

**Decision:** Use `Decimal` for monetary calculations and the assignment's fixed
current time: `2026-06-10T09:00:00+02:00` (Europe/Warsaw). The LLM will explain the
tool's result rather than calculate the amount.

**Reason:** Refund amounts and 24/48-hour boundaries must be reproducible and
covered by tests.

**Consequence:** Return a breakdown of rental refund, deposit, non-refundable
booking fee, and applicable rule. Refunding by voucher must not be described as a
cash refund. The data does not separately identify the deposit payment method, so
the agent must not invent it. The tool will quote refunds without changing bookings.

The tool defaults to the fixed assignment timestamp and accepts an injected
timezone-aware datetime and booking loader. Elapsed time is calculated in UTC.
Every status other than `confirmed` returns an ineligible result. Confirmed
records with a start time already passed follow the zero-rental-refund tier,
with the deposit returned; the tool does not infer a different booking status.
This makes the inconsistent-data case explicit without adding an undocumented
status transition. Invalid time types and naive datetimes raise clear errors.

The result contains the rental and deposit components, retained booking fee,
applicable tier, and total. `paid_with` identifies the rental payment method;
the deposit method is described only as its original payment method. No storm
exception is automatically approved. Monetary arithmetic uses Decimal; a rounding
rule for hypothetical half-cent refunds remains unspecified by the policy.

**Evidence:** The full suite reports 55 passed and two policy-search templates
skipped. Tests cover all three ineligible statuses, 24/48-hour boundaries and
one second below each, cancellation at/after start, fixed-time examples, voucher
refunds, missing bookings, source errors, and timestamp validation. Shared test
fixtures now distinguish one booking payload from the complete collection.

### 2026-11-22: Use a catalogue and strict policy section lookup

**Decision:** Replace the initial keyword-search proposal with two deterministic
tools. `list_policy_topics()` lists policy IDs (filename stems) and exact `##`
headings. `search_policies(policy, topics)` returns selected sections in requested
order with the document title, source, and introduction. Both accept an injected
policy loader, keeping tests independent of the real documents.

**Reason:** The supplied policy collection is small. Explicit topic selection is
predictable and easy to explain and test. This iteration needs no embeddings,
similarity ranking, vector database, or retrieval service.

**Consequence:** Policy/topic names are case-sensitive. Unknown policies, unknown
topics, empty topic lists, and duplicate selections return structured errors with
valid choices, without partial answers or guessed matches. The loader preserves
section bodies verbatim, including tables, lists, nested headings, and line
endings. Introductions preserve context outside sections, such as currency/VAT.
Duplicate headings and malformed policy structure raise data errors. The parser
supports the supplied ATX heading format and fenced code blocks; it is not a
general Markdown parser. Policy IDs select loaded documents, never arbitrary
user-supplied filesystem paths.

The model must still choose the relevant topic from the catalogue. Deterministic
retrieval does not guarantee correct topic selection by the model. Evaluate that
separately with paraphrased questions and questions needing multiple documents.

Example application calls (the future agent adapter will inject dependencies):

```python
from app.tools import list_policy_topics, search_policies

catalogue = list_policy_topics()
result = search_policies("prices", ["Bike rental", "Booking fee"])
```

**Evidence:** 80 tests pass overall, including 25 policy tests covering discovery,
exact content, source metadata, invalid selections, source isolation, file errors,
duplicate headings, nested/fenced headings, and LF/CRLF preservation. A separate
smoke check loaded all three supplied files and retrieved the two example topics.

## Planned agent behavior

The CLI will send a customer question to the agent. The model will choose tools,
the application will execute them, and their results will be sent back to the
model until it produces a final answer. A tool-call limit will bound each run.

Agent instructions will require answers grounded in the supplied policies and
bookings, prohibit invented booking details and amounts, and direct customers to
staff when information is missing or a question is outside the shop's scope.
The final instructions and error handling will be documented once implemented.

## Validation and evaluation

Pytest uses `.pytest_tmp/` under the working directory for temporary test data
(`--basetemp` in pyproject.toml), avoiding reliance on Windows AppData temporary
directory permissions. Run tests from the repository root. This directory is
managed and cleared by pytest and is excluded from Git; do not store project
files in it. This configuration was added after a user run reported WinError 5
for all five tests using `tmp_path`, although the assistant's environment passed.

Planned validation includes tool unit tests, every refund rule and time boundary,
missing bookings, voucher handling, and an agent-loop test using a fake model with
no network or API key.

The evaluation will contain at least 10 questions, including at least two refund
questions and two questions the agent should not answer. Its script, automatic
checks, latest results, and observed failures will be committed when available.
There is currently no evaluation pass rate to report.

## AI coding assistant usage

Codex helped inspect the supplied files, discuss the design, create the initial
repository, and write the CLI, tool, and test skeletons and this document.

One output needed revision: the first test templates used Python's `unittest`.
The user specified pytest only. The templates were converted to pytest, pytest
was added as a development dependency, and discovery was verified: 12 skipped
templates. This was a test-framework preference correction, not evidence that the
tool behavior works.

Add further concrete examples of incorrect output, how it was detected, and the
correction as development continues. Do not invent examples or evaluation results.

## Limitations and next steps

- Integrate the implemented tools into the agent and evaluate topic selection.
- Install and integrate Pydantic AI; verify the selected provider and model.
- Add environment configuration and `.env.example` without secrets.
- Implement the CLI question flow and bounded tool-calling loop.
- Add a fake-model agent test and run a real-model evaluation.
- Record failures, fixes, remaining limitations, and exact run commands here.
- Review unused starter files and dependencies before submission.

With more time, consider conversation memory and a comparison of models or
retrieval approaches after the required behavior is working and evaluated.

## Template for future decisions

### YYYY-MM-DD: Decision title

**Status:** Planned / implemented / superseded.

**Decision:** What was chosen.

**Reason:** The requirement or observed problem that motivated it, and any
relevant alternatives.

**Consequence:** Tradeoffs, limitations, and follow-up work.

**Evidence:** Relevant tests or evaluation results, when available.
