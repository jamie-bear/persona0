from __future__ import annotations

import argparse
import sys

from ..engine.modules._config import validate_runtime_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Persona0 healthcheck")
    parser.add_argument("--mode", choices=["liveness", "readiness"], default="readiness")
    args = parser.parse_args()

    if args.mode == "liveness":
        print("alive")
        return

    try:
        validate_runtime_config()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    print("ready")


if __name__ == "__main__":
    main()
