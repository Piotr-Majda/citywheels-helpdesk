"""Compare saved runs without making any model calls."""

import argparse
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, default=ROOT / "baseline/results.json")
    parser.add_argument("--after", type=Path, default=ROOT / "results.json")
    parser.add_argument("--output", type=Path, default=ROOT / "comparison.md")
    args = parser.parse_args()
    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = json.loads(args.after.read_text(encoding="utf-8"))
    for run in (before, after):
        if run["completed"] != run["metadata"]["case_count"]:
            raise ValueError("Cannot compare incomplete runs")
    for key in ("provider", "model", "cases_sha256", "checks_sha256", "temperature", "provider_retries", "limits"):
        if before["metadata"][key] != after["metadata"][key]:
            raise ValueError(f"Runs differ in {key}; comparison would be misleading")
    old = {row["id"]: row for row in before["results"]}
    new = {row["id"]: row for row in after["results"]}
    if old.keys() != new.keys():
        raise ValueError("Case IDs differ")
    lines = ["# Agent comparison", "",
             f"Model: `{after['metadata']['model']}`. Same cases, checks, and global case budgets.",
             f"Architecture: `{before['metadata'].get('architecture', 'single-agent')}` → `{after['metadata'].get('architecture', 'single-agent')}`.",
             "Deterministic business-tool implementations are unchanged; prompts, orchestration, and evidence checks may differ.",
             "One run per version: these observations do not establish statistical significance.", "",
             "| Metric | Before | After |", "| --- | ---: | ---: |",
             f"| Overall pass | {before['passed']}/{len(old)} | {after['passed']}/{len(new)} |"]
    for group in ("answer", "tools", "runtime"):
        counts = [sum(not row["failures"][group] for row in run["results"]) for run in (before, after)]
        lines.append(f"| {group.title()} checks | {counts[0]}/{len(old)} | {counts[1]}/{len(new)} |")
    for title, aggregate in (("Median seconds", statistics.median), ("Maximum seconds", max)):
        values = [aggregate(row["elapsed_seconds"] for row in run["results"]) for run in (before, after)]
        lines.append(f"| {title} | {values[0]:.3f} | {values[1]:.3f} |")
    for title, measure in (("Total model requests", lambda row: row["requests"]),
                           ("Total business tool calls", lambda row: len(row["calls"]))):
        values = [sum(measure(row) for row in run["results"]) for run in (before, after)]
        lines.append(f"| {title} | {values[0]} | {values[1]} |")
    lines.append(f"| Per-request output-token cap | {before['metadata'].get('max_output_tokens_per_request', 'not set')} | {after['metadata'].get('max_output_tokens_per_request', 'not set')} |")
    lines += ["", "| Case | Before | After | Before seconds | After seconds |",
              "| --- | --- | --- | ---: | ---: |"]
    for key, row in old.items():
        latest = new[key]
        lines.append(f"| {key} | {'PASS' if row['passed'] else 'FAIL'} | {'PASS' if latest['passed'] else 'FAIL'} | {row['elapsed_seconds']:.3f} | {latest['elapsed_seconds']:.3f} |")
    lines += ["", "Both runs include first-case initialization and later warm-cache behavior.",
              "The ten questions informed prompt development; additional cases are reported separately in `holdout/results.md`.",
              "A passing automatic check is not proof that every sentence is correct; inspect both full reports."]
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
