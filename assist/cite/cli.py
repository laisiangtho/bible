"""Commands of ``python3 -m assist cite``."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections import Counter
from typing import Callable, List

from assist.cite import config as configuration
from assist.cite import convert, examples, markup, query, rules, store, words

EXIT_OK = 0
EXIT_FOUND = 1


def register(groups: argparse._SubParsersAction) -> None:
    group = groups.add_parser(
        "cite",
        help="Zolai-English dictionary source",
        description="Check, convert and query the dictionary source in cite/.",
    )
    commands = group.add_subparsers(dest="command", metavar="command", required=True)

    def command(name: str, run: Callable, summary: str) -> argparse.ArgumentParser:
        parser = commands.add_parser(name, help=summary, description=summary)
        parser.set_defaults(run=run)
        return parser

    parser = command("check", run_check, "Check every row against the markup rules.")
    parser.add_argument("--file", default="", help="report one listed file only, e.g. draft")
    parser.add_argument("--summary", action="store_true", help="print counts per rule, not each finding")

    parser = command("format", run_format, "Put valid rows into canonical form.")
    _writing(parser)

    parser = command("convert", run_convert, "Convert rows written before markup version 1.")
    _writing(parser)

    parser = command("words", run_words, "Generate the word lists from the Bible translations.")
    parser.add_argument("--language", default="", help="one configured language only, e.g. ctd")
    parser.add_argument("--apply", action="store_true", help="write the files (default: dry run)")

    parser = command("lookup", run_lookup, "Show the rows of a Zolai keyword or an English term.")
    parser.add_argument("query", nargs="+", help="keyword, or English term with --english")
    parser.add_argument("--english", action="store_true", help="look up an English term")
    parser.add_argument("--json", action="store_true", help="print JSON")

    parser = command("search", run_search, "Find the verses that contain a word, with parallel verses.")
    parser.add_argument("query", nargs="+", help="word or phrase")
    parser.add_argument("--source", default="", help="translation id to search (default: configured sources)")
    parser.add_argument("--limit", type=int, default=10, help="verses to show, 0 for all (default: 10)")

    parser = command("todo", run_todo, "List the most frequent words that have no row yet.")
    parser.add_argument("--limit", type=int, default=50, help="words to show, 0 for all (default: 50)")

    parser = command("examples", run_examples, "Report the rows whose examples do not yet show every English term.")
    parser.add_argument("--file", default="", help="one listed file only, e.g. draft")
    parser.add_argument("--limit", type=int, default=50, help="rows to show, 0 for all (default: 50)")

    parser = command("parse", run_parse, "Print every row as JSON. Refused while the check fails.")
    parser.add_argument("--file", default="", help="one listed file only, e.g. draft")


def _writing(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--apply", action="store_true", help="write the files (default: dry run)")
    parser.add_argument("--diff", action="store_true", help="print every changed line")


def _findings(config, files) -> List[rules.Finding]:
    found = [finding for data in files for finding in data.findings]
    found.extend(rules.check_rows(config, store.all_rows(files)))
    return found


def _report(config, found: List[rules.Finding], rows: int, files: int) -> None:
    errors = {(f.file, f.number) for f in found if f.is_error}
    form_only = {(f.file, f.number) for f in found} - errors
    print(
        f"{rows} rows in {files} files: {len(errors)} with errors, "
        f"{len(form_only)} with form issues only"
    )


def run_check(args: argparse.Namespace) -> int:
    config = configuration.load()
    files = store.read_files(config)
    found = _findings(config, files)
    if args.file:
        if args.file not in config.files:
            raise configuration.CiteError(
                f"'{args.file}' is not a listed file; listed: {', '.join(config.files)}"
            )
        # Keywords resolve across all files, so everything is checked and one file is reported.
        files = [data for data in files if data.key == args.file]
        found = [finding for finding in found if finding.file == files[0].name]
    rows = len(store.all_rows(files))
    if args.summary:
        for rule, number in sorted(Counter(finding.rule for finding in found).items()):
            print(f"{rule} {config.rules[rule]['name']}: {number}")
    else:
        order = {data.name: index for index, data in enumerate(files)}
        for finding in sorted(found, key=lambda f: (order.get(f.file, -1), f.number, f.rule)):
            print(finding.describe(config))
    _report(config, found, rows, len(files))
    return EXIT_FOUND if found else EXIT_OK


def _rewrite(args: argparse.Namespace, change: Callable, verb: str) -> int:
    """Apply a line-by-line change to every data file; dry run unless --apply."""
    config = configuration.load()
    files = store.read_files(config)
    unreadable = [data.name for data in files if not data.readable]
    if unreadable:
        raise configuration.CiteError(f"cannot read: {', '.join(unreadable)}; run the check")
    total = 0
    for data in files:
        new_lines = [change(config, line) for line in data.lines]
        changed = sum(1 for old, new in zip(data.lines, new_lines) if old != new)
        new_text = store.to_text(new_lines)
        differs = new_text != data.path.read_text(encoding="utf-8")
        total += changed
        if args.diff and changed:
            sys.stdout.writelines(
                difflib.unified_diff(
                    [line + "\n" for line in data.lines],
                    [line + "\n" for line in new_lines],
                    data.name, data.name, n=0,
                )
            )
        print(f"{data.name}: {changed} rows {'changed' if args.apply else 'to change'}")
        if args.apply and differs:
            store.write_text(data.path, new_text)
    if args.apply:
        print(f"{verb}: {total} rows written. Next: python3 -m assist cite check --summary")
    else:
        print(f"dry run: {total} rows would change. Add --apply to write.")
    return EXIT_OK


def _format_line(config, line: str) -> str:
    if not markup.is_row(line):
        return line.rstrip() if line.startswith(markup.COMMENT) else ""
    return markup.canonical(config, markup.parse(line)) or line


def run_format(args: argparse.Namespace) -> int:
    return _rewrite(args, _format_line, "format")


def run_convert(args: argparse.Namespace) -> int:
    return _rewrite(args, convert.convert_line, "convert")


def run_words(args: argparse.Namespace) -> int:
    config = configuration.load()
    languages = [args.language] if args.language else list(config.raw["word"]["language"])
    for language in languages:
        for model, document in words.build(config, language).items():
            path = config.word_path(language, model)
            text = words.to_json(document)
            current = path.read_text(encoding="utf-8") if path.is_file() else None
            state = "unchanged" if current == text else ("written" if args.apply else "to write")
            print(f"{path.relative_to(config.root)}: {document['count']} words, {state}")
            if args.apply and current != text:
                store.write_text(path, text)
    if not args.apply:
        print("dry run: nothing written. Add --apply to write.")
    return EXIT_OK


def run_lookup(args: argparse.Namespace) -> int:
    config = configuration.load()
    rows = store.all_rows(store.read_files(config))
    text = " ".join(args.query)
    found = query.lookup(config, rows, text, english=args.english)
    if args.json:
        print(json.dumps([markup.record(config, row) for row in found], ensure_ascii=False, indent=2))
    elif found:
        print("\n\n".join(query.describe(config, row) for row in found))
    if not found:
        kind = "English term" if args.english else "keyword"
        print(f"no row for {kind} '{text}'", file=sys.stderr)
        return EXIT_FOUND
    return EXIT_OK


def run_search(args: argparse.Namespace) -> int:
    config = configuration.load()
    if args.limit < 0:
        raise configuration.CiteError("--limit is 0 or a positive number")
    text = " ".join(args.query)
    identify, total, hits = query.search(config, text, source=args.source, limit=args.limit)
    if not total:
        print(f"'{text}' occurs in no verse of the searched translations", file=sys.stderr)
        return EXIT_FOUND
    print(f"'{text}': {total} verses in {identify}, showing {len(hits)}")
    width = max(len(name) for hit in hits for name, _ in hit.texts)
    for hit in hits:
        print(f"\n{hit.book_name} {hit.chapter}:{hit.verse}    [{hit.book}.{hit.chapter}.{hit.verse}]")
        for name, verse in hit.texts:
            print(f"  {name:<{width}}  {verse}")
    return EXIT_OK


def run_todo(args: argparse.Namespace) -> int:
    config = configuration.load()
    if args.limit < 0:
        raise configuration.CiteError("--limit is 0 or a positive number")
    rows = store.all_rows(store.read_files(config))
    result = query.coverage(config, rows)
    print(
        f"forms with a row: {result.forms_covered} of {result.forms} "
        f"({_percent(result.forms_covered, result.forms)})"
    )
    print(
        f"running text covered: {result.occurrences_covered} of {result.occurrences} words "
        f"({_percent(result.occurrences_covered, result.occurrences)})"
    )
    shown = result.missing if args.limit == 0 else result.missing[: args.limit]
    if shown:
        print(f"\nmost frequent words without a row ({len(shown)} of {len(result.missing)}):")
        width = max(len(entry["w"]) for entry in shown)
        for entry in shown:
            print(f"  {entry['w']:<{width}}  {entry['n']:>7}  {entry['r']}")
    return EXIT_OK


def _percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "0.0%"


def run_examples(args: argparse.Namespace) -> int:
    config = configuration.load()
    if args.limit < 0:
        raise configuration.CiteError("--limit is 0 or a positive number")
    selected = [data for data in store.read_files(config) if not args.file or data.key == args.file]
    if not selected:
        raise configuration.CiteError(
            f"'{args.file}' is not a listed file; listed: {', '.join(config.files)}"
        )
    rows = [row for data in selected for row in data.rows() if examples.measurable(config, row)]
    measured = [examples.measure(config, row) for row in rows]
    short = [entry for entry in measured if not entry.complete]
    terms = Counter(min(count, examples.PER_TERM) for entry in measured for _, count in entry.terms)
    total = sum(terms.values())
    print(f"rows expected to carry examples: {len(measured)}")
    print(f"rows with {examples.PER_TERM} examples for every term: {len(measured) - len(short)} "
          f"({_percent(len(measured) - len(short), len(measured))})")
    for count in range(examples.PER_TERM, -1, -1):
        label = f"{count} or more" if count == examples.PER_TERM else str(count)
        print(f"terms shown by {label} example{'' if count == 1 else 's'}: {terms[count]} ({_percent(terms[count], total)})")
    shown = short if args.limit == 0 else short[: args.limit]
    if shown:
        print(f"\nrows to complete ({len(shown)} of {len(short)}):")
        for entry in shown:
            row = entry.row
            if entry.terms:
                detail = ", ".join(f"{term} {count}/{examples.PER_TERM}" for term, count in entry.short)
            else:
                detail = f"{entry.examples}/{examples.PER_TERM} examples"
            if entry.untranslated:
                detail += f", {entry.untranslated} without translation"
            print(f"  {row.file}:{row.number}  {row.keyword}  {detail}")
    return EXIT_OK


def run_parse(args: argparse.Namespace) -> int:
    config = configuration.load()
    files = store.read_files(config)
    found = _findings(config, files)
    if found:
        raise configuration.CiteError(
            f"the data has {len(found)} findings; nothing is printed until "
            "'python3 -m assist cite check' passes"
        )
    selected = [data for data in files if not args.file or data.key == args.file]
    if not selected:
        raise configuration.CiteError(
            f"'{args.file}' is not a listed file; listed: {', '.join(config.files)}"
        )
    document = {
        "version": config.raw["version"],
        "language": config.raw["language"],
        "row": [markup.record(config, row) for data in selected for row in data.rows()],
    }
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return EXIT_OK
