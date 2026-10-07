"""Commands of ``python3 -m assist cite``."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, List

from assist.cite import check, config as configuration, credits, examples, importer, markup, pull, query, render, tables
from assist.cite.config import CiteError, Config

EXIT_OK = 0
EXIT_FOUND = 1
DRY_RUN = "dry run: nothing written. Add --apply to write."


def register(groups: argparse._SubParsersAction) -> None:
    group = groups.add_parser(
        "cite",
        help="Zolai-English dictionary data",
        description="Check, query and change the dictionary data in cite/.",
    )
    commands = group.add_subparsers(dest="command", metavar="command", required=True)

    def command(name: str, run: Callable, summary: str) -> argparse.ArgumentParser:
        parser = commands.add_parser(name, help=summary, description=summary)
        parser.set_defaults(run=run)
        return parser

    def writing(parser: argparse.ArgumentParser, what: str) -> None:
        parser.add_argument("--apply", action="store_true", help=f"write {what} (default: dry run)")

    parser = command("check", run_check, "Check every table against the rules of the format.")
    parser.add_argument("--summary", action="store_true", help="print counts per rule, not each finding")

    parser = command("import", run_import, "Import a file of typed markup into the tables.")
    parser.add_argument("file", help="markup file; a bare name is looked up in the inbox folder")
    writing(parser, "the tables and mark the rows of the file as done")

    parser = command("pull", run_pull, "Write the rows of words as a markup file for editing.")
    parser.add_argument("word", nargs="+", help="word as spelled; quote a word of several parts")
    parser.add_argument("--related", action="store_true", help="add the words one relation or link away")
    parser.add_argument("--output", default="", help="file name in the inbox folder (default: the first word)")
    writing(parser, "the file in the inbox folder")

    parser = command("lookup", run_lookup, "Show the senses of a Zolai word or of a term of another language.")
    parser.add_argument("query", nargs="+", help="word, or term with --term")
    parser.add_argument("--term", action="store_true", help="look up a term of a gloss language")
    parser.add_argument("--language", default="", help="gloss language of the term (default: the first one)")
    parser.add_argument("--examples", type=int, default=5, help="examples per sense, 0 for all (default: 5)")
    parser.add_argument("--json", action="store_true", help="print JSON, with every example")

    parser = command("show", run_show, "Print the rows behind ids or sense keys as markup.")
    parser.add_argument("target", nargs="+", help="word, sense or example id, or a sense key such as khut.1")

    parser = command("find", run_find, "Find a text in spellings, glosses, examples and translations.")
    parser.add_argument("query", nargs="+", help="text, compared without regard to case")
    parser.add_argument("--limit", type=int, default=20, help="lines per table, 0 for all (default: 20)")

    parser = command("set", run_set, "Move senses to another set.")
    parser.add_argument("set", help="code of the set list, e.g. core")
    parser.add_argument("key", nargs="+", help="sense key or sense id, e.g. khut.1")
    writing(parser, "the tables")

    parser = command("search", run_search, "Find the verses that contain a word, with parallel verses.")
    parser.add_argument("query", nargs="+", help="word or phrase")
    parser.add_argument("--source", default="", help="translation id to search (default: configured sources)")
    parser.add_argument("--limit", type=int, default=10, help="verses to show, 0 for all (default: 10)")

    parser = command("todo", run_todo, "List the most frequent words of the Bible text that the lexicon lacks.")
    parser.add_argument("--limit", type=int, default=50, help="words to show, 0 for all (default: 50)")

    parser = command("examples", run_examples, "Report the senses whose examples do not yet show every term.")
    parser.add_argument("--set", default="", help="one set only, e.g. core")
    parser.add_argument("--limit", type=int, default=50, help="senses to show, 0 for all (default: 50)")

    parser = command("credits", run_credits, "Generate CREDITS.md from the source list.")
    writing(parser, "the file")


def _limit(args: argparse.Namespace, name: str = "limit") -> int:
    value = getattr(args, name)
    if value < 0:
        raise CiteError(f"--{name} is 0 or a positive number")
    return value


def _relative(config: Config, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(config.root))
    except ValueError:
        return str(path)


def _report(config: Config, found: List[check.Finding], summary: bool) -> None:
    if summary:
        for rule, count in sorted(Counter(finding.rule for finding in found).items()):
            print(f"{rule} {config.rules[rule]['name']}: {count}")
    else:
        for finding in found:
            print(finding.describe(config))


def run_check(args: argparse.Namespace) -> int:
    config = configuration.load()
    problems: List[str] = []
    data = tables.read_all(config, problems)
    found = check.run(config, data, problems)
    _report(config, found, args.summary)
    rows = sum(len(rows) for rows in data.values())
    print(f"{rows} rows in {len(data)} tables: {len(found)} findings")
    return EXIT_FOUND if found else EXIT_OK


def _store(config: Config, lexicon, apply: bool) -> None:
    """Check the changed model in full, then report and write the files that differ."""
    data = lexicon.tables()
    found = check.run(config, data)
    if found:
        known = set(check.run(config, tables.read_all(config)))
        new = [finding for finding in found if finding not in known]
        if new:
            _report(config, new, summary=False)
            raise CiteError(f"the change breaks {len(new)} rules; nothing is written")
        print(f"note: the tables had {len(found)} findings before the change; see: python3 -m assist cite check")
    write, remove = tables.changes(config, data)
    for path in write:
        print(f"  {'written' if apply else 'to write'}: {_relative(config, path)}")
    for path in remove:
        print(f"  {'removed' if apply else 'to remove'}: {_relative(config, path)}")
    if apply:
        tables.write_all(config, data)


def _markup_file(config: Config, name: str) -> Path:
    """A bare file name is a file of the inbox folder; any other path is used as given."""
    path = Path(name)
    if "/" not in name and "\\" not in name:
        return config.inbox / (name if path.suffix else f"{name}{config.markup_extension}")
    return path


def run_import(args: argparse.Namespace) -> int:
    config = configuration.load()
    path = _markup_file(config, args.file)
    if not path.is_file():
        raise CiteError(f"{_relative(config, path)}: the file does not exist")
    try:
        lines = path.read_text(encoding="utf-8").split("\n")
    except UnicodeDecodeError as error:
        raise CiteError(f"{_relative(config, path)}: not UTF-8: {error}") from error
    lexicon = check.load(config)
    result = importer.plan(config, lexicon, lines)
    if result.errors:
        for error in result.errors:
            print(f"{_relative(config, path)}: {error}")
        print("nothing is written")
        return EXIT_FOUND
    for action in result.actions:
        print(f"line {action.row.number}: {action.verb} {action.subject}")
    for word in result.words:
        print(f"new word: {word}")
    counts = Counter(action.verb for action in result.actions)
    print(", ".join(f"{count} {verb}" for verb, count in counts.items()))
    _store(config, lexicon, args.apply)
    if args.apply:
        tables.write_text(path, "\n".join(importer.mark_done(lines, result)))
        print(f"  marked as done: {_relative(config, path)}")
    else:
        print("the ids shown are the ones the import would give now")
        print(DRY_RUN)
    return EXIT_OK


def run_pull(args: argparse.Namespace) -> int:
    config = configuration.load()
    lexicon = check.load(config)
    text = pull.text(lexicon, [markup.collapse(word) for word in args.word], related=args.related)
    if not args.apply:
        print(text, end="")
        print(f"\n{DRY_RUN}", file=sys.stderr)
        return EXIT_OK
    name = args.output or markup.collapse(args.word[0]).replace(" ", "-")
    if "/" in name or "\\" in name:
        raise CiteError("--output is a file name, without a folder")
    path = _markup_file(config, name)
    if path.is_file() and any(markup.is_row(line) for line in path.read_text(encoding="utf-8").split("\n")):
        raise CiteError(
            f"{_relative(config, path)} holds rows that are not imported; import or delete the file, "
            f"or name another file with --output"
        )
    tables.write_text(path, text)
    print(f"written: {_relative(config, path)}")
    print(f"then: python3 -m assist cite import {path.name}")
    return EXIT_OK


def run_lookup(args: argparse.Namespace) -> int:
    config = configuration.load()
    lexicon = check.load(config)
    limit = _limit(args, "examples")
    text = " ".join(args.query)
    note = ""
    if not args.term:
        found = [
            sense_id for word_id in query.words_for(lexicon, text)
            for sense_id in lexicon.senses_of.get(word_id, []) if lexicon.active(sense_id)
        ]
        blocks = [query.describe_word(lexicon, word_id, limit) for word_id in query.words_for(lexicon, text)]
    else:
        language = args.language or config.languages[0]
        if language not in config.languages:
            raise CiteError(f"'{language}' is not a gloss language; known: {', '.join(config.languages)}")
        found = query.senses_for_term(lexicon, text, language)
        if not found:
            link = query.linked(lexicon, text, language)
            if link:
                remark, found = link
                note = f"no sense has the term '{text}'; closest senses" + (f" ({remark})" if remark else "") + ":\n"
        blocks = [query.describe(lexicon, sense_id, limit) for sense_id in found]
    if args.json:
        print(json.dumps([query.record(lexicon, sense_id) for sense_id in found], ensure_ascii=False, indent=2))
        return EXIT_OK if found else EXIT_FOUND
    if not blocks:
        print(f"nothing for {'the term' if args.term else 'the word'} '{text}'", file=sys.stderr)
        return EXIT_FOUND
    print(note + "\n\n".join(blocks))
    return EXIT_OK


def run_show(args: argparse.Namespace) -> int:
    config = configuration.load()
    lexicon = check.load(config)
    for target in args.target:
        if target in lexicon.words:
            word = lexicon.words[target]
            print(f"# word {word.id} '{word.spelling}', {config.word_status[word.status]}")
            print("\n".join(render.word_lines(lexicon, target)))
            continue
        sense_id = target if target in lexicon.senses else lexicon.sense_by_key(target)
        if sense_id:
            print(f"# sense {sense_id}, set {lexicon.senses[sense_id].set}")
            print(render.sense_line(lexicon, sense_id))
            for example, _ in lexicon.examples_of(sense_id):
                print(render.example_line(lexicon, example.id, sense_id))
        elif target in lexicon.examples:
            for sense_id in lexicon.usages.get(target, {}):
                print(render.example_line(lexicon, target, sense_id))
        else:
            raise CiteError(f"'{target}' is not an id and not a sense key")
    return EXIT_OK


def run_find(args: argparse.Namespace) -> int:
    config = configuration.load()
    found = query.find(check.load(config), " ".join(args.query), _limit(args))
    for kind, lines in found.items():
        if lines:
            print(f"{kind}:")
            for line in lines:
                print(f"  {line}")
    return EXIT_OK if any(found.values()) else EXIT_FOUND


def run_set(args: argparse.Namespace) -> int:
    config = configuration.load()
    if args.set not in config.sets:
        raise CiteError(f"'{args.set}' is not a set; known: {', '.join(config.sets)}")
    lexicon = check.load(config)
    for key in args.key:
        sense_id = key if key in lexicon.senses else lexicon.sense_by_key(key)
        if sense_id is None:
            raise CiteError(f"'{key}' is not a sense")
        sense = lexicon.senses[sense_id]
        print(f"{lexicon.key(sense_id)} ({sense_id}): {sense.set} to {args.set}")
        sense.set = args.set
    _store(config, lexicon, args.apply)
    if not args.apply:
        print(DRY_RUN)
    return EXIT_OK


def run_search(args: argparse.Namespace) -> int:
    config = configuration.load()
    text = " ".join(args.query)
    identify, total, hits = query.search(config, text, source=args.source, limit=_limit(args))
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


def _percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "0.0%"


def run_todo(args: argparse.Namespace) -> int:
    config = configuration.load()
    limit = _limit(args)
    result = query.coverage(check.load(config))
    print(
        f"forms that are a word of the lexicon: {result.forms_covered} of {result.forms} "
        f"({_percent(result.forms_covered, result.forms)})"
    )
    print(
        f"running text covered: {result.occurrences_covered} of {result.occurrences} words "
        f"({_percent(result.occurrences_covered, result.occurrences)})"
    )
    shown = result.missing if limit == 0 else result.missing[:limit]
    if shown:
        print(f"\nmost frequent words that the lexicon lacks ({len(shown)} of {len(result.missing)}):")
        width = max(len(form) for form, _, _ in shown)
        for form, number, reference in shown:
            print(f"  {form:<{width}}  {number:>7}  {reference}")
    return EXIT_OK


def run_examples(args: argparse.Namespace) -> int:
    config = configuration.load()
    limit = _limit(args)
    if args.set and args.set not in config.sets:
        raise CiteError(f"'{args.set}' is not a set; known: {', '.join(config.sets)}")
    lexicon = check.load(config)
    measured = [
        examples.measure(lexicon, sense_id) for sense_id, sense in lexicon.senses.items()
        if (not args.set or sense.set == args.set) and examples.measurable(lexicon, sense_id)
    ]
    short = [entry for entry in measured if not entry.complete]
    terms = Counter(min(count, examples.PER_TERM) for entry in measured for _, count in entry.terms)
    total = sum(terms.values())
    print(f"senses expected to carry examples: {len(measured)}")
    print(f"senses with {examples.PER_TERM} examples for every term: {len(measured) - len(short)} "
          f"({_percent(len(measured) - len(short), len(measured))})")
    for count in range(examples.PER_TERM, -1, -1):
        label = f"{count} or more" if count == examples.PER_TERM else str(count)
        print(f"terms shown by {label} example{'' if count == 1 else 's'}: {terms[count]} ({_percent(terms[count], total)})")
    shown = short if limit == 0 else short[:limit]
    if shown:
        print(f"\nsenses to complete ({len(shown)} of {len(short)}):")
        for entry in shown:
            if entry.terms:
                detail = ", ".join(f"{term} {count}/{examples.PER_TERM}" for term, count in entry.short)
            else:
                detail = f"{entry.examples}/{examples.PER_TERM} examples"
            print(f"  {entry.sense}  {lexicon.key(entry.sense)}  {detail}")
    return EXIT_OK


def run_credits(args: argparse.Namespace) -> int:
    config = configuration.load()
    path = credits.path(config)
    stale = credits.stale(config)
    print(f"{_relative(config, path)}: {('written' if args.apply else 'to write') if stale else 'unchanged'}")
    if args.apply and stale:
        tables.write_text(path, credits.build(config))
    if not args.apply:
        print(DRY_RUN)
    return EXIT_OK
