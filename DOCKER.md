# Docker and Compose setup

This adds container packaging after the native `v0.1.0` release. Use a checkout
containing `Dockerfile` and `compose.yaml`; those files are not in the immutable
v0.1.0 tag. No host Python or uv installation is needed. Install Docker Engine
with Compose v2 on a server, or Docker Desktop with Linux containers on Windows/macOS.

The application remains a **CLI**: run commands in your terminal or over SSH.
There is no HTTP endpoint or browser interface, and the app publishes no ports.

## Online provider: OpenAI

Copy `compose.env.example` to `.env` and set your available OpenAI model ID and
API key. For example, on a Linux server:

```bash
cp compose.env.example .env
# Edit .env: replace LLM_MODEL and OPENAI_API_KEY with your real values.
docker compose build helpdesk
docker compose run --rm helpdesk "How much will I get back for CW-1002?"
```

On PowerShell, use `Copy-Item compose.env.example .env` instead of `cp`.
Compose reads `.env` and injects settings at runtime. The native Python CLI also
loads the root `.env` automatically through Pydantic Settings. Exported environment
variables override file values.
An online model needs outbound internet and valid provider credentials. The
container build, tests, and CLI help do not need an API key. Do not commit `.env`.

```bash
docker compose run --rm helpdesk --help
docker compose run --rm helpdesk --verbose "What are your opening hours?"
```

Keys are provided only at container runtime, never as build arguments or files
copied into an image. Missing credentials/model configuration fails the request;
there is no automatic fallback to another provider. A live OpenAI request has not
been tested because no key was supplied.

## Offline tests in Docker

```bash
docker compose build tests
docker compose run --rm tests
```

The test image includes development dependencies. Its Compose service disables
networking and receives no provider credentials. **151 tests passed in Docker**,
including configuration, routing, policy-answer, and packaged Git-metadata checks.
The production image excludes pytest and the test source.

## Optional: run Ollama in Compose

This provides a self-contained alternative on a server without an online provider.
The baseline configuration is CPU-only; GPU passthrough is hardware/platform
specific and is not configured here. Model files are downloaded once into a named
volume and reused on subsequent starts.

```bash
docker compose -f compose.yaml -f compose.ollama.yaml up -d --wait ollama
docker compose -f compose.yaml -f compose.ollama.yaml exec ollama ollama pull llama3.1:8b
docker compose -f compose.yaml -f compose.ollama.yaml run --rm helpdesk "How much will I get back for CW-1002?"
```

The overlay sets the provider and internal URL (`http://ollama:11434/v1`), and uses
`OLLAMA_MODEL` (default `llama3.1:8b`) independently of the OpenAI model in `.env`.
If changing `OLLAMA_MODEL`, pull that exact model name too. The health check verifies
the server is ready; **it does not download a model or prove the model is installed**.
There is no published Ollama port, so it does not compete with host port 11434.

Stop the stack while keeping model/report volumes:

```bash
docker compose -f compose.yaml -f compose.ollama.yaml down
```

Do not add `--volumes` unless you intend to delete downloaded models and reports.
The server health path was tested with the pinned image. A container model was
not downloaded or run during implementation; this was intentionally deferred.

## Optional: an existing Ollama service

For a reachable existing service, set these values in `.env`:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
DOCKER_OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
```

Then use the default `docker compose run --rm helpdesk ...` command. Docker
Desktop provides host access; a plain Linux Docker host may require a reachable
host address and Ollama listener configuration. `localhost` inside the app
container means that container, not your host. If model discovery returns an empty
list, verify you reached the intended Ollama instance instead of downloading or
changing unrelated services automatically. The internal Compose service above
avoids dependence on host DNS/listeners.

## Real evaluation and persistent reports

The evaluation service shares the app image and provider configuration, with a
named volume at `/reports`. Git history is intentionally absent from the image:
reports record `git_metadata_available: false`, null Git fields, and actual
application/case/checker fingerprints instead of inventing a commit.

```bash
docker compose run --name citywheels-eval evaluation
mkdir -p eval/docker-results
docker cp citywheels-eval:/reports/. ./eval/docker-results/
docker rm citywheels-eval
```

For PowerShell, create the directory with
`New-Item -ItemType Directory -Force eval/docker-results`. Evaluation exit code 1
means a check failed; stopped containers can still be copied from. Remove the
named `citywheels-eval` container before reusing that name. The exported directory
is ignored by Git. Named-volume reports also survive container removal; another
evaluation to `/reports` replaces the previous report files there.

With containerized Ollama, include both `-f` options in the evaluation command as
well. No Docker live-model evaluation scores are claimed. Current native results
are **10/10 for OpenAI** and **7/10 for Ollama** on matching application code; see
[the reference comparison](eval/reference/README.md). Historical release scores
remain separate.

## Build details and verification limits

- Python 3.14.0 and uv 0.9.7 images are pinned by digest; dependencies use `uv.lock`.
- Runtime is non-root; host `.venv`, `.git`, `.env`, and private-key files are
  excluded from the allowlisted build context. Business data is baked into the image.
- Normal images contain only runtime dependencies. A separate target adds tests.
- Both Compose configurations validated, both images built, CLI help worked,
  and all 151 tests passed with networking disabled on Docker Desktop/Linux amd64.
- The optional Ollama service reached healthy status without exposing a host port.
- A host-backed CLI smoke test reached a different empty Ollama instance and
  returned model-not-found. No existing user service was modified. Further local
  model troubleshooting and duplicate model downloads were stopped at user request.

Reference: [uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/),
[Ollama Docker](https://docs.ollama.com/docker),
[Compose startup checks](https://docs.docker.com/compose/how-tos/startup-order/).
