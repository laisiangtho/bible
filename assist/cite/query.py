"""Questions asked of the data: lookup of entries, text search, verse search, missing words."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from assist.cite import bible, markup, render, words
from assist.cite.config import CiteError, Config
from assist.cite.lexicon import Lexicon


def squash(text: str) -> str:
    """Comparison key that ignores case, hyphens, spaces and apostrophes."""
    return "".join(character for character in text.casefold() if character not in " -'’")


def _closest(query: str, candidates: Dict[str, List[str]], inside: bool = False) -> List[str]:
    """Values of the candidates that match best: exact, then without case, then squashed, then as a whole word."""
    folded, squashed = query.casefold(), squash(query)
    tests = [
        lambda name: name == query,
        lambda name: name.casefold() == folded,
        lambda name: squash(name) == squashed,
    ]
    if inside:
        word = re.compile(rf"(?<!\w){re.escape(folded)}(?!\w)")
        tests.append(lambda name: word.search(name.casefold()) is not None)
    for test in tests:
        found = [value for name, values in candidates.items() if test(name) for value in values]
        if found:
            return list(dict.fromkeys(found))
    return []


def words_for(lexicon: Lexicon, query: str) -> List[str]:
    """Word ids for a Zolai spelling.

    An exact match is preferred. Without one, the comparison ignores case,
    then also hyphens, spaces and apostrophes, so that ``ze-et`` is found as
    ``zeet`` or ``ze et``.
    """
    query = markup.collapse(query)
    if not query:
        raise CiteError("the query is empty")
    return _closest(query, {spelling: [word] for spelling, word in lexicon.spelling.items()})


def senses_for_term(lexicon: Lexicon, query: str, language: str) -> List[str]:
    """Sense ids that have the term in the language; a whole-word match inside a term is tried last."""
    query = markup.collapse(query)
    if not query:
        raise CiteError("the query is empty")
    terms: Dict[str, List[str]] = {}
    for sense_id, gloss in lexicon.gloss.get(language, {}).items():
        if lexicon.active(sense_id):
            for term in markup.split_list(gloss.terms):
                terms.setdefault(term, []).append(sense_id)
    return _closest(query, terms, inside=True)


def linked(lexicon: Lexicon, query: str, language: str) -> Optional[Tuple[str, List[str]]]:
    """Remark and senses of the link row of a word of the language."""
    link = lexicon.links.get(language, {}).get(markup.collapse(query).casefold())
    if link is None:
        return None
    senses = [sense_id for sense_id in markup.split_list(link.senses) if lexicon.active(sense_id)]
    return render.status_value(lexicon, link.status, link.note), senses


def record(lexicon: Lexicon, sense_id: str) -> Dict[str, Any]:
    """A sense as plain data, for JSON output."""
    config = lexicon.config
    sense = lexicon.senses[sense_id]
    data: Dict[str, Any] = {
        "id": sense.id,
        "key": lexicon.key(sense_id),
        "word": {"id": sense.word, "spelling": lexicon.word_of(sense_id).spelling},
        "type": sense.type,
        "set": sense.set,
        "status": config.sense_status[sense.status],
    }
    for name, value in (("category", sense.category), ("field", sense.field), ("source", sense.source)):
        if value:
            data[name] = markup.split_list(value)
    for name, value in (("origin", sense.origin), ("note", sense.note)):
        if value:
            data[name] = value
    data["gloss"] = {
        language: {
            key: value for key, value in (
                ("terms", markup.split_list(glosses[sense_id].terms)),
                ("definition", glosses[sense_id].definition),
                ("text", glosses[sense_id].text),
            ) if value
        }
        for language, glosses in lexicon.gloss.items() if sense_id in glosses
    }
    relations = {
        kind: lexicon.relation_items(sense_id, kind)
        for kind in render.RELATION_KEYS if lexicon.relation_items(sense_id, kind)
    }
    if relations:
        data["relation"] = relations
    data["example"] = [
        {
            "id": example.id,
            "text": example.text,
            "start": usage.starts(),
            "length": int(usage.length),
            "source": markup.split_list(example.source),
            "translation": {
                language: found[example.id] for language, found in lexicon.translations.items() if example.id in found
            },
        }
        for example, usage in lexicon.examples_of(sense_id)
    ]
    return data


def describe(lexicon: Lexicon, sense_id: str, examples: int = 0) -> str:
    """A sense as labelled lines for reading. ``examples`` limits the examples shown; 0 shows all."""
    config = lexicon.config
    sense = lexicon.senses[sense_id]
    lines = [f"{lexicon.key(sense_id)}    [{sense.id}, {sense.set}, {config.sense_status[sense.status]}]"]

    def put(label: str, value: str) -> None:
        if value:
            lines.append(f"  {label:<13}{value}")

    def coded(value: str, codes: Dict[str, Dict[str, Any]]) -> str:
        return ", ".join(f"{code} ({codes[code]['name']})" for code in markup.split_list(value))

    put("type", coded(sense.type, config.types))
    put("category", coded(sense.category, config.categories))
    put("field", coded(sense.field, config.fields))
    for language, glosses in lexicon.gloss.items():
        gloss = glosses.get(sense_id)
        if gloss:
            put(f"term {language}", ", ".join(markup.split_list(gloss.terms)))
            put("definition", gloss.definition)
            put("text", gloss.text)
    for kind in render.RELATION_KEYS:
        put(config.relations[kind]["name"], ", ".join(lexicon.relation_items(sense_id, kind)))
    put("origin", sense.origin)
    put("source", ", ".join(markup.split_list(sense.source)))
    put("note", sense.note)
    shown = list(lexicon.examples_of(sense_id))
    keyword = lexicon.word_of(sense_id).spelling
    primary = lexicon.translations.get(config.languages[0], {})
    for index, (example, usage) in enumerate(shown[:examples] if examples else shown):
        zolai = markup.blank(example.text, keyword, usage.starts(), int(usage.length))
        source = f"  [{example.source}]" if example.source else ""
        lines.append(f"  {'example' if index == 0 else '':<13}{zolai} | {primary.get(example.id, '')}{source}")
    if examples and len(shown) > examples:
        lines.append(f"  {'':<13}and {len(shown) - examples} more")
    return "\n".join(lines)


def describe_word(lexicon: Lexicon, word_id: str, examples: int = 0) -> str:
    """A word with its redirect and every active sense."""
    word = lexicon.words[word_id]
    status = lexicon.config.word_status[word.status]
    blocks = []
    target = lexicon.relation_items(word_id, "see")
    variant_of = [
        lexicon.name(source) for source, relations in lexicon.relations.items()
        if any(r.kind == "v" and r.to == word_id for r in relations)
    ]
    senses = [sense_id for sense_id in lexicon.senses_of.get(word_id, []) if lexicon.active(sense_id)]
    if target:
        blocks.append(f"{word.spelling}    [{word.id}, {status}]\n  {'see':<13}{target[0]}")
    if variant_of:
        blocks.append(f"{word.spelling}    [{word.id}, {status}]\n  {'variant of':<13}{', '.join(variant_of)}")
    blocks.extend(describe(lexicon, sense_id, examples) for sense_id in senses)
    if not blocks:
        blocks.append(f"{word.spelling}    [{word.id}, {status}]\n  not yet described")
    return "\n\n".join(blocks)


def find(lexicon: Lexicon, query: str, limit: int = 20) -> Dict[str, List[str]]:
    """Lines of the data that contain the text, without regard to case: spellings, glosses, examples."""
    query = markup.collapse(query).casefold()
    if not query:
        raise CiteError("the query is empty")
    found: Dict[str, List[str]] = {"word": [], "gloss": [], "example": []}
    counts = dict.fromkeys(found, 0)

    def hit(kind: str, line: str) -> None:
        counts[kind] += 1
        if not limit or len(found[kind]) < limit:
            found[kind].append(line)

    for word in lexicon.words.values():
        if query in word.spelling.casefold():
            hit("word", f"{word.id}  {word.spelling}")
    for language, glosses in lexicon.gloss.items():
        for sense_id, gloss in glosses.items():
            if query in f"{gloss.terms}\t{gloss.definition}\t{gloss.text}".casefold():
                hit("gloss", f"{sense_id}  {lexicon.key(sense_id)}  [{language}]  {gloss.terms}  {gloss.definition}".rstrip())
    for example in lexicon.examples.values():
        shown = [found_in.get(example.id, "") for found_in in lexicon.translations.values()]
        if query in example.text.casefold() or any(query in text.casefold() for text in shown):
            senses = ", ".join(lexicon.key(sense_id) for sense_id in lexicon.usages.get(example.id, {}))
            hit("example", f"{example.id}  {example.text} | {' | '.join(shown)}  [{senses}]")
    for kind, total in counts.items():
        if total > len(found[kind]):
            found[kind].append(f"and {total - len(found[kind])} more")
    return found


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
    missing: List[Tuple[str, int, str]]


def coverage(lexicon: Lexicon) -> Coverage:
    """How much of the running text of the source translations is a word of the lexicon."""
    retired = lexicon.config.status_code("word", "retired")
    known = {word.spelling for word in lexicon.words.values() if word.status != retired}
    counted = words.count(lexicon.config)
    missing = [entry for entry in counted if entry[0] not in known]
    total = sum(number for _, number, _ in counted)
    return Coverage(
        forms=len(counted),
        forms_covered=len(counted) - len(missing),
        occurrences=total,
        occurrences_covered=total - sum(number for _, number, _ in missing),
        missing=missing,
    )
