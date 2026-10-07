"""Command line of the assist package: one sub-parser per group of commands."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from assist.cite import cli as cite_cli
from assist.cite.config import CiteError
from assist.cite3 import cli as cite3_cli

EXIT_OK = 0
EXIT_FOUND = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m assist",
        description="Tooling for the laisiangtho/bible repository.",
    )
    groups = parser.add_subparsers(dest="group", metavar="group", required=True)
    cite_cli.register(groups)
    cite3_cli.register(groups)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.run(args)
    except CiteError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    except BrokenPipeError:
        # Output was piped into a command that stopped reading, such as head.
        sys.stderr.close()
        return EXIT_OK
