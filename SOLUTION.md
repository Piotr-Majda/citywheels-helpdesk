# CityWheels: decisions and development evidence

This document explains the decisions, their development stage, rationale, and
observed consequences. [README.md](README.md) contains setup and use. The evaluated
models are **OpenAI `gpt-5.4-nano`** and **Ollama `llama3.1:8b`**. Both run the same
workflow and business tools; provider selection is configuration.

## Stage 1 — CLI scope and testable tools (20 November 2026)

**Decision:** implement `app/main.py` as a CLI, defer FastAPI, and place each tool
in its own `app/tools/` module. Use pytest only, grouped by feature.

**Reason:** the CLI meets the assignment interface requirement. An HTTP server
adds deployment concerns without improving the core task. Independent tools can
be reviewed and tested before introducing a model. The final source/dependencies
remove FastAPI and the unused greeting starter.

**Decision:** explicitly inject booking/policy loaders and the cancellation clock;
use `BookingBase` for shared validation and `BookingRead` for results; remove the
global booking cache.

**Reason:** tests can supply isolated fake data without monkeypatching globals.
For ten supplied bookings a cache adds state with little benefit. Validation
distinguishes unknown bookings from broken source data. Duplicate IDs fail instead
of overwriting records. Statuses match the supplied data; dates are timezone-aware
and money uses Decimal. Read-model fields cannot be reassigned, although nested
lists remain mutable.

**Evidence:** loader/tool tests cover missing files, malformed JSON, duplicate IDs,
failed-load recovery, dependency isolation, and invalid booking fields. The Windows
temporary-directory problem was addressed with project-local pytest temporary
storage. No feature-template tests remain skipped.

## Stage 2 — deterministic retrieval and refund rules (22 November)

**Decision:** use `list_policy_topics()` and `search_policies(policy, topics)` rather
than vector search. The catalogue exposes three file IDs and exact `##` headings.
Retrieval returns selected sections with original Markdown, introduction, and source.

**Reason:** three small documents already have a useful taxonomy. Exact lookup is
predictable, explainable, and testable. Embeddings, chunking, similarity thresholds,
and vector storage would add uncertainty and operational work. The tradeoff is
that the model must select the right file and topic: valid selections can still
be irrelevant. A larger corpus could justify revisiting this decision.

**Decision:** calculate refunds in Python using Decimal, stored booking prices,
and the fixed clock **2026-06-10 09:00 Europe/Warsaw (UTC+02:00)**. Compare elapsed
time in UTC; the LLM performs no monetary arithmetic.

**Reason:** amounts and time boundaries must be reproducible and independently tested.

| Condition | Rental refund | Deposit | Booking fee |
| --- | --- | --- | --- |
| Confirmed; at least 48 hours before start | 100% | Returned | Retained |
| Confirmed; at least 24 but less than 48 hours | 50% | Returned | Retained |
| Confirmed; less than 24 hours | 0% | Returned | Retained |
| Any other status | No new cancellation refund | No new cancellation refund | No new cancellation refund |

Confirmed records whose start has passed use the zero-rental-refund tier; the
tool does not infer a status transition. Voucher rental refunds remain vouchers,
not cash. The deposit's separate payment method is unknown, so responses mention
only its original method. Storm exceptions and damage/theft decisions require
staff. No tool changes bookings or moves money. Policy rounding for hypothetical
half-cent refunds is unspecified and remains a limitation.

**Evidence:** tests cover 24/48-hour boundaries and one second below them, statuses,
vouchers, timestamps, source errors, and unknown bookings. CW-1002 returns 340 EUR:
40 EUR rental plus 300 EUR deposit, with the booking fee retained.

## Stage 3 — Ollama baseline and prompt experiments (22 November)

**Decision:** use Pydantic AI and one active provider per run. Begin with local
Ollama `llama3.1:8b`, already installed, while retaining an OpenAI adapter.
Tool wrappers expose business arguments only; Python injects dependencies.
There is no automatic local-to-cloud fallback.

**Reason:** Pydantic AI supplies typed output, validation, usage accounting, and
provider adapters. Local inference offers a credential-free setup. Explicit
provider choice avoids silently forwarding local questions to a cloud service.

**Observed problem:** correct tools and fluent output did not ensure correct
orchestration. The single-agent baseline passed **4/10**. A longer prompt with
workflows and examples also passed **4/10**, and **1/5** additional cases. Some runs
stopped after catalogue discovery or answered without retrieving the source.
Longer instructions alone were not demonstrated to improve the solution.

**Evidence:** [baseline](eval/baseline/results.md),
[longer prompt](eval/long_prompt/results.md), and
[additional cases](eval/long_prompt/holdout/results.md). These are historical
experiments, not current-application results.

## Stage 4 — manager and narrow specialists (22 November)

**Decision:** replace the broad single-agent loop with explicit sequential stages:

```text
Question
  -> manager: classify scope and select policy/booking/refund tasks
  -> Python: validate plan and discover required policy topics
  -> narrow specialists: choose arguments and execute their permitted tool
  -> Python: validate returned evidence
  -> manager: select exact policy quotations
  -> Python: render verified quotations and booking/refund facts
```

**Reason:** each specialist receives a smaller context and one relevant tool.
Successful specialist output is an executed Python tool result, rather than a
generated claim that execution occurred. Python forces catalogue discovery before
policy lookup. All stages use the same selected model, with separate contexts;
this is not recursive delegation or a collection of different model weights.

**Refinement:** simplify the initial nested plan to flat `policies`, `bookings`,
and `refunds` arrays, with at most four distinct tasks. Restrict booking-ID enums
to IDs present in the question and policy/topic enums to real documents.
These constraints prevent invented identifiers but do not establish relevance.

**Evidence:** early workflows passed [3/10](eval/workflow_v1/results.md) and
[6/10](eval/workflow_v2/results.md). Historical v0.1.0 reached
[8/10](eval/reference/ollama-llama3.1-8b/results.md), with
[3/5 additional cases](eval/holdout/results.md). The extra stages have a cost:
17 model requests across the original baseline versus 30 in v0.1.0. One run per
version does not establish statistical improvement or isolate every design change.

## Stage 5 — grounded rendering and bounded execution (22 November)

**Decision:** remove unrestricted policy paraphrases. The synthesizer returns only
`source_id` and exact quotations. Python verifies source membership and coverage,
then renders the quotes. Booking facts and refund amounts come directly from typed
tool results.

**Trigger and reason:** an earlier generated answer said the shop was closed while
quoting evidence saying it was open. Checking citations and numbers did not verify
that paraphrase. Extractive output reduces this failure mode, at the cost of less
conversational answers. Source membership still does not prove relevance or that
every necessary condition was included.

**Decision:** share one request/tool budget and deadline across stages, block
identical repeated business-tool calls, cap each response at 1024 tokens, and
disable provider transport retries. Tool-argument validation may retry once.

**Reason:** smaller contexts must not create an unbounded sequence of calls.
CLI defaults are six model requests, eight business-tool executions, and 180 seconds.
Evaluation uses five requests, four tool executions, a 120-second deadline, and a
separate 60-second performance target. Phase timings, raw responses, tools, results,
tokens, and failures explain where time went. Errors return a fallback instead of
unchecked partial answers.

## Stage 6 — OpenAI validation and targeted corrections (22 November)

**Decision:** evaluate OpenAI `gpt-5.4-nano` with the shared workflow and checks,
without changing the business tools for that provider.

**Trigger:** an initial OpenAI run failed `age_limit` during routing. It returned
`policies: ["ages", "helmets"]` rather than a file ID such as `faq`. Validation
rejected this before any tools ran. Routing had zero retries, and defaulted fields
made the schema incompatible with automatic OpenAI strict mode.

**Change and reason:** explicitly request `NativeOutput(..., strict=True)` for
routing, clarify file IDs versus specialist-selected topics, and permit one
validation retry within the existing budget. An injected HTTP transport test checks
the actual OpenAI strict-schema request. Fake-model tests verify recovery, retry
exhaustion, and shared limits. The input constraints remain provider-neutral.

**Related decisions:**

- Add staff contact when a selected quotation calls for staff involvement rather
  than on every policy response. Unused staff-related retrieved sections must not
  escalate an otherwise complete answer. This uses a limited phrase matcher.
- Preserve the explicit-refusal evaluation requirement for the 14-year-old question.
  A small Python renderer derives a negative electric-bike age conclusion from one
  unambiguous age and a minimum in selected quotations. It preserves source text,
  invents no threshold, and does not infer eligibility. Other phrasings receive
  policy quotations; this is deliberately limited language handling.
- Use Pydantic Settings for root `.env` loading, environment overrides, and
  `SecretStr` credentials. Pass dotenv-loaded keys explicitly to the provider:
  loading a file does not export its key into the SDK's process environment.
  Inject configuration sources in tests instead of monkeypatching globals.

**Evidence:** the targeted age case passed in 4.938 seconds, followed by the full
OpenAI run below. The current offline suite passes **151 tests**, with no skips,
including schema, configuration, retry, and age-conclusion regressions.

## Stage 7 — both models on matching code (22 November)

The current saved runs share application fingerprints, ten questions, checker,
limits, fixed business time, temperature, response cap, architecture, and Pydantic
AI version (2.71.0). **26/26 comparison checks passed.**

| Metric | OpenAI `gpt-5.4-nano` | Ollama `llama3.1:8b` |
| --- | ---: | ---: |
| Overall pass | **10/10** | **7/10** |
| Answer checks | 10/10 | 10/10 |
| Tool checks | 10/10 | 7/10 |
| Runtime checks | 10/10 | 10/10 |
| Median seconds | 2.320 | 19.084 |
| Maximum seconds | 4.391 | 49.842 |
| Total case seconds | 25.230 | 205.858 |
| Model requests | 21 | 29 |
| Business-tool executions | 11 | 19 |
| Reported total tokens | 8688 | 10902 |

Ollama's failures include correct required facts alongside unnecessary policy text:

| Case | Observed failure |
| --- | --- |
| `half_refund` | Correct 340 EUR total, plus unrelated accident/theft quotations. |
| `already_cancelled` | Correct refusal of another refund, plus unrelated FAQ text and an unnecessary booking-details lookup. The recorded checker failure is the FAQ selection. |
| `unknown_booking` | Correct not-found result, plus the entire FAQ retrieval and an irrelevant opening-hours quotation. |

**Decision:** retain the shared implementation and both providers; use OpenAI as
the stronger observed reference. Preserve Ollama failures instead of weakening the
checks or altering a working OpenAI workflow solely for this local model. Ollama
remains the default for credential-free local setup; default configuration and
observed quality are separate choices.

One run per model is not a reliability guarantee. Hardware versus hosted service,
network, load, caching, and token accounting differ. Cost was not measured. The five
additional cases have historical results only; they are now development data,
not an unseen benchmark. No broad model ranking or monetary-cost claim is supported.

### Evidence and source binding

- [OpenAI report](eval/reference/openai-gpt-5.4-nano/results.md) and
  [JSON](eval/reference/openai-gpt-5.4-nano/results.json).
- [Current Ollama report](eval/reference/ollama-llama3.1-8b-current/results.md)
  and [JSON](eval/reference/ollama-llama3.1-8b-current/results.json).
- [Comparison checks](eval/reference/comparison-checks.json) and
  [manifest](eval/reference/manifest.json), including report checksums and an
  LF-normalized binding to the published application files.
- [Ten questions](eval/cases.json), [extra questions](eval/holdout_cases.json),
  and [grading code](eval/checks.py).

Original metadata is preserved: current runs used an uncommitted tree based on an
earlier Git commit. The base commit alone is not evaluated-source identification;
application fingerprints provide that binding. Original reference bytes survive
Git line-ending conversion. `eval/results.*` may hold a later run, so fixed
references should be used for comparison. The historical [release manifest](eval/release.json)
refers to paths in the immutable v0.1.0 tag. Its 118-test verification and 8/10
score must not be presented as current results.

Grading checks required answer patterns, tool choices/arguments/results, rejected
attempts, repeats, budgets, and latency. It does not prove semantic correctness.
Ollama's irrelevant but source-backed text demonstrates why full traces matter
even when all answer-pattern checks pass.

## Stage 8 — packaging and review handoff (22–23 November)

**Decision:** supply pinned Python 3.14.0/uv 0.9.7 images, locked dependencies, a
non-root CLI image, a separate offline-test target, and Compose configurations for
OpenAI or internal CPU-only Ollama with persistent model storage. No HTTP server
or published app port is added.

**Reason:** reviewers can run without host Python while keeping credentials in
runtime settings. A separate test image keeps pytest out of production. Images
omit Git history, so packaged evaluations explicitly record unavailable Git
metadata instead of inventing a commit. Installation commands belong in README.

**Verified:** native and Docker suites both pass **151 tests**. Compose validation,
image builds, CLI help, and optional Ollama server health were checked. Container
inference was not verified; no model was downloaded into that server during
implementation. Current model reports measure native OpenAI and host Ollama.
Historical v0.1.0 had a separate clone/new-environment check recorded in its release
manifest; this is not a fresh-machine verification of current main.

**Documentation decision:** README covers setup and project assumptions; SOLUTION
covers decision stages, rationale, and evidence. Generated reports and JSON
manifests remain evaluation artifacts; policy Markdown remains input data. Separate
installation, Docker, evaluation-guide, and history documents are removed to avoid
duplicated, contradictory claims.

## AI assistance and remaining limits

Codex assisted with discussion, scaffolding, implementation, review, tests,
evaluations, and documentation. The developer selected CLI scope, pytest,
dependency injection, strict section retrieval, and the specialist workflow.
Generated changes were checked with tests and real runs. Earlier unittest
scaffolding was corrected to pytest; a policy-paraphrase contradiction drove the
extractive-rendering decision.

The model can still misclassify scope, select unnecessary valid tasks/topics,
or omit conditions. Exact quotes do not establish relevance. Extractive output and
the narrow age renderer are less flexible than conversation. There is no memory,
customer authentication, real booking mutation, payment integration, or production
API. Two unrelated prompts do not constitute a comprehensive safety evaluation;
other models/platforms are not validated.

Next work should use fresh paraphrases and adversarial cases, repeated model
runs, and explicit provider-specific experiments that preserve the OpenAI reference
and shared regressions. Vector retrieval or unrestricted synthesis should require
evidence that their added complexity improves task results.
