# CityWheels help desk

A Python CLI agent for a fictional bike rental shop. It answers policy questions,
looks up supplied bookings, and quotes cancellation refunds. It supports **OpenAI**
and **Ollama**, with one provider selected per run.

The LLM routes questions and selects evidence. Small deterministic Python tools
retrieve exact policy sections, validate booking data, and calculate money. The
agent does not change bookings, issue payments, or expose an HTTP API.

## Current verification

| Check | OpenAI `gpt-5.4-nano` | Ollama `llama3.1:8b` |
| --- | ---: | ---: |
| Ten-case evaluation | **10/10** | **7/10** |
| Answer / tool / runtime checks | 10/10 / 10/10 / 10/10 | 10/10 / 7/10 / 10/10 |
| Median response time | 2.320 s | 19.084 s |
| Maximum response time | 4.391 s | 49.842 s |

Both saved runs use the same application fingerprint, questions, checker, and
execution limits. They are single observations, not reliability guarantees.
Ollama's failures concern unnecessary policy/tool selections, including irrelevant
text beside correct booking/refund facts. Cost was not measured.

The offline suite passes **151 tests**, on Windows and in Docker with container
networking disabled. Native inference was tested with both providers. Docker
images, CLI help, and server health were checked; live inference through Docker
was not verified. [SOLUTION.md](SOLUTION.md) explains the decisions, evaluation
limitations, and full supporting reports.

## Native setup

Requires Git, [uv](https://docs.astral.sh/uv/getting-started/installation/),
Python 3.14+, and either OpenAI credentials or a running Ollama instance.
Run commands from the repository root. Examples use PowerShell; `cp` can replace
`Copy-Item` on Linux/macOS.

```powershell
git clone --branch main https://github.com/Piotr-Majda/citywheels-helpdesk.git
cd citywheels-helpdesk
uv python install 3.14
uv sync --locked
Copy-Item .env.example .env
```

`uv sync --locked` creates `.venv` from pinned dependencies, including pytest.
Activation is unnecessary. Python, package, and model downloads need network access.

### OpenAI

Edit the root `.env`:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.4-nano
OPENAI_API_KEY=your-key
```

This is the OpenAI model used in the saved reference. Your account must have
access to the configured model; real requests use your API credits.

### Ollama

Install [Ollama](https://ollama.com/download), start its service, and obtain the
evaluated local model:

```powershell
ollama pull llama3.1:8b
ollama list
```

If the service is not running, start `ollama serve` in another terminal.
Use these values in `.env`:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

Ollama is the application default and needs no API key. Memory and latency depend
on hardware. The recorded local environment was a 24-GB Windows laptop with a
Ryzen AI 9 365 and integrated Radeon 880M graphics.

### Configuration and execution

Pydantic Settings automatically reads the repository-root `.env`. Process
environment variables override file values. To switch providers, edit `.env` and
check for old exported `LLM_PROVIDER`/`LLM_MODEL` overrides. OpenAI requires an
explicit model and key. There is no automatic provider fallback. `.env` is excluded
from Git and Docker builds.

```powershell
uv run --locked python -m app.main --help
uv run --locked python -m app.main "Can my 14-year-old rent an electric bike?"
uv run --locked python -m app.main --verbose "How much will I get back for CW-1002?"
```

The assignment fixes the business clock at **2026-06-10 09:00 Europe/Warsaw
(UTC+02:00)**. CW-1002 therefore has a **340 EUR** refund: 40 EUR rental plus
300 EUR deposit, with the 2 EUR booking fee retained. This quotes an amount;
it does not perform a cancellation.

Answers go to stdout. `--verbose` writes provider/model, time, tool names, request
and token counts, stages, and errors to stderr. Execution/configuration or evidence
failures return a nonzero exit code and a staff-contact fallback.

## Tests and real evaluations

```powershell
uv run --locked pytest -q
uv run --locked python -m eval.run --output eval/local-run/review
uv run --locked python -m eval.run --cases eval/holdout_cases.json --output eval/local-holdout
```

Pytest needs no live model, network access, or API key. Tests use injected loaders,
fake model responses, and an injected HTTP transport. Temporary files live under
`.pytest_tmp/`; do not store project files there.

Evaluations call the configured provider and save real answers, timings, tool
arguments/results, failures, and metadata as Markdown and JSON. Exit 0 means all
checks passed; exit 1 means at least one failed. Use a separate output directory
to preserve references. Run each provider separately after changing configuration.
The five extra cases have historical results only, not a current two-model comparison.

| Limit per question | CLI | Evaluation |
| --- | ---: | ---: |
| Model requests | 6 | 5 |
| Business-tool executions | 8 | 4 |
| Enforced deadline | 180 s | 120 s |
| Performance target | — | 60 s |

All stages share these limits. The 60-second target is a project benchmark,
not an assignment requirement. Correct facts can still fail tool/runtime checks.
Passing pattern checks do not establish relevance of every sentence.

## Docker and Compose

Requires Docker Engine with Compose v2, or Docker Desktop using Linux containers.
Host Python and uv are unnecessary. This remains a CLI; no app port is published.

### OpenAI in Docker

```powershell
Copy-Item compose.env.example .env
# Edit .env: set LLM_MODEL=gpt-5.4-nano and your OPENAI_API_KEY.
docker compose build helpdesk
docker compose run --rm helpdesk "How much will I get back for CW-1002?"
```

Compose injects credentials at runtime. Exported variables override `.env`.
The app image runs as non-root and excludes `.env`, Git history, pytest, and test
sources. Real model access requires outbound connectivity.

```powershell
docker compose build tests
docker compose run --rm tests
```

The separate test service disables networking and receives no provider credentials.

### Ollama in Docker

```powershell
docker compose -f compose.yaml -f compose.ollama.yaml up -d --wait ollama
docker compose -f compose.yaml -f compose.ollama.yaml exec ollama ollama pull llama3.1:8b
docker compose -f compose.yaml -f compose.ollama.yaml run --rm helpdesk "What are your opening hours?"
docker compose -f compose.yaml -f compose.ollama.yaml down
```

The overlay selects `http://ollama:11434/v1` and uses `OLLAMA_MODEL` (default
`llama3.1:8b`) independently of `LLM_MODEL`. Pull that exact model if changing it.
The CPU-only service publishes no host port; models persist in a named volume.
Health checks verify the server, not model availability. `down` preserves volumes;
adding `--volumes` deletes downloaded models and reports.

For an existing host Ollama instead, set `LLM_PROVIDER=ollama`,
`LLM_MODEL=llama3.1:8b`, and
`DOCKER_OLLAMA_BASE_URL=http://host.docker.internal:11434/v1` in `.env`, then use
normal Compose commands. `localhost` inside a container is not the host; Linux
hosts may need additional Ollama listener/network configuration.

### Docker evaluation reports

```powershell
docker compose run --name citywheels-eval evaluation
New-Item -ItemType Directory -Force eval/docker-results
docker cp citywheels-eval:/reports/. ./eval/docker-results/
docker rm citywheels-eval
```

Include both `-f` options with the Ollama overlay. Reports persist in the `/reports`
named volume; later evaluations replace its report files. Copy them before reusing
the container name. Exit 1 still permits copying from the stopped container.
Packaged evaluations record null Git fields and `git_metadata_available: false`,
while retaining source fingerprints.

## Project layout and assumptions

| Location | Purpose |
| --- | --- |
| `app/main.py` | CLI entry point |
| `app/config.py` | OpenAI/Ollama configuration |
| `app/agent.py`, `app/specialists.py`, `app/prompts.py` | Manager, narrow specialists, evidence checks |
| `app/tools/` | Deterministic catalogue, policy, booking, and refund tools |
| `app/models/`, `app/db/` | Validated models and injectable file loaders |
| `tests/<feature>/test_*.py` | Pytest unit and workflow tests |
| `data/bookings.json`, `data/policies/` | Supplied bookings and three policy documents |
| `eval/` | Runner, checker, cases, generated reports, and JSON manifests |

Bookings use explicit statuses, timezone-aware dates, bike counts/types, add-ons,
Decimal money values, and a card/voucher rental-payment method. Rental price
includes add-ons; the non-refundable booking fee and refundable deposit are
separate components. The deposit's own payment method is not separately recorded.

Policy Markdown is application data; generated evaluation reports are evidence.
The project's two documentation entry points are this README and
[SOLUTION.md](SOLUTION.md).

## Troubleshooting

- Connection/model errors: verify the service and configured model. Ollama URLs
  must end in `/v1`; `ollama list` shows installed models.
- Unexpected provider/model: check exported variables overriding `.env`.
- Staff fallback: use `--verbose` to distinguish configuration, routing, budget,
  source, and evidence failures. A source-backed quotation can still be irrelevant.
- Restricted Windows test environments: asyncio needs a local socket pair even
  with fake models. Run pytest from a normal terminal.
