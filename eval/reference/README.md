# OpenAI and Ollama reference results

The current comparison uses saved real-model runs with the **same application fingerprint, ten questions, grading code, limits, temperature, output-token cap, and Pydantic AI version**. No application code was changed and no model calls were made to save these reports.

**Comparison checks: PASS.** [Machine-readable checks](comparison-checks.json) verify matching metadata, complete runs, identical questions, consistent pass counts, and snapshot integrity. [The manifest](manifest.json) preserves original metadata and report SHA-256 checksums.

| Metric | Ollama `llama3.1:8b` (current) | OpenAI `gpt-5.4-nano` |
| --- | ---: | ---: |
| Overall pass | 7/10 | 10/10 |
| Answer checks | 10/10 | 10/10 |
| Tool checks | 7/10 | 10/10 |
| Runtime checks | 10/10 | 10/10 |
| Median seconds | 19.084 | 2.320 |
| Maximum seconds | 49.842 | 4.391 |
| Total case seconds | 205.858 | 25.230 |
| Model requests | 29 | 21 |
| Business-tool executions | 19 | 11 |
| Reported total tokens | 10902 | 8688 |

| Case | Ollama | OpenAI | Ollama seconds | OpenAI seconds |
| --- | --- | --- | ---: | ---: |
| opening_hours | PASS | PASS | 49.842 | 3.507 |
| ebike_price | PASS | PASS | 14.466 | 4.391 |
| age_limit | PASS | PASS | 23.703 | 3.707 |
| booking_details | PASS | PASS | 10.597 | 2.047 |
| half_refund | FAIL | PASS | 28.747 | 2.480 |
| deposit_only | PASS | PASS | 10.140 | 3.221 |
| already_cancelled | FAIL | PASS | 25.386 | 1.802 |
| unknown_booking | FAIL | PASS | 36.807 | 2.160 |
| out_of_scope_geography | PASS | PASS | 3.113 | 0.986 |
| out_of_scope_recipe | PASS | PASS | 3.057 | 0.929 |

## What failed in Ollama

- `half_refund`: correct 340 EUR calculation, but unrelated accident/theft FAQ sections were requested and quoted.
- `already_cancelled`: correct refusal of another refund, but unrelated FAQ sections and an unnecessary booking-details lookup were added. The recorded checker failure is the unrelated FAQ selection.
- `unknown_booking`: correct not-found result, but the entire FAQ was retrieved and an unrelated opening-hours quotation was added. The policy-tool calls were unexpected for this question.

All ten answer-pattern and runtime checks pass. The three overall failures are tool-selection failures. Passing answer checks does not establish relevance of every sentence. The evidence validator checks that quotations exist in retrieved sources; it does not establish that they answer the question.

## Reports and provenance

- [Current Ollama report](ollama-llama3.1-8b-current/results.md) and [raw JSON](ollama-llama3.1-8b-current/results.json): **7/10**, same application as OpenAI.
- [OpenAI report](openai-gpt-5.4-nano/results.md) and [raw JSON](openai-gpt-5.4-nano/results.json): **10/10**.
- [Historical v0.1.0 Ollama report](ollama-llama3.1-8b/results.md) and [raw JSON](ollama-llama3.1-8b/results.json): **8/10**, different application code; excluded from the current comparison above.

Original model outputs, failures, stage timings, and source metadata are preserved. Both current runs used uncommitted source changes; the shared base Git commit alone does not identify evaluated code. The matching application SHA-256 fingerprint does.

## Limits and future runs

These are single runs, not statistical reliability estimates. Latency also reflects local hardware, hosted-provider load, network, and caching. Costs were not measured; reported token counts may be accounted for differently. The additional five cases were not compared for these current snapshots.

`eval/results.*` currently holds the latest Ollama run and may be overwritten by another evaluation. Reference snapshots remain separate. Save future runs to a new directory, for example `uv run python -m eval.run --output eval/local-run/next-run`, and do not overwrite the reference snapshots.
