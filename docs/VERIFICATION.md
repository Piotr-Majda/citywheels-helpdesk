# Fresh-checkout verification — v0.1.0

Verified on 22 November 2026 on Windows, using an independent local Git clone
of source commit [`89c3ae660b80889ade0a5031d1ff1001d441273d`](https://github.com/Piotr-Majda/citywheels-helpdesk/commit/89c3ae660b80889ade0a5031d1ff1001d441273d).
This file was added in a documentation-only follow-up before tagging the release.
The released application tree is unchanged from that tested source commit:
`8525c1ac40b278c026025815994095627a88919d`.

## Environment and isolation

- Python **3.14.0**, uv **0.9.7**, pytest **9.2.0**.
- Pydantic AI **2.71.0**, Pydantic **2.14.3**; dependencies installed from `uv.lock`.
- Independent clone with a newly created `.venv`; no copied environment or `.env`.
- Reused the existing uv package cache, Python installation, and local Ollama
  service/model. This was not a factory-new machine or a cold inference benchmark.
- FastAPI and Starlette were absent from the installed environment.

## Commands and results

| Check | Result |
| --- | --- |
| `uv sync --locked` | Created a new environment; installed 32 distributions successfully |
| `uv run --locked pytest -q` | **118 passed**, no skips; 19.76 seconds |
| `uv run --locked python -m app.main --help` | Exit 0; CLI help displayed |
| Release fingerprint verification | Application files, data, reports, cases, checker, lockfile, and package version matched `eval/release.json` |
| `git status --short` after tests and live execution | Clean |

Real execution used the installation guide's example, with the documented Ollama
values explicitly set in that terminal:

```powershell
$env:LLM_PROVIDER = "ollama"
$env:LLM_MODEL = "llama3.1:8b"
$env:OLLAMA_BASE_URL = "http://localhost:11434/v1"
uv run --locked python -m app.main --verbose "How much will I get back for CW-1002?"
```

Observed answer:

> Booking CW-1002. Total refund: 340.0 EUR. Rental refund: 40.0 EUR. Deposit refund:
> 300.0 EUR. Booking fee retained: 2.0 EUR. Rental refund goes to the original card.
> The deposit follows its original payment method.

Exit code **0**, `error=None`, **2 model requests**, one `calculate_refund` execution,
**44.04 seconds** end to end. Router phase: 36.625 seconds; refund specialist:
7.239 seconds. These are observations from one smoke request, not a replacement
for the saved evaluation scores of **8/10** and **3/5**.

The host's restricted Windows sandbox blocked Git's shell initialization and
asyncio's socket setup. The clone/test/live commands succeeded outside that
sandbox, as they would run in a normal terminal. No external model API or paid key
was used; runtime model requests went to local Ollama.

The final documentation commit changes only this verification record and release
binding documentation/metadata. The application, tests, business data, dependency
lock, and evaluation cases/checker are identical to the tested source commit.
