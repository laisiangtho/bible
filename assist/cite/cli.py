"""Commands of ``python3 -m assist cite``."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections import Counter
from typing import Callable, List

from assist.cite import config as configuration
from assist.cite import convert, examples, index, markup, query, rules, store, upgrade, words

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

    parser = command("convert", run_convert, "Bring rows written for an earlier markup version to the current one.")
    _writing(parser)

    parser = command("index", run_index, "Generate the keyword index and the English term index.")
    parser.add_argument("--apply", action="store_true", help="write the files (default: dry run)")

    parser = command("move", run_move, "Move senses, with their examples, to another data file.")
    parser.add_argument("target", help="listed file that receives the senses, e.g. core")
    parser.add_argument("key", nargs="*", help="sense key, e.g. khut.1")
    parser.add_argument("--list", default="", help="text file with one sense key per line")
    parser.add_argument("--apply", action="store_true", help="write the files (default: dry run)")

    parser = command("rename", run_rename, "Rename a keyword in every file that names it.")
    parser.add_argument("old", help="keyword as written now")
    parser.add_argument("new", help="keyword as it is to be written")
    parser.add_argument("--apply", action="store_true", help="write the files (default: dry run)")

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


def _findings(config, data: store.Data) -> List[rules.Finding]:
    found = [finding for file in data.every_file() for finding in file.findings]
    found.extend(rules.check_rows(config, data.rows(), data.example_rows(), data.translation_rows()))
    if all(file.readable for file in data.files):
        found.extend(rules.Finding(name, 0, "F06", "run 'python3 -m assist cite index --apply'")
                     for name in index.stale(config, data.rows()))
    return found


def _report(config, found: List[rules.Finding], rows: int, files: int) -> None:
    errors = {(f.file, f.number) for f in found if f.is_error}
    form_only = {(f.file, f.number) for f in found} - errors
    print(
        f"{rows} rows in {files} files: {len(errors)} with errors, "
        f"{len(form_only)} with form issues only"
    )


def _listed(config, key: str) -> None:
    if key not in config.files:
        raise configuration.CiteError(
            f"'{key}' is not a listed file; listed: {', '.join(config.files)}"
        )


def run_check(args: argparse.Namespace) -> int:
    config = configuration.load()
    data = store.load(config)
    found = _findings(config, data)
    files = data.every_file()
    if args.file:
        _listed(config, args.file)
        # Keywords and sense keys resolve across all files, so everything is checked
        # and the data file with its example file is reported.
        files = [file for file in data.files + data.examples if file.key == args.file]
        names = {file.name for file in files}
        found = [finding for finding in found if finding.file in names]
    rows = len(store.all_rows(files))
    if args.summary:
        for rule, number in sorted(Counter(finding.rule for finding in found).items()):
            print(f"{rule} {config.rules[rule]['name']}: {number}")
    else:
        order = {file.name: position for position, file in enumerate(files)}
        for finding in sorted(found, key=lambda f: (order.get(f.file, -1), f.number, f.rule)):
            print(finding.describe(config))
    _report(config, found, rows, len(files))
    return EXIT_FOUND if found else EXIT_OK


def _write(args: argparse.Namespace, config, changes, verb: str) -> int:
    """Report the new lines of each file and write them; dry run unless --apply."""
    total = 0
    for file, lines in changes.items():
        old = file.lines
        if len(lines) == len(old):
            changed = sum(1 for before, after in zip(old, lines) if before != after)
        else:
            before, after = Counter(old), Counter(lines)
            changed = sum(((after - before) + (before - after)).values())
        total += changed
        if getattr(args, "diff", False) and changed:
            sys.stdout.writelines(
                difflib.unified_diff(
                    [line + "\n" for line in old], [line + "\n" for line in lines],
                    file.name, file.name, n=0,
                )
            )
        print(f"{file.name}: {changed} rows {'changed' if args.apply else 'to change'}")
        if args.apply:
            store.write_text(file.path, store.to_text(lines))
    if args.apply:
        print(f"{verb}: {total} rows written. Next: python3 -m assist cite check --summary")
    else:
        print(f"dry run: {total} rows would change. Add --apply to write.")
    return EXIT_OK


def _readable(data: store.Data) -> None:
    unreadable = [file.name for file in data.every_file() if not file.readable]
    if unreadable:
        raise configuration.CiteError(f"cannot read: {', '.join(unreadable)}; run the check")


def _format_line(config, kind: str, line: str) -> str:
    if not markup.is_row(line):
        return line.rstrip() if line.startswith(markup.COMMENT) else ""
    row = markup.parse(line)
    if kind == "example":
        return markup.canonical_example(row) or line
    if kind == "translation":
        return markup.canonical_translation(config, row) or line
    return markup.canonical(config, row) or line


def run_format(args: argparse.Namespace) -> int:
    config = configuration.load()
    data = store.load(config)
    _readable(data)
    changes = {}
    for file in data.every_file():
        lines = [_format_line(config, file.kind, line) for line in file.lines]
        while lines and not lines[-1]:
            lines.pop()
        if lines != file.lines or store.to_text(lines) != file.path.read_text(encoding="utf-8"):
            changes[file] = lines
    return _write(args, config, changes, "format")


def run_convert(args: argparse.Namespace) -> int:
    config = configuration.load()
    data = store.load(config)
    _readable(data)
    for file in data.files:
        file.lines = [convert.convert_line(config, line) for line in file.lines]
    changes = upgrade.upgrade(config, data, upgrade.bible_locator(config))
    original = {file.name: file for file in store.load(config).every_file()}
    for file in data.files:
        before = original[file.name].lines
        if file not in changes and file.lines != before:
            changes[file] = file.lines
        file.lines = before
    return _write(args, config, changes, "convert")


def run_index(args: argparse.Namespace) -> int:
    config = configuration.load()
    data = store.load(config)
    _readable(data)
    for code, text in index.build(config, data.rows()).items():
        path = config.index_path(code)
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        state = "unchanged" if current == text else ("written" if args.apply else "to write")
        print(f"{path.relative_to(config.root)}: {text.count(chr(10)) - 2} lines, {state}")
        if args.apply and current != text:
            store.write_text(path, text)
    if not args.apply:
        print("dry run: nothing written. Add --apply to write.")
    return EXIT_OK


def run_move(args: argparse.Namespace) -> int:
    config = configuration.load()
    data = store.load(config)
    _readable(data)
    keys = list(args.key)
    if args.list:
        try:
            with open(args.list, encoding="utf-8") as stream:
                keys.extend(line.strip() for line in stream if line.strip() and not line.startswith("#"))
        except OSError as error:
            raise configuration.CiteError(f"cannot read the list: {error}") from error
    if not keys:
        raise configuration.CiteError("no sense key is given")
    result = _write(args, config, upgrade.move(config, data, keys, args.target), "move")
    if args.apply:
        print("Then: python3 -m assist cite index --apply")
    return result


def run_rename(args: argparse.Namespace) -> int:
    config = configuration.load()
    data = store.load(config)
    _readable(data)
    changes = upgrade.rename(config, data, args.old, args.new)
    result = _write(args, config, changes, "rename")
    if args.apply:
        print("Then: python3 -m assist cite index --apply")
    return result


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
    data = store.load(config)
    by_key = data.by_key()
    text = " ".join(args.query)
    found = query.lookup(config, data.rows(), text, english=args.english)

    def shown(row):
        return by_key.get(markup.row_key(row), [])

    if args.json:
        print(json.dumps(
            [markup.record(config, row, shown(row)) for row in found], ensure_ascii=False, indent=2
        ))
    elif found:
        print("\n\n".join(query.describe(config, row, shown(row)) for row in found))
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
    if args.file:
        _listed(config, args.file)
    data = store.load(config)
    by_key = data.by_key()
    rows = [
        row for file in data.files if not args.file or file.key == args.file
        for row in file.rows() if examples.measurable(config, row)
    ]
    measured = [examples.measure(config, row, by_key.get(markup.row_key(row), [])) for row in rows]
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
    data = store.load(config)
    found = _findings(config, data)
    if found:
        raise configuration.CiteError(
            f"the data has {len(found)} findings; nothing is printed until "
            "'python3 -m assist cite check' passes"
        )
    if args.file:
        _listed(config, args.file)
    selected = [file for file in data.files if not args.file or file.key == args.file]
    by_key = data.by_key()
    document = {
        "version": config.raw["version"],
        "language": config.raw["language"],
        "row": [
            markup.record(config, row, by_key.get(markup.row_key(row), []))
            for file in selected for row in file.rows()
        ],
    }
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return EXIT_OK
