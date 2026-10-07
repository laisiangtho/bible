"""The tables as one model in memory: words, senses, glosses, relations, examples."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

from assist.cite import markup, tables
from assist.cite.config import ID_KINDS, CiteError, Config
from assist.cite.tables import Row, Tables


@dataclass
class Word:
    id: str
    spelling: str
    status: str


@dataclass
class Sense:
    id: str
    word: str
    number: str
    type: str
    category: str
    field: str
    set: str
    status: str
    origin: str
    source: str
    note: str


@dataclass
class Gloss:
    terms: str = ""
    definition: str = ""
    text: str = ""

    @property
    def empty(self) -> bool:
        return not (self.terms or self.definition or self.text)


@dataclass(frozen=True)
class Relation:
    kind: str
    to: str
    order: int


@dataclass
class Example:
    id: str
    source: str
    text: str


@dataclass(frozen=True)
class Usage:
    start: str
    length: str

    def starts(self) -> List[int]:
        return [int(item) for item in self.start.split(markup.LIST_SEPARATOR)]


@dataclass
class Link:
    term: str
    senses: str
    source: str
    status: str
    note: str


@dataclass
class Lexicon:
    config: Config
    words: Dict[str, Word] = field(default_factory=dict)
    senses: Dict[str, Sense] = field(default_factory=dict)
    gloss: Dict[str, Dict[str, Gloss]] = field(default_factory=dict)
    relations: Dict[str, List[Relation]] = field(default_factory=dict)
    examples: Dict[str, Example] = field(default_factory=dict)
    usages: Dict[str, Dict[str, Usage]] = field(default_factory=dict)
    translations: Dict[str, Dict[str, str]] = field(default_factory=dict)
    links: Dict[str, Dict[str, Link]] = field(default_factory=dict)
    notes: List[Row] = field(default_factory=list)
    last: Dict[str, int] = field(default_factory=dict)
    # Derived indexes, kept by the methods below.
    spelling: Dict[str, str] = field(default_factory=dict)
    senses_of: Dict[str, List[str]] = field(default_factory=dict)
    shown_by: Dict[str, List[str]] = field(default_factory=dict)

    # Reading.

    def word_of(self, sense_id: str) -> Word:
        return self.words[self.senses[sense_id].word]

    def key(self, sense_id: str) -> str:
        """Sense key as shown: the spelling and the sense number."""
        sense = self.senses[sense_id]
        return markup.sense_key(self.words[sense.word].spelling, sense.number)

    def sense_by_key(self, key: str) -> Optional[str]:
        """Sense id of a sense key such as khut.1; None when there is none."""
        parts = markup.split_key(key)
        word = self.spelling.get(parts[0]) if parts else None
        if word is None:
            return None
        for sense_id in self.senses_of.get(word, []):
            if self.senses[sense_id].number == parts[1]:
                return sense_id
        return None

    def name(self, target: str) -> str:
        """An id as shown: the sense key of a sense, the spelling of a word."""
        if target in self.senses:
            return self.key(target)
        if target in self.words:
            return self.words[target].spelling
        return target

    def relation_items(self, source: str, kind: str) -> List[str]:
        """Targets of one kind as shown, in their order."""
        found = sorted((r for r in self.relations.get(source, []) if r.kind == kind), key=lambda r: r.order)
        return [self.name(relation.to) for relation in found]

    def active(self, sense_id: str) -> bool:
        return self.config.sense_status[self.senses[sense_id].status] != "retired"

    def examples_of(self, sense_id: str) -> Iterator[Tuple[Example, Usage]]:
        for example_id in self.shown_by.get(sense_id, []):
            yield self.examples[example_id], self.usages[example_id][sense_id]

    # Writing.

    def new_id(self, kind: str) -> str:
        self.last[kind] += 1
        return f"{self.config.prefix[kind]}{self.last[kind]}"

    def add_word(self, spelling: str, status: str) -> Word:
        if spelling in self.spelling:
            raise CiteError(f"the word '{spelling}' exists already")
        word = Word(self.new_id("word"), spelling, status)
        self.words[word.id] = word
        self.spelling[spelling] = word.id
        self.senses_of[word.id] = []
        return word

    def add_sense(self, sense: Sense) -> None:
        self.senses[sense.id] = sense
        self.senses_of.setdefault(sense.word, []).append(sense.id)

    def set_relations(self, source: str, kinds: Tuple[str, ...], relations: List[Relation]) -> None:
        """Replace the relations of the given kinds that start at ``source``."""
        kept = [r for r in self.relations.get(source, []) if r.kind not in kinds]
        if kept or relations:
            self.relations[source] = kept + relations
        else:
            self.relations.pop(source, None)

    def set_usage(self, example_id: str, sense_id: str, usage: Usage) -> None:
        if sense_id not in self.usages.setdefault(example_id, {}):
            self.shown_by.setdefault(sense_id, []).append(example_id)
        self.usages[example_id][sense_id] = usage

    def remove_usage(self, example_id: str, sense_id: str) -> None:
        """Remove a usage; an example left without usage is removed with its translations."""
        del self.usages[example_id][sense_id]
        self.shown_by[sense_id].remove(example_id)
        if not self.usages[example_id]:
            del self.usages[example_id]
            del self.examples[example_id]
            for translations in self.translations.values():
                translations.pop(example_id, None)

    # Storing.

    def tables(self) -> Tables:
        """Rows of every table, by stored name."""
        config = self.config
        stored = {name: table.path for name, table in config.tables.items() if not table.per_language}
        result: Tables = {
            stored["word"]: [(w.id, w.spelling, w.status) for w in self.words.values()],
            stored["sense"]: [
                (s.id, s.word, s.number, s.type, s.category, s.field, s.set, s.status, s.origin, s.source, s.note)
                for s in self.senses.values()
            ],
            stored["relation"]: [
                (source, r.kind, r.to, str(r.order)) for source, found in self.relations.items() for r in found
            ],
            stored["example"]: [(e.id, e.source, e.text) for e in self.examples.values()],
            stored["usage"]: [
                (example, sense, usage.start, usage.length)
                for example, found in self.usages.items() for sense, usage in found.items()
            ],
            stored["note"]: list(self.notes),
            stored["sequence"]: [(kind, str(self.last[kind])) for kind in ID_KINDS],
        }
        for language, glosses in self.gloss.items():
            result[config.tables["gloss"].instance(language)] = [
                (sense, g.terms, g.definition, g.text) for sense, g in glosses.items() if not g.empty
            ]
        for language, translations in self.translations.items():
            result[config.tables["translation"].instance(language)] = list(translations.items())
        for language, links in self.links.items():
            result[config.tables["link"].instance(language)] = [
                (l.term, l.senses, l.source, l.status, l.note) for l in links.values()
            ]
        return result


def _language(config: Config, table: str, name: str) -> str:
    """Language code of a stored per-language table name; empty when it is another table."""
    for language in config.languages:
        if config.tables[table].instance(language) == name:
            return language
    return ""


def build(config: Config, data: Tables) -> Lexicon:
    """The model of tables whose structure is sound (see ``check.structure``)."""
    lexicon = Lexicon(config)
    stored = {name: table.path for name, table in config.tables.items() if not table.per_language}
    for row in data[stored["word"]]:
        lexicon.words[row[0]] = Word(*row)
        lexicon.spelling[row[1]] = row[0]
        lexicon.senses_of[row[0]] = []
    for row in data[stored["sense"]]:
        lexicon.add_sense(Sense(*row))
    for found in lexicon.senses_of.values():
        found.sort(key=lambda sense_id: tables.sort_key((lexicon.senses[sense_id].number, sense_id)))
    for source, kind, target, order in data[stored["relation"]]:
        lexicon.relations.setdefault(source, []).append(Relation(kind, target, int(order)))
    for row in data[stored["example"]]:
        lexicon.examples[row[0]] = Example(*row)
    for example, sense, start, length in data[stored["usage"]]:
        lexicon.set_usage(example, sense, Usage(start, length))
    for name, rows in data.items():
        language = _language(config, "gloss", name)
        if language:
            lexicon.gloss[language] = {row[0]: Gloss(*row[1:]) for row in rows}
        language = _language(config, "translation", name)
        if language:
            lexicon.translations[language] = dict(rows)
        language = _language(config, "link", name)
        if language:
            lexicon.links[language] = {row[0]: Link(*row) for row in rows}
    lexicon.notes = list(data[stored["note"]])
    lexicon.last = {kind: int(last) for kind, last in data[stored["sequence"]]}
    return lexicon
