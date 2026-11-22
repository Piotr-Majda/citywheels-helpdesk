# Agent comparison

Model: `llama3.1:8b`. Same cases, checks, and global case budgets.
Architecture: `single-agent` → `manager-specialists-v1`.
Deterministic business-tool implementations are unchanged; prompts, orchestration, and evidence checks may differ.
One run per version: these observations do not establish statistical significance.

| Metric | Before | After |
| --- | ---: | ---: |
| Overall pass | 4/10 | 8/10 |
| Answer checks | 4/10 | 9/10 |
| Tools checks | 7/10 | 9/10 |
| Runtime checks | 10/10 | 10/10 |
| Median seconds | 14.704 | 16.749 |
| Maximum seconds | 58.233 | 31.071 |
| Total model requests | 17 | 30 |
| Total business tool calls | 7 | 20 |
| Per-request output-token cap | not set | 1024 |

| Case | Before | After | Before seconds | After seconds |
| --- | --- | --- | ---: | ---: |
| opening_hours | FAIL | PASS | 58.233 | 22.809 |
| ebike_price | FAIL | PASS | 14.277 | 16.443 |
| age_limit | FAIL | FAIL | 17.974 | 17.055 |
| booking_details | PASS | PASS | 13.307 | 6.942 |
| half_refund | FAIL | PASS | 16.398 | 18.022 |
| deposit_only | FAIL | PASS | 15.989 | 15.740 |
| already_cancelled | PASS | PASS | 15.132 | 21.558 |
| unknown_booking | PASS | FAIL | 11.723 | 31.071 |
| out_of_scope_geography | PASS | PASS | 12.479 | 3.236 |
| out_of_scope_recipe | FAIL | PASS | 7.897 | 2.417 |

Both runs include first-case initialization and later warm-cache behavior.
The ten questions informed prompt development; additional cases are reported separately in `holdout/results.md`.
A passing automatic check is not proof that every sentence is correct; inspect both full reports.
