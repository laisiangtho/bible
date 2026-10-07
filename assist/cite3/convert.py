"""Conversion of the format 2 files into the tables of format 3."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from assist.cite import markup, store, upgrade
from assist.cite.config import CiteError, Config
from assist.cite.store import Data
from assist.cite3 import legacy, schema

Tables = Dict[str, List[Tuple[str, ...]]]

RELATION_ATTRIBUTES = ("s", "a", "b", "j", "v")
SET_OF_FILE = {"core": "core", "draft": "bible", "digit-number": "bible"}
WORD_STANDARD = "1"
WORD_VARIANT = "2"

# Sections of the notes files: file name, kind, columns after the subject, heading.
NOTE_FILES = ("ctd-core-notes.txt", "ctd-draft-notes.txt")
NOTE_KINDS = ("concept", "english", "article", "book", "editor")
NOTE_WITH_SOURCE = {"book"}
NOTE_SEPARATOR = " | "


def set_of(file_key: str) -> str:
    if file_key in SET_OF_FILE:
        return SET_OF_FILE[file_key]
    if file_key.startswith("noun-"):
        return "name"
    raise CiteError(f"no set is defined for the data file '{file_key}'")


def read_notes(directory: Path) -> List["Note"]:
    """Notes as (kind, heading, subject, source, text), in file order."""
    notes: List[Note] = []
    kinds = iter(NOTE_KINDS)
    for name in NOTE_FILES:
        path = directory / name
        if not path.is_file():
            raise CiteError(f"{path}: the notes file is missing")
        kind = heading = ""
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if not line:
                continue
            if line.startswith(markup.COMMENT):
                try:
                    kind = next(kinds)
                except StopIteration:
                    raise CiteError(f"{path}:{number}: more sections than the kinds {NOTE_KINDS}") from None
                heading = line
                continue
            if not kind:
                raise CiteError(f"{path}:{number}: a note before the first heading")
            parts = line.split(NOTE_SEPARATOR, 2 if kind in NOTE_WITH_SOURCE else 1)
            subject = parts[0]
            source = parts[1] if kind in NOTE_WITH_SOURCE and len(parts) == 3 else ""
            text = parts[-1] if len(parts) > 1 else ""
            notes.append((kind, heading, subject, source, text))
    return notes


Note = Tuple[str, str, str, str, str]


def convert(config: Config, data: Data, notes: Optional[List[Note]] = None) -> Tables:
    """Tables of everything in the format 2 files.

    ``notes`` are read from the notes files of the cite directory unless given.

    Ids are given in the order of the keywords, senses within a keyword by
    their number, examples in the order of their senses.
    """
    tables: Tables = {name: [] for name in schema.TABLES}
    lexicon = [(file.key, row) for file in data.files for row in file.rows()]

    # Words: every keyword, then every variant spelling named in v.
    spellings = sorted({row.keyword for _, row in lexicon}, key=upgrade.sort_key)
    word_id: Dict[str, str] = {}
    for spelling in spellings:
        word_id[spelling] = schema.make_id("w", len(word_id) + 1)
        tables["word"].append((word_id[spelling], spelling, WORD_STANDARD))
    for _, row in lexicon:
        if row.described and "v" in row.values():
            for item in markup.split_items(config.attributes["v"], row.values()["v"]):
                if item not in word_id:
                    word_id[item] = schema.make_id("w", len(word_id) + 1)
                    tables["word"].append((word_id[item], item, WORD_VARIANT))

    def word_of(spelling: str, where: str) -> str:
        if spelling not in word_id:
            raise CiteError(f"{where}: '{spelling}' is not a keyword")
        return word_id[spelling]

    # Senses, glosses and relations.
    def sense_order(entry: Tuple[str, markup.Row]) -> Tuple:
        row = entry[1]
        number = row.values().get("i", "") if row.described else ""
        return upgrade.sort_key(row.keyword), 0 if number.isdigit() else 1, int(number) if number.isdigit() else 0

    sense_id: Dict[str, str] = {}
    count = 0
    for file_key, row in sorted(lexicon, key=sense_order):
        if not row.described:
            continue
        where = f"{row.file}:{row.number}"
        values = row.values()
        if values.get("t") == "see":
            targets = markup.XREF.findall(row.text)
            if len(row.attributes) != 1 or len(targets) != 1 or markup.collapse(row.text) != f"<{targets[0]}>":
                raise CiteError(f"{where}: a row of type see holds the type and one link only")
            tables["relation"].append((word_id[row.keyword], "see", word_of(targets[0], where), "1"))
            continue
        count += 1
        sid = schema.make_id("s", count)
        number = values.get("i", "")
        if number:
            key = markup.sense_key(row.keyword, number)
            if key in sense_id:
                raise CiteError(f"{where}: the sense {key} occurs twice")
            sense_id[key] = sid
        elif values.get("t") != "todo":
            raise CiteError(f"{where}: a row with a meaning has no sense number")
        status, note = legacy.read_q(values.get("q", ""))
        tables["sense"].append((
            sid, word_id[row.keyword], number, values.get("t", ""), values.get("c", ""), values.get("f", ""),
            set_of(file_key), str(status), values.get("o", ""), values.get("r", ""), note,
        ))
        terms, definition, text = values.get("w", ""), values.get("d", ""), markup.collapse(row.text)
        if terms or definition or text:
            tables["gloss/eng"].append((sid, terms, definition, text))
        for kind in RELATION_ATTRIBUTES:
            if kind in values:
                for order, item in enumerate(markup.split_items(config.attributes[kind], values[kind]), 1):
                    tables["relation"].append((sid, kind, word_of(item, where), str(order)))

    # Examples: one row per sentence, one usage per sense that it shows.
    example_id: Dict[Tuple[str, str, str], str] = {}
    usages: Dict[Tuple[str, str], Tuple[str, str]] = {}
    for row in data.example_rows():
        if not row.described:
            continue
        where = f"{row.file}:{row.number}"
        item = markup.example(row)
        if item.key not in sense_id:
            raise CiteError(f"{where}: the sense {item.key} has no row")
        keyword = markup.split_key(item.key)[0]
        text, starts, length = legacy.fill(item.zolai, keyword)
        if legacy.blank(text, keyword, starts, length) != item.zolai:
            raise CiteError(f"{where}: the example cannot be rebuilt from word positions")
        source = markup.LIST_SEPARATOR.join(item.references)
        identity = (text, source, item.english if item.translated else "\x00")
        if identity not in example_id:
            example_id[identity] = schema.make_id("e", len(example_id) + 1)
            tables["example"].append((example_id[identity], source, text))
            if item.translated:
                tables["translation/eng"].append((example_id[identity], item.english))
        usage = (example_id[identity], sense_id[item.key])
        position = (markup.LIST_SEPARATOR.join(map(str, starts)), str(length))
        if usage in usages:
            raise CiteError(f"{where}: the same sentence is given twice for the sense {item.key}")
        usages[usage] = position
    tables["usage"] = [usage + position for usage, position in usages.items()]

    # Links of English words to senses.
    for row in data.link_rows():
        if not row.described:
            continue
        where = f"{row.file}:{row.number}"
        keys = markup.link_keys(row)
        for key in keys:
            if key not in sense_id:
                raise CiteError(f"{where}: the sense {key} has no row")
        status, note = legacy.read_q(row.values().get("q", ""))
        tables["link/eng"].append((
            row.keyword, markup.LIST_SEPARATOR.join(sense_id[key] for key in keys),
            row.values().get("r", ""), str(status), note,
        ))

    seen = set()
    for kind, _, subject, source, text in read_notes(config.directory) if notes is None else notes:
        if (kind, subject, source, text) in seen:
            raise CiteError(f"notes: '{subject}' is noted twice under {kind}")
        seen.add((kind, subject, source, text))
        tables["note/open"].append((kind, subject, source, text))

    tables["sequence"] = [
        ("word", str(len(word_id))), ("sense", str(count)), ("example", str(len(example_id))),
    ]
    return tables
