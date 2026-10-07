"""Commands of ``python3 -m assist cite3``: the move from format 2 to format 3."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from assist.cite import config as configuration
from assist.cite import store
from assist.cite.config import CiteError
from assist.cite3 import convert, roundtrip, tables

EXIT_OK = 0
EXIT_FOUND = 1


def register(groups: argparse._SubParsersAction) -> None:
    group = groups.add_parser(
        "cite3",
        help="Zolai-English dictionary source, format 3",
        description="Convert the dictionary source to the tables of format 3 and prove the conversion.",
    )
    commands = group.add_subparsers(dest="command", metavar="command", required=True)

    def command(name: str, run: Callable, summary: str) -> argparse.ArgumentParser:
        parser = commands.add_parser(name, help=summary, description=summary)
        parser.set_defaults(run=run)
        return parser

    parser = command("convert", run_convert, "Convert the format 2 files to tables.")
    parser.add_argument("directory", type=Path, help="folder that receives the tables")
    parser.add_argument("--apply", action="store_true", help="write the tables (default: dry run)")

    parser = command("roundtrip", run_roundtrip, "Compare the tables of a folder with the format 2 files.")
    parser.add_argument("directory", type=Path, help="folder that holds the tables")


def _load():
    config = configuration.load()
    data = store.load(config)
    for file in data.every_file():
        if file.findings:
            first = file.findings[0]
            raise CiteError(f"{file.name}: {first.rule} {first.detail}; run 'cite check' first")
    return config, data


def run_convert(args: argparse.Namespace) -> int:
    config, data = _load()
    converted = convert.convert(config, data)
    report = roundtrip.compare(config, data, converted)
    for name, rows in converted.items():
        print(f"{name}: {len(rows)} rows")
    for line in roundtrip.text(report):
        print(line)
    if not report.equal:
        raise CiteError("the tables do not return the format 2 rows; nothing is written")
    if not args.apply:
        print("dry run: nothing written; add --apply to write the tables")
        return EXIT_OK
    written = tables.write_all(args.directory, converted)
    print(f"{len(written)} files written to {args.directory}")
    return EXIT_OK


def run_roundtrip(args: argparse.Namespace) -> int:
    config, data = _load()
    report = roundtrip.compare(config, data, tables.read_all(args.directory))
    for line in roundtrip.text(report):
        print(line)
    return EXIT_OK if report.equal else EXIT_FOUND
