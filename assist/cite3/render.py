"""Format 2 lines rebuilt from the tables of format 3."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from assist.cite import markup
from assist.cite.config import CiteError, Config
from assist.cite3 import convert, legacy, schema

Tables = Dict[str, List[Sequence[str]]]


class Lookup:
    """The tables indexed by id."""

    def __init__(self, tables: Tables) -> None:
        self.spelling: Dict[str, str] = {}
        for word, spelling, _ in tables["word"]:
            if word in self.spelling:
                raise CiteError(f"the word id {word} occurs twice")
            self.spelling[word] = spelling
        self.sense: Dict[str, Sequence[str]] = {}
        for row in tables["sense"]:
            if row[0] in self.sense:
                raise CiteError(f"the sense id {row[0]} occurs twice")
            if row[1] not in self.spelling:
                raise CiteError(f"the sense {row[0]} names the word {row[1]}, which has no row")
            self.sense[row[0]] = row
        self.gloss = {row[0]: row for row in tables["gloss/eng"]}
        self.relations: Dict[str, List[Sequence[str]]] = defaultdict(list)
        for row in tables["relation"]:
            self.relations[row[0]].append(row)
        self.example = {row[0]: row for row in tables["example"]}
        self.translation = {row[0]: row[1] for row in tables["translation/eng"]}

    def key(self, sense: str) -> str:
        """Sense key in the form ``keyword.number``."""
        if sense not in self.sense:
            raise CiteError(f"the sense {sense} has no row")
        row = self.sense[sense]
        if not row[2]:
            raise CiteError(f"the sense {sense} has no number")
        return markup.sense_key(self.spelling[row[1]], row[2])

    def word(self, word: str) -> str:
        if word not in self.spelling:
            raise CiteError(f"the word {word} has no row")
        return self.spelling[word]


def lexicon_lines(config: Config, tables: Tables) -> List[str]:
    """One format 2 row per sense, redirect and bare keyword."""
    look = Lookup(tables)
    lines: List[str] = []
    with_row = set()
    for sense, word, number, kind, category, field, _, status, origin, source, note in tables["sense"]:
        with_row.add(word)
        _, terms, definition, text = look.gloss.get(sense, (sense, "", "", ""))
        values = {"i": number, "t": kind, "c": category, "f": field, "w": terms, "d": definition, "o": origin, "r": source}
        related: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        for _, relation, target, order in look.relations.get(sense, ()):
            related[relation].append((int(order), look.word(target)))
        for relation, items in related.items():
            values[relation] = markup.LIST_SEPARATOR.join(item for _, item in sorted(items))
        values["q"] = legacy.write_q(int(status), note)
        lines.append(markup.render(config, look.word(word), {k: v for k, v in values.items() if v}, text))
    for word, relations in look.relations.items():
        if schema.split_id(word)[0] != "w":
            continue
        for _, relation, target, _ in relations:
            if relation != "see":
                raise CiteError(f"the word {word} carries the relation {relation}; only see is defined for a word")
            with_row.add(word)
            lines.append(markup.render(config, look.word(word), {"t": "see"}, f"<{look.word(target)}>"))
    for word, spelling, status in tables["word"]:
        if word not in with_row and status == convert.WORD_STANDARD:
            lines.append(spelling)
    return lines


def example_lines(tables: Tables) -> List[str]:
    """One format 2 example row per usage."""
    look = Lookup(tables)
    lines: List[str] = []
    for example, sense, start, length in tables["usage"]:
        if example not in look.example:
            raise CiteError(f"the usage of {sense} names the example {example}, which has no row")
        _, source, text = look.example[example]
        key = look.key(sense)
        keyword = markup.split_key(key)[0]
        starts = [int(item) for item in start.split(markup.LIST_SEPARATOR) if item]
        zolai = legacy.blank(text, keyword, starts, int(length))
        if example not in look.translation:
            raise CiteError(f"the example {example} has no English translation")
        references = source.split(markup.LIST_SEPARATOR) if source else []
        lines.append(markup.render_example(key, zolai, look.translation[example], references))
    return lines


def link_lines(config: Config, tables: Tables) -> List[str]:
    look = Lookup(tables)
    lines: List[str] = []
    for term, senses, source, status, note in tables["link/eng"]:
        keys = [look.key(sense) for sense in senses.split(markup.LIST_SEPARATOR)]
        values = {"r": source, "q": legacy.write_q(int(status), note)}
        lines.append(markup.render_link(config, term, keys, {k: v for k, v in values.items() if v}))
    return lines


def note_lines(tables: Tables) -> List[str]:
    """Notes as ``kind: subject | source | text``; the kind stands for the section heading."""
    lines: List[str] = []
    for kind, subject, source, text in tables["note/open"]:
        parts = [subject] + ([source] if source else []) + ([text] if text else [])
        lines.append(f"{kind}: {convert.NOTE_SEPARATOR.join(parts)}")
    return lines
