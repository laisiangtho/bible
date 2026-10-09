"""Display of senses as text and as data, and the verse search of the Bible texts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from assist.cite import bible, markup, render
from assist.cite.config import CiteError, Config
from assist.cite.lexicon import Lexicon


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
