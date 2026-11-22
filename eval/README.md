# Real-model evaluation

Run from the repository root with Ollama running and the configured model installed:

```powershell
uv run python -m eval.run
```

The default provider/model are Ollama and `llama3.1:8b`. To compare another installed
model, set `LLM_MODEL` and use a separate output directory to preserve the baseline:

```powershell
$env:LLM_MODEL = "your-installed-model"
uv run python -m eval.run --output eval/comparison
```

The initial prompt's ten-case results are preserved under `eval/baseline/`.
The longer-prompt experiment is archived under `eval/long_prompt/`, including its
additional-case results. `eval/results.*` holds the latest run on the unchanged
ten-case suite. Current short role prompts live in `app/prompts.py`; the original
agent source is archived as `eval/baseline/agent_before.py.txt` for comparison.

The current architecture routes to narrow specialists. Catalogue discovery is
forced by Python for policy tasks; specialists select their allowed tool's exact
arguments. Traces label application-origin versus model-origin executions.
Manager/specialist/synthesis phases share the original global request/tool/time
budgets. Reports now include phase timings and all raw model tool-call attempts,
so rejected arguments are not hidden by the successful execution trace.

The checker now also marks rejected/unexecuted model attempts as tool failures.
Saved baseline outputs were regraded without new inference; scores did not change.
Metadata records that regrading, allowing comparison using matching checker hashes.

The final manager/specialist run scored 8/10 on the original cases and 3/5 on the
additional cases. All original runtime checks passed. Policy output is now an
extractive summary, not an unrestricted paraphrase. Some correct excerpts fail
strict wording checks (for example, quoting a minimum age rather than explicitly
saying "no"). Valid but unnecessary policy selections also fail tool checks.
These failures remain in the score; the full text and traces distinguish them
from fabricated facts. Intermediate workflow runs are archived under
`workflow_v1/` and `workflow_v2/` so the implementation history remains reviewable.

After completing the new ten-case run, generate a comparison without model calls:

```powershell
uv run python -m eval.compare
```

The comparison checks that cases, grading code, provider/model, and limits match.
It reports both pass counts and latency, so a longer prompt is not assumed to
be an improvement merely because it contains more instructions.

Five additional cases were written before observing the revised prompt's outputs:
cash deposits, late-return rules, storm review, a voucher refund, and an instruction
to invent missing booking details. Run them separately:

```powershell
uv run python -m eval.run --cases eval/holdout_cases.json --output eval/holdout
```

These are additional development checks, not a statistically independent benchmark.
The developer knows the domain and the original ten questions informed the prompt.
After inspecting these five results they also become development data; future
generalization checks should add new cases rather than claim this set is unseen.

The runner uses the same agent and tools as the CLI. Each case starts a new
conversation, runs sequentially, and saves progress after completion. Exit code
0 means all checks passed; 1 means at least one failed. Interrupted runs can have
partial reports: compare `completed` with `metadata.case_count` in results.json.

## Cases and expected behavior

`cases.json` defines ten questions: opening hours, day pricing, age restrictions,
booking details, two refund calculations, an already-cancelled booking, an unknown
booking, and two unrelated questions requiring refusal and staff contact.

Checks cover:

- Required answer facts, currency for prices/refunds, refusal/contact wording,
  and selected forbidden content. Patterns allow multiple phrasings.
- Required and allowed tools; exact booking IDs; valid policy IDs and topic
  names; expected policy/topic retrieval and catalogue order.
- Actual refund tool totals/components and ineligible/not-found results.
- Missing results, tool retries, repeated identical calls, and execution errors.
- End-to-end time, model response count, and tool call count.

The target is at most 60 seconds, five model requests, four tool calls, and no
identical repeated calls per question. The agent enforces the request/call limits
and a 120-second run timeout. An answer taking 80 seconds can be correct but fails
the runtime target. The 60-second target is our benchmark, not a recruitment
requirement. Provider transport retries are disabled; tool-validation retry is
allowed by the agent but marked as an evaluation failure for these simple cases.

## Reports and interpretation

- `results.md`: summary, full answers, failure reasons, and tool traces.
- `results.json`: machine-readable results, exact arguments/results, timings,
  token usage when available, model settings, code/data fingerprints, and limits.

Results are real observations, not expected answers copied into a report. Tests
under `tests/evaluation/` exercise the checker with deliberately wrong amounts,
booking IDs, contradictory totals, skipped tools, repeats, retries, and timeouts.
They run with the standard `uv run pytest` command without a live model.

Automated checks are intentionally limited. A regex can miss a valid paraphrase
or accept an incorrect sentence that happens to contain expected words. The
checks do not prove semantic correctness or detect every invented detail. Review
the saved answers and traces as well as the score. Two unrelated prompts are not
a comprehensive prompt-injection or safety evaluation.

The first case may include model loading and initialization. Later cases benefit
from model/OS caches. No warm-up is excluded, and timings are not pure token
generation measurements. Different model/hardware runs should be compared under
similar conditions. Request counts on failed runs count captured model responses;
an incomplete request that timed out may have no response and is represented by
the run error rather than included in that count.
