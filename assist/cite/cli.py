"""Commands of ``python3 -m assist cite``."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, List

from assist.cite import check, config as configuration, credits, importer, index, markup, pull, query, render, tables
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

    parser = command("lookup", run_lookup, "Show the senses of a Zolai word or phrase; without one, of a term of any other language.")
    parser.add_argument("query", nargs="+", help="word or phrase")
    for code, entry in _languages().items():
        parser.add_argument(f"--{code}", action="append_const", const=code, dest="languages",
                            help=f"look up a term of {entry['name']} only")
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

    parser = command("next", run_next, "List the senses to work on next, the most frequent words first.")
    parser.add_argument("--kind", choices=NEXT_KINDS, action="append", help="one kind of gap only; may be repeated")
    parser.add_argument("--set", default="", help="one set only, e.g. core")
    parser.add_argument("--limit", type=int, default=20, help="senses to show, 0 for all (default: 20)")
    parser.add_argument("--output", default="next", help="file name in the inbox folder for --apply (default: next)")
    writing(parser, "the words of the listed senses as a markup file in the inbox folder")

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
    name = args.output or markup.collapse(args.word[0]).replace(" ", "-")
    return _write_pull(config, lexicon, [markup.collapse(word) for word in args.word], name, args.related, args.apply)


def _write_pull(config: Config, lexicon, spellings: List[str], name: str, related: bool, apply: bool) -> int:
    text = pull.text(lexicon, spellings, related=related)
    if not apply:
        print(text, end="")
        print(f"\n{DRY_RUN}", file=sys.stderr)
        return EXIT_OK
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


def _languages():
    """Gloss languages of the configuration, for the options of lookup."""
    return configuration.load().raw["language"]["gloss"]


def _rebuilding() -> None:
    print("the tables changed; building the index once ...", file=sys.stderr)


def _open() -> "index.Index":
    return index.open_index(configuration.load(), _rebuilding)


def run_lookup(args: argparse.Namespace) -> int:
    config = configuration.load()
    found = _open()
    limit = _limit(args, "examples")
    text = " ".join(args.query)
    names = config.raw["language"]["gloss"]
    blocks: List[str] = []
    senses: List[str] = []
    if not args.languages:
        words = found.words_for(text)
        if words:
            model = found.subset(words)
            blocks = [query.describe_word(model, word_id, limit) for word_id in words]
            senses = [s for w in words for s in model.senses_of.get(w, []) if model.active(s)]
            other = found.senses_for_term(text, config.languages)
            hint = [f"--{code}" for code in other]
            if hint and not args.json:
                blocks.append(f"also a term of {', '.join(names[c]['name'] for c in other)}: add {' or '.join(hint)}")
            return _print_lookup(args, model, senses, blocks)
    languages = args.languages or list(config.languages)
    by_language = found.senses_for_term(text, languages)
    if by_language:
        model = found.subset(sense_ids=[s for ids in by_language.values() for s in ids])
        for code, ids in by_language.items():
            blocks.append(f"{names[code]['name']} '{text}':")
            blocks.extend(query.describe(model, sense_id, limit) for sense_id in ids)
            senses.extend(ids)
        return _print_lookup(args, model, senses, blocks)
    links = found.linked(text, languages)
    if links:
        ids = [s for _, _, found_ids in links.values() for s in found_ids]
        model = found.subset(sense_ids=ids)
        for code, (status, note, found_ids) in links.items():
            remark = render.status_value(model, status, note)
            blocks.append(f"no sense has the {names[code]['name']} term '{text}'; closest senses" + (f" ({remark})" if remark else "") + ":")
            blocks.extend(query.describe(model, sense_id, limit) for sense_id in found_ids if model.active(sense_id))
            senses.extend(found_ids)
        return _print_lookup(args, model, senses, blocks)
    where = "a Zolai word or a term" if not args.languages else "a term of " + ", ".join(names[c]["name"] for c in languages)
    print(f"'{text}' is not {where} of the lexicon", file=sys.stderr)
    return EXIT_FOUND


def _print_lookup(args: argparse.Namespace, model, senses: List[str], blocks: List[str]) -> int:
    if args.json:
        print(json.dumps([query.record(model, sense_id) for sense_id in dict.fromkeys(senses)], ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(blocks))
    return EXIT_OK


def run_show(args: argparse.Namespace) -> int:
    found = _open()
    for target in args.target:
        kind = index.known(found, target)
        sense_id = target if kind == "sense" else index.sense_by_key(found, target) if not kind else None
        if kind == "word":
            model = found.subset([target])
            word = model.words[target]
            print(f"# word {word.id} '{word.spelling}', {model.config.word_status[word.status]}")
            print("\n".join(render.word_lines(model, target)))
        elif sense_id:
            model = found.subset(sense_ids=[sense_id])
            print(f"# sense {sense_id}, set {model.senses[sense_id].set}")
            print(render.sense_line(model, sense_id))
            for example, _ in model.examples_of(sense_id):
                print(render.example_line(model, example.id, sense_id))
        elif kind == "example":
            model = found.subset(example_ids=[target])
            for sense_id in model.usages.get(target, {}):
                print(render.example_line(model, target, sense_id))
        else:
            raise CiteError(f"'{target}' is not an id and not a sense key")
    return EXIT_OK


def run_find(args: argparse.Namespace) -> int:
    found = _open().find(" ".join(args.query), _limit(args))
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


NEXT_KINDS = ("low", "examples", "todo")
EXAMPLES_WANTED = 3


def run_next(args: argparse.Namespace) -> int:
    config = configuration.load()
    limit = _limit(args)
    if args.set and args.set not in config.sets:
        raise CiteError(f"'{args.set}' is not a set; known: {', '.join(config.sets)}")
    found = _open()
    low = config.status_code("sense", "low")
    wanted = args.kind or list(NEXT_KINDS)
    rows = []
    counts = {kind: 0 for kind in NEXT_KINDS}
    for sense_id, key, word_id, type_code, set_code, status, examples, frequency, terms in found.queue():
        if args.set and set_code != args.set:
            continue
        kinds = []
        if status == low:
            kinds.append("low")
        if config.has_meaning(type_code) and type_code != "name" and examples < EXAMPLES_WANTED:
            kinds.append("examples")
        if type_code == "todo":
            kinds.append("todo")
        for kind in kinds:
            counts[kind] += 1
        kinds = [kind for kind in kinds if kind in wanted]
        if kinds:
            rows.append((-frequency, key, sense_id, word_id, kinds, examples, frequency, terms))
    rows.sort()
    print("senses to work on" + (f" in the set {args.set}" if args.set else "") + ":")
    for kind, text in (
        ("low", "status low: the meaning rests on thin evidence"),
        ("examples", f"fewer than {EXAMPLES_WANTED} examples"),
        ("todo", "type todo: the meaning is not yet known"),
    ):
        print(f"  {kind:<9}{counts[kind]:>7}  {text}")
    shown = rows if limit == 0 else rows[:limit]
    if not shown:
        return EXIT_OK
    print(f"\nthe most frequent words first ({len(shown)} of {len(rows)}); frequency counts the Bible text and the examples:")
    width = max(len(row[1]) for row in shown)
    for _, key, sense_id, _, kinds, examples, frequency, terms in shown:
        print(f"  {key:<{width}}  {sense_id:<7}  {'/'.join(kinds):<13} examples {examples}  frequency {frequency:<6}  {terms[:40]}")
    if not args.apply:
        print(f"\nadd --apply to write their words to {args.output}{config.markup_extension} in the inbox folder", file=sys.stderr)
        return EXIT_OK
    words = list(dict.fromkeys(found.rows("select spelling from word where id = ?", [row[3]])[0][0] for row in shown))
    print()
    return _write_pull(config, check.load(config), words, args.output, False, True)


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
