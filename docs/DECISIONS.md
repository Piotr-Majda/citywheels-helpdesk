# Archived development history

This is a historical working log. Counts, pending notes, and architecture descriptions
refer to stages of development, not necessarily the released implementation.
Use [SOLUTION.md](../SOLUTION.md), [INSTALL.md](../INSTALL.md), and the release
evaluation manifest for the current version.

---

# CityWheels solution and architecture decisions

This document records decisions as the project develops. Planned behavior is
identified explicitly; it should not be read as implemented functionality.

## Current status

The repository contains the original data, a CLI skeleton, booking lookup and
refund calculation tools, deterministic policy lookup, a Pydantic AI agent,
an Ollama/OpenAI provider switch, a minimal CLI, and pytest tests.
The real-model evaluation runner and ten cases are implemented under `eval/`.

The active architecture is now a manager with narrow specialists; older
single-agent and prompt-only experiments below are retained as development history.

## Active manager/specialist architecture

1. A manager produces a typed `RoutePlan`: supported, unsupported, or clarification,
   with flat `policies`, `bookings`, and `refunds` lists expanded by Python into
   at most four distinct specialist tasks. Python validates the plan
   and rejects booking IDs absent from the customer's question. Its JSON schema
   restricts booking/refund arrays to enums of IDs extracted from that question;
   without an ID those arrays must be empty. The LLM cannot fill them with invented
   bike details or unrelated IDs and still produce a valid plan.
2. Each task goes to a specialist using the same model and a separate, small
   context. Policy tasks first execute catalogue discovery in Python. Topic names
   and assigned IDs are embedded as exact enum choices in each specialist's tool
   schema, rather than relying only on instructions.
3. Specialists use Pydantic AI output functions: a successful specialist must make
   its one permitted native tool call. Its result is the actual Python tool result,
   not a model-written summary. The result is handed back to the manager workflow.
   Invalid arguments can retry once; unsupported text cannot complete a specialist.
4. Python renders booking/refund facts directly from typed results. For policies,
   the manager selects exact source excerpts. Python verifies source IDs, quote
   membership, and coverage of every requested source, then renders the excerpts
   and source references. No free-form policy answer field is allowed. This was
   added after a real smoke check retrieved the correct opening hours but the
   model paraphrased them into the opposite meaning despite a correct citation.

`app/prompts.py` contains separate short instructions for routing, each specialist,
and extractive synthesis. `app/specialists.py` owns the limited tool interfaces;
`app/context.py` owns per-question dependencies, execution budgets, and audit
events. The business tools and loaders were not changed by this architecture work.

All model calls share one usage budget and one deadline: default CLI limits are
six requests, eight business-tool executions, and 180 seconds; evaluation uses
the existing five-request/four-tool/120-second limits and 60-second latency target.
Model replies also have a 1024-token cap to bound malformed or verbose outputs.
No recursive delegation or automatic provider fallback is allowed. Calls execute
sequentially, so multiple specialists do not compete for local model resources.
Both actual executions (with application/model origin) and rejected model attempts
are recorded, along with phase timings, plan output, source checks, and errors.
Raw model responses are retained per stage to diagnose malformed plans and
specialist retries, instead of reporting only a generic validation exception.

Source failure, invalid planning, exhausted budgets, or invalid evidence produce a
staff-contact fallback and an explicit error state/nonzero CLI exit code. Partial
unchecked model answers are not emitted. Unsupported requests use a fixed refusal
without querying business tools. Scope/topic selection can still be wrong; the
checks cannot prove relevance or that a selected excerpt contains every condition.
Extractive policy responses trade conversational phrasing for verifiable source
text. A future paraphrasing mode would need stronger semantic validation.

## Setup and commands

The project currently requires Python 3.14 or newer and uses uv for dependencies.

```bash
uv sync --locked
uv run python -m app.main --help
uv run pytest
uv run python -m eval.run
```

Pass a question to the CLI (or use `--help`):

```powershell
$env:LLM_PROVIDER = "ollama"
$env:LLM_MODEL = "llama3.1:8b"
$env:OLLAMA_BASE_URL = "http://localhost:11434/v1"
uv run python -m app.main --verbose "How much will I get back for CW-1002?"
```

Ollama must be running and the selected model must already be installed. Those
three values are defaults, so no environment setup is needed for that local model.
To switch to OpenAI, set `LLM_PROVIDER=openai`, `LLM_MODEL` to an available model,
and `OPENAI_API_KEY`. OpenAI has not yet been tested with a real provider call.
`.env.example` lists configuration; `.env` is not automatically loaded.
The CLI writes answers to stdout and errors and optional diagnostics to stderr.
The latest suite has 118 passing tests and no skips, including 22 offline
workflow tests and 16 evaluation-checker tests. Real evaluations are
separate from pytest and require the selected provider to be running.

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
under `app/db/`. The agent and CLI question flow are implemented.

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

### 2026-11-22: Pydantic AI with Ollama first

**Decision:** Use a Pydantic AI agent with one active provider per run. Support
configuration for OpenAI or Ollama.

**Reason:** Keep tool orchestration in one agent while allowing the model provider
to change without rewriting tool logic.

**Consequence:** Use `pydantic-ai-slim[openai]` with OllamaProvider and
OpenAIChatModel. Local `llama3.1:8b` is the initial baseline because it is already
installed and reports tool support. The application chooses one provider at
startup; no automatic fallback sends local questions to a cloud provider.
Agent dependencies carry the booking and policy loaders and fixed cancellation
time. Tool wrappers expose only booking IDs or policy/topic selections to the
model. Source failures return `data_unavailable`, distinct from not-found results.
Instructions require grounded answers, policy catalogue lookup, tool-calculated
refunds, and staff escalation when appropriate. Prompt instructions alone do not
guarantee those behaviors; real-model evaluation remains necessary.

The agent is bounded by six model requests, eight tool calls, a 180-second run
timeout, a 120-second model request timeout, and zero provider transport retries.
One retry is allowed for tool argument validation. `--verbose` displays elapsed
time, tool call names, requests, and token usage; detailed tracing is not yet added.

**Evidence:** Four FunctionModel tests exercise all four tools, check that injected
dependencies are absent from model-facing schemas, distinguish source failures
from missing bookings, and verify the request limit stops repeated calls. These
tests need no API key or external service. In the assistant's restricted Windows
sandbox, asyncio socket-pair creation hangs; running the suite outside that
sandbox succeeded (84 tests). This is separate from model/network access.

A real CLI smoke run with Ollama `llama3.1:8b` called `calculate_refund` for CW-1002
and returned 340 EUR with the correct breakdown. It took 52.26 seconds and two
model requests. This is one smoke check, not an evaluation pass rate or a warmed
inference benchmark. Smaller models are candidates for comparison; none were
downloaded as part of this work.

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

## Agent behavior

The CLI sends a customer question to the agent. The model chooses tools,
the application executes them, and their results return to the model until it
produces a final answer. Request, tool-call, and time limits bound each run.

Instructions in `app/agent.py` require grounded answers, prohibit invented booking
details and amounts, and direct customers to staff when information is missing
or a question is outside the shop's scope. These instructions are tested through
real-model evaluation; they are not hard guarantees of model behavior.

## Validation and evaluation

Pytest uses `.pytest_tmp/` under the working directory for temporary test data
(`--basetemp` in pyproject.toml), avoiding reliance on Windows AppData temporary
directory permissions. Run tests from the repository root. This directory is
managed and cleared by pytest and is excluded from Git; do not store project
files in it. This configuration was added after a user run reported WinError 5
for all five tests using `tmp_path`, although the assistant's environment passed.

Pytest covers the tools, refund rules and boundaries, missing bookings, voucher
handling, and agent loops using a fake model with no network or API key.

`eval/cases.json` contains ten real-model questions, including two refund cases
and two unrelated questions requiring refusal and staff contact. Run
`uv run python -m eval.run`; results are written incrementally to `eval/results.md`
and `eval/results.json`. See `eval/README.md` for comparison runs and limitations.

Checks cover answer facts/refusals, required and allowed tools, exact booking
IDs, policy IDs/topics, catalogue order, tool results, repeated calls, and runtime.
Answer, tool, and runtime checks are reported separately. Each case has a
60-second latency target, a 120-second enforced timeout, at most five model
requests and four tool calls, and no identical repeated calls. These are project
benchmarks, not additional assignment requirements. The runner returns exit code
1 when any case fails and preserves failures rather than hiding them. Automated
pattern checks do not prove complete semantic correctness; full answers and traces
are saved for review. The first case may include cold-start costs.

Sixteen offline checker tests include deliberately wrong amounts, IDs,
contradictory totals, missing tools, invalid arguments, repeated calls, retries,
timeouts, and excessive requests. Correct answers without supporting tool calls
do not pass tool validation. Run metadata includes the configured model/provider,
limits, fixed time, code/case fingerprints, and whether the working tree was dirty.

### Original-prompt baseline: Ollama llama3.1:8b

The ten-question baseline scored **4/10 overall**: answer checks 4/10, tool checks
7/10, and runtime checks 10/10. The original-prompt run archived from disk before
the prompt experiment has median latency 14.704 seconds and maximum 58.233 seconds.
An earlier run reported in this chat had median 13.259 seconds and maximum
38.198 seconds; the archived run is the basis for the comparison below.
No case repeated an identical tool call or exceeded its loop/time budget.
This run used the existing local model; no model was downloaded or swapped.

Observed failures:

- Opening hours: no tool call; the model incorrectly said it could not look up hours.
- Pricing and age limits: invented `rental_policy.txt` and nonexistent topics,
  skipped catalogue discovery, and failed to recover from the tool's valid choices.
- Both refund cases: correct tool arguments and numeric totals, but no currency
  label. The deposit-only answer also wrongly called the deposit a full rental refund.
- Pancake recipe: declined the unrelated request but omitted staff contact.

The saved outputs were rechecked after manual inspection: the checker now
recognizes "not able" as refusal wording and flags the observed full-rental-refund
mislabeling for a zero rental component. Negated wording is tested separately.
No model calls were rerun for that checker adjustment; original timings and raw
answers are preserved, and report metadata records the regrading and fingerprints.
The overall score remained 4/10. This targeted regex still does not establish full
semantic correctness or catch every possible contradictory explanation.

The baseline is preserved under `eval/baseline/` with the original agent source.

### 2026-11-22: Test explicit workflows and few-shot tool examples

**Decision:** Keep the single-agent loop and deterministic tools. Move instructions
to `app/prompts.py`, spell out policy/booking/refund/refusal workflows, add examples
using questions and booking IDs outside the original ten cases, explain invalid
argument recovery, and give a refund field-to-answer template with EUR labels.
Clarify the catalogue and policy-retrieval tool descriptions. Do not introduce
specialist agents or change the business tools during this comparison.

**Reason:** First measure whether clearer instructions solve the observed errors
before adding routing decisions and extra model calls.

**Evidence:** On the unchanged ten cases, the score remained **4/10**. Answer
checks improved from 4/10 to 7/10, tool checks fell from 7/10 to 4/10, and runtime
checks remained 10/10. Median latency changed from 14.704 to 13.996 seconds;
maximum latency changed from 58.233 to 56.365 seconds. The two refund explanations
now label currency and components correctly. Policy questions still stop after
catalogue discovery or use wrong arguments. Both unrelated questions now produce
the required refusal text but unnecessarily call the catalogue. The already
cancelled booking regressed: the model called get_booking and said it was missing
even though the tool returned the existing cancelled booking.

`eval/comparison.md` is generated by `uv run python -m eval.compare`. It verifies
matching case/check fingerprints, model/provider, and limits. This is one run per
version, not a statistically significant performance comparison. The additional
five cases in `eval/holdout_cases.json` were defined before seeing revised-prompt
outputs and are reported separately under `eval/holdout/`.

The five additional cases scored **1/5 overall**: answer checks 2/5, tool checks
2/5, runtime checks 5/5. Policy cases again stopped after catalogue discovery.
The late-return answer invented a 10 EUR/hour fee and cited nonexistent
`prices.json`, rather than retrieving the actual 1.5-times-hourly-price rule.
Cash-deposit and storm-review questions were not answered from their policy text.
The missing-booking fabrication instruction was rejected correctly. The voucher
case returned the correct amount and identified voucher payment, but failed the
explicit "not cash" wording check; this is a stricter response-completeness
failure, not a wrong amount or a demonstrated cash-refund claim. Full traces
and raw answers are preserved for that distinction. After this first inspection,
these five cases are development data rather than an unseen benchmark.

**Consequence:** The longer prompt alone is not an established improvement.
Next investigate enforcing workflow/evidence in application code or evaluate a
different tool-capable model. A router with specialists remains an option to test,
not a demonstrated fix. Preserve these failures and do not relax the original
evaluation checks to raise the score.

### Manager/specialist implementation and final results

The final implementation keeps the same local `llama3.1:8b` model and business
tools. Manager instructions are 187 words; individual specialist instructions
are 21–32 words; the extractive manager instructions are 63 words. Each agent
gets a separate context containing only its assignment and relevant evidence.

Early workflow failures are preserved in `eval/workflow_v1/` (3/10) and
`eval/workflow_v2/` (6/10). The first nested task plan was simplified to flat lists.
After a manager put invented bike details in a booking-ID field, the schema was
restricted to IDs actually present in the question. Specialist schemas likewise
enumerate real topic names and assigned IDs. These are enforced input constraints,
not just longer prompt instructions.

The final unchanged ten-case evaluation scored **8/10 overall**, compared with
the archived original baseline's **4/10**. Answer checks passed 9/10, tool checks
9/10, and runtime checks 10/10. Median latency was 16.749 seconds, maximum
31.071 seconds. Total model requests increased from 17 to 30: separate planning,
retrieval, and synthesis stages have a real cost. A new 1024-token response cap
also applies; this difference is included in the comparison metadata/report.
See `eval/comparison.md` for per-case results. This is one observed run per version,
not a statistically controlled latency benchmark.

Remaining ten-case failures:

- Age limits: the correct topic and exact minimum-age-16 policy excerpt were
  returned. The unchanged checker requires an explicit negative answer to the
  14-year-old question, which this extractive response does not generate.
- Unknown booking: the final not-found answer was correct, but the manager also
  selected unnecessary FAQ and price-policy tasks. Input schemas prevent invalid
  IDs/topics, not semantically unnecessary valid selections.

The five additional development cases scored **3/5**, versus 1/5 for the longer
single-agent prompt. Late-return rules, storm review, and voucher refunds passed.
The cash-deposit response quoted the correct "cash, but not the deposit" rule,
but omitted the payment-alternative wording required by the checker and performed
an unnecessary price-policy lookup. The fabricated-booking request correctly
returned not found, but performed unnecessary policy lookups and took 60.060
seconds, exceeding the 60-second target (while remaining under the enforced
120-second deadline). Scores were not relaxed for these wording/overfetch failures.

Next improve semantic routing/minimal evidence selection, add fresh questions,
and compare another tool-capable model. Do not claim exact-source extraction
proves relevance, sufficient context, or complete semantic correctness.

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

Another concrete correction arose during the manager/specialist implementation:
the assistant initially allowed a free policy answer when its citations and
numbers matched retrieved evidence. A real Ollama smoke test retrieved the correct
opening hours, then said the shop was closed while quoting a policy saying it was
open. Citation/numeric membership was insufficient to validate that paraphrase.
The free answer field was removed, and policy synthesis now selects only exact
retrieved excerpts. Python checks and renders those excerpts. This prevents that
paraphrase failure at the cost of a less conversational policy response.

## Limitations and next steps

- Improve observed real-model failures and rerun the same evaluation cases.
- Compare smaller Ollama models using the same questions and timing method.
- Add CLI/configuration tests and verify the optional OpenAI path if credentials are supplied.
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
