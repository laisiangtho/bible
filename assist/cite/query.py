"""Questions asked of the data: lookup of entries, verse search, missing words."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from assist.cite import bible, markup, words
from assist.cite.config import CiteError, Config
from assist.cite.markup import Row


def lookup(config: Config, rows: List[Row], query: str, english: bool = False) -> List[Row]:
    """Rows for a Zolai keyword or variant, or for an English term.

    An exact match is preferred. Without one, the comparison ignores case,
    then also hyphens, spaces and apostrophes, so that a keyword written
    ``ze-et`` is found as ``zeet`` or ``ze et``. For an English term a
    whole-word match inside a term is tried last.
    """
    query = markup.collapse(query)
    if not query:
        raise CiteError("the query is empty")
    key = "w" if english else "v"
    attribute = config.attributes[key]

    def candidates(row: Row) -> List[str]:
        found = [] if english else [row.keyword]
        value = row.values().get(key)
        if value:
            found.extend(item for item in markup.split_items(attribute, value) if item)
        return found

    exact = [row for row in rows if query in candidates(row)]
    if exact:
        return exact
    folded = query.casefold()
    loose = [row for row in rows if folded in (c.casefold() for c in candidates(row))]
    if loose:
        return loose
    squashed = squash(query)
    joined = [row for row in rows if squashed in (squash(c) for c in candidates(row))]
    if joined or not english:
        return joined
    word = re.compile(rf"(?<!\w){re.escape(folded)}(?!\w)")
    return [row for row in rows if any(word.search(c.casefold()) for c in candidates(row))]


def squash(text: str) -> str:
    """Comparison key that ignores case, hyphens, spaces and apostrophes."""
    return "".join(character for character in text.casefold() if character not in " -'\u2019")


def describe(config: Config, row: Row) -> str:
    """A row as labelled lines for reading."""
    lines = [f"{row.keyword}    [{row.file}:{row.number}]"]
    if not row.described:
        lines.append("  not yet described")
        return "\n".join(lines)
    values = row.values()
    for key, attribute in config.attributes.items():
        if key not in values:
            continue
        items = [item for item in markup.split_items(attribute, values[key]) if item]
        if key == "t":
            shown = [f"{item} ({config.types[item]['name']})" if item in config.types else item for item in items]
        elif key == "c":
            shown = [
                f"{item} ({config.categories[item]['name']})" if item in config.categories else item
                for item in items
            ]
        else:
            shown = items
        for index, item in enumerate(shown):
            label = attribute.name if index == 0 else ""
            lines.append(f"  {label:<13}{item}")
    if row.text:
        lines.append(f"  {'description':<13}{row.text}")
    return "\n".join(lines)


@dataclass(frozen=True)
class Hit:
    book: int
    chapter: int
    verse: int
    book_name: str
    texts: Tuple[Tuple[str, str], ...]


def search(config: Config, query: str, source: str = "", limit: int = 10) -> Tuple[str, int, List[Hit]]:
    """Verses that contain the query as whole words, with parallel verses.

    The source translations are tried in the configured order; the first one
    with a match is used. Returns the translation used, the number of matching
    verses and the hits up to the limit (0 for no limit).
    """
    query = markup.collapse(query)
    if not query:
        raise CiteError("the query is empty")
    settings = config.raw["bible"]
    sources = [source] if source else settings["source"]
    pattern = re.compile(rf"(?<![^\W_]){re.escape(query)}(?![^\W_])", re.IGNORECASE)
    for identify in sources:
        data = bible.load(config, identify)
        matches = [
            (book, chapter, verse, text)
            for book, chapter, verse, text in bible.verses(data, identify)
            if pattern.search(text)
        ]
        if not matches:
            continue
        shown = matches if limit == 0 else matches[:limit]
        parallels = [(other, bible.load(config, other)) for other in settings["reference"] if other != identify]
        hits = []
        for book, chapter, verse, text in shown:
            texts = [(identify, text)]
            for other, other_data in parallels:
                parallel = bible.verse_text(other_data, book, chapter, verse)
                if parallel:
                    texts.append((other, parallel))
            hits.append(Hit(book, chapter, verse, bible.book_name(data, book), tuple(texts)))
        return identify, len(matches), hits
    return sources[0], 0, []


@dataclass(frozen=True)
class Coverage:
    forms: int
    forms_covered: int
    occurrences: int
    occurrences_covered: int
    missing: List[Dict]


def coverage(config: Config, rows: List[Row]) -> Coverage:
    """How much of the plain word list of the keyword language has a row."""
    known = {row.keyword for row in rows}
    variant = config.attributes.get("v")
    if variant is not None:
        for row in rows:
            value = row.values().get("v")
            if value:
                known.update(item for item in markup.split_items(variant, value) if item)
    listed = words.read(config, config.language, "plain")["word"]
    missing = [entry for entry in listed if entry["w"] not in known]
    total = sum(entry["n"] for entry in listed)
    return Coverage(
        forms=len(listed),
        forms_covered=len(listed) - len(missing),
        occurrences=total,
        occurrences_covered=total - sum(entry["n"] for entry in missing),
        missing=missing,
    )
