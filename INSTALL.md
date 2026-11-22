# Fresh installation and execution — v0.1.0

The commands below use Windows PowerShell and run from the repository root.
The tested interpreter is Python 3.14.0; `.python-version` requests the 3.14 series.

## 1. Install prerequisites

Install Git, [uv](https://docs.astral.sh/uv/getting-started/installation/), and
[Ollama for Windows](https://docs.ollama.com/windows). For example, uv is available
through WinGet:

```powershell
winget install --id=astral-sh.uv -e
```

Open a new terminal after installation and check:

```powershell
git --version
uv --version
ollama --version
```

## 2. Clone the marked version and create a new environment

```powershell
git clone --branch v0.1.0 https://github.com/Piotr-Majda/citywheels-helpdesk.git
cd citywheels-helpdesk
git describe --tags --exact-match
uv python install 3.14
uv sync --locked
```

Expected Git version marker: `v0.1.0`. `uv sync --locked` creates `.venv` from
`uv.lock`, including pytest. No activation or pre-existing virtual environment is
required. Python/package/model downloads require network access during setup.
The public repository clone needs no GitHub collaborator access.

## 3. Run the offline tests

```powershell
uv run --locked pytest
```

Release verification expects **118 passed**, no skips. No model, network call,
or API key is used by these tests. Pytest manages `.pytest_tmp/` under the working
directory; do not put project files there. Run from the repository root.

## 4. Start Ollama and obtain the model

Open the Ollama app. If it is not already serving requests, run `ollama serve` in
another terminal. Skip that command if the app is already listening on port 11434.
Then:

```powershell
ollama pull llama3.1:8b
Invoke-RestMethod http://localhost:11434/api/tags
```

The model should appear in the returned list. The model download is several GB
and runtime memory/latency depend on hardware. The recorded evaluation used a
24-GB Windows laptop with a Ryzen AI 9 365 and integrated Radeon 880M graphics.
No particular GPU acceleration is required by the application.

## 5. Ask a real question

Defaults work without setting environment variables:

```powershell
uv run --locked python -m app.main --help
uv run --locked python -m app.main --verbose "How much will I get back for CW-1002?"
```

At the assignment's fixed current time, CW-1002 has a **340 EUR** refund:
40 EUR rental refund plus 300 EUR deposit; the 2 EUR booking fee is retained.
Model routing can fail and produce a staff-contact fallback instead. The saved
evaluation describes observed failures; a correct setup does not guarantee every
model answer passes evaluation.

A request is bounded globally by six model calls, eight business-tool executions,
and 180 seconds. `--verbose` prints provider/model, phase timing, call names, usage,
and error state on stderr. Answers go to stdout. A nonzero exit code indicates an
execution or verification failure, rather than an approved cancellation.

## 6. Configure a provider explicitly (optional)

For Ollama:

```powershell
$env:LLM_PROVIDER = "ollama"
$env:LLM_MODEL = "llama3.1:8b"
$env:OLLAMA_BASE_URL = "http://localhost:11434/v1"
```

For OpenAI, replace the placeholders with your own available model and key:

```powershell
$env:LLM_PROVIDER = "openai"
$env:LLM_MODEL = "your-available-model"
$env:OPENAI_API_KEY = "your-key"
```

The OpenAI path is implemented but not live-tested. Environment variables apply
to the current terminal session. `.env.example` lists names; copying it to `.env`
does not automatically configure the application. Never commit a real key.

## 7. Run a real evaluation without overwriting recorded results

```powershell
uv run --locked python -m eval.run --output eval/local-run
uv run --locked python -m eval.run --cases eval/holdout_cases.json --output eval/local-holdout
```

Expect a few minutes of model execution. Each case has a 120-second enforced
deadline and a separate 60-second latency target, five-request cap, and four-tool
cap. Reports are saved incrementally as Markdown and JSON in the selected output
directory. Exit code 1 means one or more checks failed; it is not automatically
an installation error. The committed scores are **8/10** and **3/5**, not 100%.

[eval/RELEASE.md](eval/RELEASE.md) identifies the version/report binding;
[eval/README.md](eval/README.md) describes grading and comparison limitations.
[docs/VERIFICATION.md](docs/VERIFICATION.md) records the actual clean-checkout check.

## Troubleshooting

- Ollama connection error: check the app is running, port 11434 is reachable, and
  `OLLAMA_BASE_URL` ends in `/v1`.
- Model unavailable: run `ollama list` and select an installed tool-capable model.
- Configuration error after switching providers: check `LLM_PROVIDER`, `LLM_MODEL`,
  and, for OpenAI only, `OPENAI_API_KEY` in the same terminal used to run the CLI.
- Staff fallback with an error: use `--verbose` and inspect phase/error diagnostics.
  It can be an invalid model plan or evidence failure, not only a server issue.
- Tests blocked in a restricted Windows sandbox: asyncio requires a local socket
  pair even for fake-model tests. Run from a normal terminal; it does not require
  access to an external model service.
