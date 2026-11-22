# CityWheels solution — v0.1.0

This is the current implementation guide. The tagged repository version is
[`v0.1.0`](https://github.com/Piotr-Majda/citywheels-helpdesk/tree/v0.1.0).
[INSTALL.md](INSTALL.md) covers a fresh setup; [docs/DECISIONS.md](docs/DECISIONS.md)
preserves the development history.

## Run

Requires Git, uv, Python 3.14+, and Ollama with `llama3.1:8b` installed.
From the repository root:

```powershell
uv sync --locked
uv run --locked python -m app.main --verbose "How much will I get back for CW-1002?"
uv run --locked pytest
uv run --locked python -m eval.run --output eval/local-run
```

The default provider is Ollama at `http://localhost:11434/v1`; no API key is needed.
Environment variables are listed in `.env.example`. They must be exported in the
terminal; the application does not automatically load `.env` files. To use OpenAI,
set `LLM_PROVIDER=openai`, `LLM_MODEL` to an available model, and `OPENAI_API_KEY`.
The OpenAI path is implemented but has not been verified with a live provider call.

The CLI prints answers to stdout and optional timing/tool diagnostics to stderr.
It exits nonzero for execution/configuration errors or unverified answers. Evaluation
exits 1 if any case fails; this is expected for the committed real-model results.

## Model and framework

The evaluated model is local Ollama `llama3.1:8b`. It was already installed, supports
native tool calls, and makes the solution runnable without paid API credentials.
The locked Pydantic AI version is 2.71.0. It supplies structured outputs, tool
argument validation, retry handling, usage accounting, and model-provider adapters.
Python application code supplies routing checks, execution limits, evidence
validation, and answer formatting. No vector database, HTTP server, or external
observability service is required.

## Architecture

```text
Customer question
  -> manager: typed scope and plan
  -> Python: validate selected IDs and tasks
  -> narrow specialists: execute their permitted tools
  -> Python: validate actual evidence
  -> manager: select policy excerpts
  -> Python: render verified excerpts and structured booking/refund results
```

1. The manager returns scope plus flat `policies`, `bookings`, and `refunds` lists.
   Plans allow at most four distinct tasks. Booking-ID enums are generated from
   IDs present in the question; policy IDs are restricted to the three supplied files.
2. Each specialist uses the same model with a fresh, small context and one allowed
   native tool. Its successful output is a Python tool result, not generated prose.
   Pydantic AI output functions enforce this handoff; invalid arguments may retry
   once. The policy specialist receives exact topic enums after Python executes
   catalogue discovery. Successful results return to the manager workflow; policy
   evidence is subsequently provided to the model for extractive synthesis.
3. Python checks result types and source availability. A policy summary may contain
   only citations and verbatim quotes present in retrieved text; every requested
   policy source must be cited. There is no unrestricted policy-answer field.
4. Booking facts and refund amounts are rendered directly from typed results.
   Policy excerpts are rendered with their source filename, topics, and document
   introduction. Unsupported questions receive a fixed refusal and staff contact.

These are separate contexts and sequential calls, not recursive delegation.
Short role instructions live in `app/prompts.py`; routing/assembly is in
`app/agent.py`, specialist tool interfaces in `app/specialists.py`, and per-question
state/audit events in `app/context.py`.

All stages share a request/tool budget and deadline. CLI defaults: six model
requests, eight business-tool executions, 180 seconds. Evaluation: five requests,
four tool executions, 120-second deadline, and a separate 60-second performance
target. Replies are capped at 1024 tokens. Provider transport retries are disabled.
Repeated identical business-tool executions are blocked. Invalid plans, exhausted
budgets, missing data, or unsupported evidence produce a staff-contact fallback
and an explicit error state; unchecked partial answers are not emitted.

## Tools and data decisions

| Tool | Implementation and reason |
| --- | --- |
| `list_policy_topics` | Generate available policy IDs and exact `##` headings from the documents. |
| `search_policies` | Retrieve exact selected sections, including tables/lists, introduction, and sources. Strict lookup is predictable for three small files. |
| `get_booking` | Validate JSON into `BookingRead`; return a booking or structured `not_found`. No shared mutable cache. |
| `calculate_refund` | Use Python `Decimal`, stored booking prices, booking status, and timezone-aware elapsed time. The LLM does no monetary arithmetic. |

Loaders and cancellation time are injected explicitly, including in unit tests.
The fixed assignment time is **2026-06-10 09:00 Europe/Warsaw (UTC+02:00)**.
Rental refunds are 100% at >=48 hours, 50% at >=24 and <48 hours, and zero below
24 hours. Confirmed cancellations return the full deposit; booking fees are retained.
Other statuses cannot be cancelled and receive no new cancellation refund.
A confirmed record whose start has passed uses the zero-rental-refund tier; the
tool does not invent a status transition. No booking is changed and no money is sent.

Voucher rental refunds are new vouchers, not cash. The deposit follows its original
payment method, which the data does not separately identify. Storm exceptions and
damage/theft decisions require staff. No automatic exception is approved.

## Tests, evaluation, and version binding

The offline suite has **118 passing tests**, with no skips. It covers all tools,
refund rules and boundaries, source failures, model-free workflow tests using
`FunctionModel`, argument/source guards, shared budgets/timeouts, and the evaluator
itself. Tests inject fake data and need no Ollama service or API key.

The real-model reports belong to the unchanged application source packaged as
v0.1.0. [eval/RELEASE.md](eval/RELEASE.md) and [eval/release.json](eval/release.json)
link recorded run fingerprints to this version. Original run metadata is preserved:
the runs were recorded from an uncommitted working tree based on an earlier Git
commit. That base commit is not falsely presented as the evaluated final source.
Canonical per-file hashes handle Git's line-ending normalization across checkouts.
[docs/VERIFICATION.md](docs/VERIFICATION.md) records the separate fresh-clone check.

| Validation | Result | Evidence |
| --- | --- | --- |
| Original ten real questions | **8/10** overall | [Report](eval/results.md), [JSON](eval/results.json), [cases](eval/cases.json) |
| Answer / tool / runtime checks | **9/10 / 9/10 / 10/10** | Same report, with full answers and traces |
| Five additional development cases | **3/5** | [Report](eval/holdout/results.md), [cases](eval/holdout_cases.json) |
| Original single-agent baseline | **4/10** | [Before/after comparison](eval/comparison.md) |

Median latency for the final ten-case run was **16.749 seconds**, maximum **31.071
seconds**. Model requests increased from 17 to 30 compared with the archived
baseline. These are single observed runs with cache/startup effects, not controlled
performance claims. All rejected model attempts, actual tool arguments/results,
stage timings, and guard failures are available in the reports.

The remaining failures are kept in the score:

- The age-limit response quotes the correct minimum age of 16 but lacks the
  explicit negative wording required by the checker for a 14-year-old.
- Unknown-booking responses are correct but sometimes trigger unnecessary policy
  lookups. The fabrication-instruction case also took 60.060 seconds, just above
  our 60-second target while below the enforced 120-second deadline.
- The cash-deposit response quotes "cash, but not the deposit", but misses the
  checker's requested alternative-payment wording and performs an extra lookup.

Run metadata, grading rules, limitations, comparison commands, and historical
experiments are explained in [eval/README.md](eval/README.md). Local reruns should
use `--output` so the committed baseline is preserved. Regex checks are useful but
can reject valid wording or miss semantic mistakes; full answers still need review.
The additional five cases are now development data, not an unseen benchmark.

## AI-assistant usage and corrections

Codex helped inspect the task data, discuss designs, scaffold the repository,
implement and review tools/agents/tests, run evaluations, and write documentation.
The user chose the CLI focus, pytest, dependency injection, strict policy retrieval,
and manager/specialist architecture; generated changes were checked through tests
and real local-model runs.

A concrete assistant mistake was accepting a generated policy answer when its
quotes and numbers matched evidence. A real run retrieved the correct hours but
said the shop was closed while quoting text saying it was open. The provenance
check did not validate that paraphrase. We removed the free answer field and now
render only validated excerpts. Earlier test scaffolding also used `unittest` and
was corrected to pytest at the user's request. No example or evaluation score was
invented to claim success.

## Limitations and next steps

- The model can still misclassify scope, select unnecessary valid tasks/topics,
  or choose incomplete excerpts. Source membership does not prove relevance or
  that every condition has been included.
- Extractive answers are less conversational. Improving paraphrases requires
  stronger semantic checking, not just longer instructions.
- Model weights/Ollama behavior can change; use the recorded model/settings and
  locked dependencies, but do not expect identical wording or timings.
- OpenAI live execution, other models/operating systems, and broad adversarial
  coverage have not been validated. Fresh validation reuses the existing Ollama
  service and package cache; it is not a brand-new-machine benchmark.
- No conversation memory, production booking authentication, real cancellation,
  payment integration, or network API is implemented. This is a demo over supplied data.
- The policy does not specify rounding for hypothetical half-cent refunds.

With more time: improve minimal routing/evidence selection, add fresh paraphrases
and adversarial cases, compare a smaller tool-capable model under the same checks,
and add CLI/configuration tests and CI. Keep evaluations honest rather than tuning
the checker solely to obtain a perfect score.
