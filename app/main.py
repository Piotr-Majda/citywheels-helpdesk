"""CLI entry point. Run with: python -m app.main."""

import argparse
import logging
import os
import sys
from time import perf_counter

from app.agent import ask, build_agent
from app.config import Settings


def main() -> int:
    """Ask the configured model a question through the help desk tools."""
    parser = argparse.ArgumentParser(description="CityWheels help desk CLI")
    parser.add_argument("question", nargs="+", help="Customer question")
    parser.add_argument("--verbose", action="store_true", help="Show timing and tool calls on stderr")
    args = parser.parse_args()
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    started = perf_counter()
    try:
        settings = Settings.from_env()
        result = ask(build_agent(settings.create_model()), " ".join(args.question))
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except Exception as error:
        # Avoid printing provider payloads, credentials, or source file contents.
        print(
            f"Unable to answer ({type(error).__name__}). Check provider configuration, "
            "model availability and data files, or contact staff.", file=sys.stderr,
        )
        return 1
    print(result.output)
    if args.verbose:
        calls = [call["tool"] for call in result.calls]
        usage = result.usage
        print(f"provider={settings.provider} model={settings.model} "
              f"elapsed={perf_counter() - started:.2f}s tools={calls} "
              f"requests={usage.requests} tokens={usage.total_tokens} error={result.error} "
              f"stages={[(stage['phase'], stage['elapsed_seconds']) for stage in result.stages]}", file=sys.stderr)
    return 1 if result.error else 0


if __name__ == "__main__":
    raise SystemExit(main())
