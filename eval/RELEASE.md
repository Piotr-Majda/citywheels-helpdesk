# Evaluated solution version — v0.1.0

Repository snapshot: [v0.1.0](https://github.com/Piotr-Majda/citywheels-helpdesk/tree/v0.1.0).
The exact commit is resolved with `git rev-parse 'v0.1.0^{commit}'`. Python project
version: **0.1.0**. Machine-readable binding: [release.json](release.json).

| Report | Result | Model |
| --- | --- | --- |
| [Original ten cases](reference/ollama-llama3.1-8b/results.md) / [JSON](reference/ollama-llama3.1-8b/results.json) | **8/10** | Ollama `llama3.1:8b` |
| [Five additional cases](holdout/results.md) / [JSON](holdout/results.json) | **3/5** | Same model |
| [Baseline comparison](comparison.md) | **4/10 → 8/10** | Same model |

These reports contain real model responses, timings, tool arguments/results,
rejected attempts, and stage diagnostics. Failed checks remain visible.

This document and `release.json` bind the historical v0.1.0 tag, not current main.
Paths recorded in that release manifest refer to the tagged tree. The original
ten-case report is also preserved byte for byte in `reference/ollama-llama3.1-8b/`;
current `eval/results.*` can contain a later run. Current same-code OpenAI/Ollama
results and their checksums are in [the reference comparison](reference/README.md).

## Honest version binding

The runs were recorded before the final implementation was committed. Therefore
their original metadata correctly names base commit `8c8b94b` and
`working_tree_dirty: true`. That commit alone is **not** the evaluated final code.
Those fields have not been rewritten to pretend otherwise.

During release preparation, both recorded application fingerprints were verified
against the actual application source. `release.json` records that original raw
fingerprint and a canonical LF-normalized fingerprint for the tagged source,
plus individual application files, case files, checker, dependency lockfile,
data files, and raw JSON reports. LF normalization accounts only for Git's
CRLF/LF conversion; it does not change code semantics. Fresh-checkout validation
checks these fingerprints before executing tests and a real CLI request.

Cleanup removed the unused root greeting script and FastAPI dependency. Application
logic/prompts and the evaluator's checks/cases were not changed for release, so
the saved model results remain the evaluated behavior rather than invented reruns.
The exact dependencies are pinned by `uv.lock`; Pydantic AI remains 2.71.0.

See [fresh-checkout verification](../docs/VERIFICATION.md) for the separate clean
installation result and [INSTALL.md](../INSTALL.md) to reproduce setup. Model
outputs and latency can vary; successful fresh execution is not a new ten-case
benchmark score. Local reruns should use a separate output directory.
