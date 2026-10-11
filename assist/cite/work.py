"""Counts of the lexicon and the queue of senses to work on, answered from the index."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from assist.cite import markup
from assist.cite.config import CiteError, Config

EXAMPLES_WANTED = 3
STATS = "STATS.md"
GAPS = {
    "low": "status low: the meaning rests on thin evidence",
    "examples": f"fewer than {EXAMPLES_WANTED} examples",
    "todo": "type todo: the meaning is not yet known",
    "noterm": "no term in the first gloss language",
    "nogloss": "no definition in the first gloss language",
    "doubtful": "an editor note names the sense as doubtful",
    "letter": "spelled with a letter native words do not use, and no origin given",
}
DIMENSIONS = ("type", "status", "set", "field", "category", "source")
SORTS = ("frequency", "key", "random")
VERSE = re.compile(r"^\d+\.\d+\.\d+$")
NOTE_KEY = re.compile(r"^(?P<key>\S+\.[1-9][0-9]*):")


@dataclass(frozen=True)
class Fact:
    """What the counts and the queue need to know of one active sense."""

    id: str
    key: str
    word: str
    word_id: str
    type: str
    set: str
    status: str
    fields: Tuple[str, ...]
    categories: Tuple[str, ...]
    sources: Tuple[str, ...]
    examples: int
    frequency: int
    terms: str
    definition: str
    doubtful: bool
    foreign: bool

    def values(self, dimension: str) -> Tuple[str, ...]:
        """The codes of the sense for one dimension; a sense without a code counts as '-'."""
        found = {
            "type": (self.type,), "status": (self.status,), "set": (self.set,),
            "field": self.fields, "category": self.categories, "source": self.sources,
        }[dimension]
        return tuple(value for value in found if value) or ("-",)


def _codes(value: str, separator: str) -> Tuple[str, ...]:
    return tuple(item for item in (part.strip() for part in value.split(separator)) if item)


def source_codes(value: str, separator: str) -> Tuple[str, ...]:
    """Source codes of a source value: 'bible' for a verse, the code before the colon otherwise."""
    codes = []
    for part in _codes(value, separator):
        code = "bible" if VERSE.match(part) else part.split(":", 1)[0]
        if code not in codes:
            codes.append(code)
    return tuple(codes)


def facts(index, config: Config) -> List[Fact]:
    """Every active sense of the index."""
    language = config.languages[0]
    separator = config.list_separator
    letters = {form for (form,) in index.rows("select form from pattern where kind = 'letter'")}
    doubted: Dict[str, set] = {}
    for subject, text in index.rows("select subject, text from note where kind = 'editor'"):
        match = NOTE_KEY.match(text or "")
        if match:
            doubted.setdefault(subject, set()).add(match.group("key"))
    result = []
    for row in index.rows(
        "select s.id, w.spelling, s.number, w.id, s.type, s.\"set\", s.status, s.field, s.category, s.source, "
        "(select count(*) from usage u where u.sense = s.id), "
        "coalesce(f.bible, 0) + coalesce(f.examples, 0), "
        "coalesce(g.terms, ''), coalesce(g.definition, ''), coalesce(s.origin, '') "
        "from sense s join word w on w.id = s.word left join frequency f on f.fold = w.fold "
        "left join gloss g on g.sense = s.id and g.language = ? where s.status != ?",
        [language, index.retired],
    ):
        (sense_id, spelling, number, word_id, type_code, set_code, status, field, category, source,
         examples, frequency, terms, definition, origin) = row
        key = markup.sense_key(spelling, number)
        notes = doubted.get(spelling, set())
        result.append(Fact(
            sense_id, key, spelling, word_id, type_code, set_code, status,
            _codes(field or "", separator), _codes(category or "", separator), source_codes(source or "", separator),
            examples, frequency, terms, definition, key in notes,
            not origin and type_code not in ("name", "see", "todo") and bool(letters & set(spelling.lower())),
        ))
    return result


def gaps(fact: Fact, config: Config) -> List[str]:
    """The kinds of work a sense still needs, in the order of GAPS."""
    meaning = config.has_meaning(fact.type)
    found = []
    if fact.status == config.status_code("sense", "low"):
        found.append("low")
    if meaning and fact.type != "name" and fact.examples < EXAMPLES_WANTED:
        found.append("examples")
    if fact.type == "todo":
        found.append("todo")
    if meaning and not fact.terms:
        found.append("noterm")
    if meaning and fact.type != "name" and not fact.definition:
        found.append("nogloss")
    if fact.doubtful:
        found.append("doubtful")
    if fact.foreign:
        found.append("letter")
    return found


@dataclass(frozen=True)
class Filter:
    """Conditions a sense must meet; an empty condition holds for every sense."""

    set: str = ""
    type: str = ""
    status: str = ""
    field: str = ""
    source: str = ""
    word: str = ""
    min_frequency: int = 0

    def validate(self, config: Config) -> None:
        for name, value, known in (
            ("set", self.set, config.sets), ("type", self.type, config.types), ("field", self.field, config.fields),
        ):
            if value and value not in known:
                raise CiteError(f"'{value}' is not a {name}; known: {', '.join(known)}")
        if self.status and self.status not in config.sense_status.values():
            raise CiteError(f"'{self.status}' is not a sense status; known: {', '.join(config.sense_status.values())}")
        if self.source and self.source != "bible" and self.source not in config.sources:
            raise CiteError(f"'{self.source}' is not a source; known: bible, {', '.join(config.sources)}")

    def holds(self, fact: Fact, config: Config) -> bool:
        return (
            (not self.set or fact.set == self.set)
            and (not self.type or fact.type == self.type)
            and (not self.status or fact.status == config.status_code("sense", self.status))
            and (not self.field or self.field in fact.fields)
            and (not self.source or self.source in fact.sources)
            and (not self.word or fact.word == self.word)
            and fact.frequency >= self.min_frequency
        )

    def describe(self) -> str:
        parts = [f"{name} {value}" for name, value in (
            ("set", self.set), ("type", self.type), ("status", self.status), ("field", self.field),
            ("source", self.source), ("word", self.word),
        ) if value]
        if self.min_frequency:
            parts.append(f"frequency at least {self.min_frequency}")
        return ", ".join(parts)


def queue(found: Iterable[Fact], config: Config, wanted: Sequence[str], sort: str, seed: Optional[int] = None):
    """Senses with at least one wanted gap, ordered, with the counts of every gap among the given senses."""
    counts = {kind: 0 for kind in GAPS}
    rows = []
    for fact in found:
        kinds = gaps(fact, config)
        for kind in kinds:
            counts[kind] += 1
        kinds = [kind for kind in kinds if kind in wanted]
        if kinds:
            rows.append((fact, kinds))
    if sort == "frequency":
        rows.sort(key=lambda item: (-item[0].frequency, item[0].key))
    elif sort == "key":
        rows.sort(key=lambda item: (item[0].word.lower(), item[0].key))
    else:
        random.Random(seed).shuffle(rows)
    return rows, counts


def label(config: Config, dimension: str, code: str) -> str:
    """Name of a code of a dimension, for display."""
    lists = {
        "type": config.types, "set": config.sets, "field": config.fields, "category": config.categories,
        "source": config.sources,
    }
    if dimension == "status":
        return config.sense_status.get(code, code)
    if dimension == "source" and code == "bible":
        return "Bible"
    entry = lists.get(dimension, {}).get(code)
    return entry["name"] if entry else code


def counts(found: Iterable[Fact], dimension: str) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for fact in found:
        for value in fact.values(dimension):
            result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items(), key=lambda item: (-item[1], item[0])))


def crossed(found: Iterable[Fact], rows: str, columns: str) -> Dict[str, Dict[str, int]]:
    """Counts of senses by the values of two dimensions."""
    result: Dict[str, Dict[str, int]] = {}
    for fact in found:
        for first in fact.values(rows):
            line = result.setdefault(first, {})
            for second in fact.values(columns):
                line[second] = line.get(second, 0) + 1
    return result


def overview(index, config: Config, found: List[Fact]) -> Dict[str, object]:
    """Counts beyond the senses: words, examples, and what each language holds."""
    words = dict(index.rows("select status, count(*) from word group by status"))
    examples = index.rows("select count(*) from example")[0][0]
    by_source: Dict[str, int] = {}
    for (source,) in index.rows("select source from example"):
        for code in source_codes(source or "", config.list_separator) or ("-",):
            by_source[code] = by_source.get(code, 0) + 1
    ids = {fact.id for fact in found}
    languages = {}
    for language in config.languages:
        terms = definitions = 0
        for sense, term, definition in index.rows(
            "select sense, terms, definition from gloss where language = ?", [language]
        ):
            if sense in ids:
                terms += bool(term)
                definitions += bool(definition)
        translations = index.rows("select count(*) from translation where language = ?", [language])[0][0]
        links = index.rows("select count(*) from link where language = ?", [language])[0][0]
        concepts = index.rows("select count(*) from concept where language = ?", [language])[0][0]
        equivalents = index.rows("select count(distinct sense) from equivalent where language = ?", [language])[0][0]
        languages[language] = {
            "terms": terms, "definitions": definitions, "translations": translations, "links": links,
            "concepts": concepts, "senses with an equivalent": equivalents,
        }
    return {
        "words": {config.word_status.get(code, code): number for code, number in sorted(words.items())},
        "examples": examples,
        "examples by source": dict(sorted(by_source.items(), key=lambda item: (-item[1], item[0]))),
        "languages": languages,
    }
