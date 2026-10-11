"""Commands of ``python3 -m assist cite``."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, List

from assist.cite import (
    analyse, check, config as configuration, credits, importer, index, markup, pull, query, render, tables, work,
)
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

    def filters(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--set", default="", help="one set only, e.g. core")
        parser.add_argument("--type", default="", help="one type only, e.g. ppm")
        parser.add_argument("--status", default="", help="one sense status only, e.g. low")
        parser.add_argument("--field", default="", help="one field only, e.g. everyday")
        parser.add_argument("--source", default="", help="senses attested in one source, e.g. zd, or bible")
        parser.add_argument("--word", default="", help="the senses of one word, as spelled")
        parser.add_argument("--min-frequency", type=int, default=0, help="words counted at least this often")

    parser = command("next", run_next, "List the senses to work on next.")
    parser.add_argument("--kind", choices=tuple(work.GAPS), action="append", help="one kind of gap only; may be repeated")
    filters(parser)
    parser.add_argument("--sort", choices=work.SORTS, default="frequency", help="order of the list (default: frequency)")
    parser.add_argument("--limit", type=int, default=20, help="senses to show, 0 for all (default: 20)")
    parser.add_argument("--offset", type=int, default=0, help="senses to skip, for the next page (default: 0)")
    parser.add_argument("--count", action="store_true", help="print only the counts of each kind of gap")
    parser.add_argument("--output", default="next", help="file name in the inbox folder for --apply (default: next)")
    writing(parser, "the words of the listed senses as a markup file in the inbox folder")

    parser = command("stats", run_stats, "Count words, senses, examples and languages.")
    filters(parser)
    parser.add_argument("--by", default="", help=f"one dimension, or two separated by a comma, of: {', '.join(work.DIMENSIONS)}")
    parser.add_argument("--markdown", action="store_true", help=f"the counts as {work.STATS}; --apply writes the file")
    parser.add_argument("--apply", action="store_true", help="with --markdown, write the file (default: print it)")

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
    for path in tables.changes(config, data):
        print(f"  {'written' if apply else 'to write'}: {_relative(config, path)}")
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
        readings = analyse.analyse_with_index(found, text) if " " not in text.strip() else []
        if readings:
            other = found.senses_for_term(text, config.languages)
            if args.json:
                print(json.dumps({"analysis": [analyse.record(r) for r in readings]}, ensure_ascii=False, indent=2))
                return EXIT_OK
            print(f"'{text}' is not in the lexicon; read as parts that are (an analysis, not a stored entry):")
            print("\n".join(analyse.describe(reading) for reading in readings))
            if other:
                hint = " or ".join(f"--{code}" for code in other)
                print(f"also a term of {', '.join(names[c]['name'] for c in other)}: add {hint}")
            return EXIT_OK
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


def _filter(args: argparse.Namespace, config: Config) -> "work.Filter":
    chosen = work.Filter(
        args.set, args.type, args.status, args.field, args.source, args.word, args.min_frequency
    )
    chosen.validate(config)
    if args.min_frequency < 0:
        raise CiteError("--min-frequency is zero or more")
    return chosen


def run_next(args: argparse.Namespace) -> int:
    config = configuration.load()
    limit = _limit(args)
    if args.offset < 0:
        raise CiteError("--offset is zero or more")
    chosen = _filter(args, config)
    found = _open()
    facts = [fact for fact in work.facts(found, config) if chosen.holds(fact, config)]
    if args.word and not facts:
        raise CiteError(f"'{args.word}' has no active sense; check the spelling with: python3 -m assist cite lookup {args.word}")
    wanted = args.kind or list(work.GAPS)
    rows, counts = work.queue(facts, config, wanted, args.sort)
    scope = chosen.describe()
    print("senses to work on" + (f" ({scope})" if scope else "") + f", of {len(facts):,}:")
    for kind, text in work.GAPS.items():
        print(f"  {kind:<9}{counts[kind]:>7,}  {text}")
    shown = rows[args.offset:] if limit == 0 else rows[args.offset:args.offset + limit]
    if args.count or not shown:
        return EXIT_OK
    order = {"frequency": "the most frequent words first", "key": "by keyword", "random": "in random order"}[args.sort]
    print(f"\n{order}, {args.offset + 1} to {args.offset + len(shown)} of {len(rows)}; frequency counts the Bible text and the examples:")
    width = max(len(fact.key) for fact, _ in shown)
    for fact, kinds in shown:
        print(
            f"  {fact.key:<{width}}  {fact.id:<7}  {'/'.join(kinds):<22} examples {fact.examples}  "
            f"frequency {fact.frequency:<6}  {fact.terms[:40]}"
        )
    if len(rows) > args.offset + len(shown):
        print(f"\nnext page: --offset {args.offset + len(shown)}", file=sys.stderr)
    if not args.apply:
        print(f"add --apply to write their words to {args.output}{config.markup_extension} in the inbox folder", file=sys.stderr)
        return EXIT_OK
    words = list(dict.fromkeys(fact.word for fact, _ in shown))
    print()
    return _write_pull(config, check.load(config), words, args.output, False, True)


def _stats_lines(config: Config, found: "index.Index", facts: List["work.Fact"], by: List[str], scope: str, markdown: bool) -> List[str]:
    """The counts as lines of text, or of Markdown for the stats file."""
    lines: List[str] = []

    def heading(text: str) -> None:
        lines.extend(["", f"## {text}", ""] if markdown else ["", f"{text}:"])

    def table(header: List[str], body: List[List[str]]) -> None:
        if markdown:
            lines.append("| " + " | ".join(header) + " |")
            lines.append("| " + " | ".join(["---"] + ["---:"] * (len(header) - 1)) + " |")
            lines.extend("| " + " | ".join(row) + " |" for row in body)
            return
        widths = [max(len(row[i]) for row in [header] + body) for i in range(len(header))]
        numeric = [i > 0 and all(row[i].replace(",", "").isdigit() for row in body) for i in range(len(header))]
        for row in [header] + body:
            cells = [v.rjust(w) if numeric[i] else v.ljust(w) for i, (v, w) in enumerate(zip(row, widths))]
            lines.append(("  " + "  ".join(cells)).rstrip())

    number = "{:,}".format
    if markdown:
        lines += ["# Statistics", "", f"Counts of the cite data, generated by `python3 -m assist cite stats --markdown --apply`. Refreshed by hand, so it can lag behind the tables."]
    else:
        lines.append(f"senses{f' ({scope})' if scope else ''}: {number(len(facts))}")
    if by:
        if len(by) == 1:
            heading(f"Senses by {by[0]}")
            table([by[0], "senses"], [[_name(config, by[0], code), number(n)] for code, n in work.counts(facts, by[0]).items()])
        else:
            grid = work.crossed(facts, by[0], by[1])
            columns = list(work.counts(facts, by[1]))
            heading(f"Senses by {by[0]} and {by[1]}")
            table(
                [f"{by[0]} \\ {by[1]}"] + [_name(config, by[1], code) for code in columns] + ["all"],
                [
                    [_name(config, by[0], code)] + [number(grid[code].get(c, 0)) for c in columns]
                    + [number(n)]
                    for code, n in work.counts(facts, by[0]).items()
                ],
            )
        return lines
    facts_all = facts
    rest = work.overview(found, config, facts_all)
    if markdown:
        heading("Totals")
        table(["", "count"], [["words", number(sum(rest["words"].values()))], ["senses", number(len(facts))], ["examples", number(rest["examples"])]])
        heading("Words by status")
    else:
        lines.append(f"words: {number(sum(rest['words'].values()))}   examples: {number(rest['examples'])}")
        heading("words by status")
    table(["status", "words"], [[name, number(n)] for name, n in rest["words"].items()])
    for dimension in ("status", "type", "set", "field", "source"):
        heading(f"Senses by {dimension}" if markdown else f"senses by {dimension}")
        table([dimension, "senses"], [[_name(config, dimension, code), number(n)] for code, n in work.counts(facts, dimension).items()])
    heading("Examples by source" if markdown else "examples by source")
    table(["source", "examples"], [[_name(config, "source", code), number(n)] for code, n in rest["examples by source"].items()])
    heading("Languages" if markdown else "languages")
    table(
        ["language", "terms", "definitions", "translations", "links"],
        [
            [f"{config.raw['language']['gloss'][code]['name']} ({code})"] + [number(v) for v in values.values()]
            for code, values in rest["languages"].items()
        ],
    )
    heading("Work to do" if markdown else "work to do")
    _, gaps = work.queue(facts, config, list(work.GAPS), "key")
    table(["gap", "senses", "meaning"], [[kind, number(gaps[kind]), text] for kind, text in work.GAPS.items()])
    return lines


def _name(config: Config, dimension: str, code: str) -> str:
    name = work.label(config, dimension, code)
    return code if name == code else f"{name} ({code})"


def run_stats(args: argparse.Namespace) -> int:
    config = configuration.load()
    chosen = _filter(args, config)
    by = [part.strip() for part in args.by.split(",")] if args.by else []
    if len(by) > 2 or any(part not in work.DIMENSIONS for part in by):
        raise CiteError(f"--by takes one dimension, or two separated by a comma, of: {', '.join(work.DIMENSIONS)}")
    if args.apply and not args.markdown:
        raise CiteError("--apply writes the Markdown file; add --markdown")
    if args.markdown and (by or chosen.describe()):
        raise CiteError(f"--markdown writes {work.STATS} for the whole data; leave out --by and the filters")
    found = _open()
    facts = [fact for fact in work.facts(found, config) if chosen.holds(fact, config)]
    lines = _stats_lines(config, found, facts, by, chosen.describe(), args.markdown)
    text = "\n".join(lines).strip("\n") + "\n"
    if not args.markdown or not args.apply:
        print(text, end="")
        if args.markdown:
            print(f"\n{DRY_RUN}", file=sys.stderr)
        return EXIT_OK
    target = config.directory / work.STATS
    unchanged = target.is_file() and target.read_text(encoding="utf-8") == text
    if not unchanged:
        tables.write_text(target, text)
    print(f"{_relative(config, target)}: {'unchanged' if unchanged else 'written'}")
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
