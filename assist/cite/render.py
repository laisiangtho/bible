"""The model written as markup: the rows of a word as they are typed."""

from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple

from assist.cite import markup
from assist.cite.lexicon import Lexicon

RELATION_KEYS = ("s", "a", "b", "j", "v")
SENSE_ORDER = ("i", "t", "c", "f", "w", "d", "s", "a", "b", "j", "v", "o", "r", "q")


def status_value(lexicon: Lexicon, status: str, note: str) -> str:
    """The value of q; empty for a draft without remark, which is what a row without q means."""
    name = lexicon.config.sense_status[status]
    if note:
        return f"{name}, {note}"
    return "" if name == "draft" else name


def sense_values(lexicon: Lexicon, sense_id: str) -> Tuple[Dict[str, str], str]:
    """Attributes and text of a sense in the first gloss language."""
    sense = lexicon.senses[sense_id]
    gloss = lexicon.gloss.get(lexicon.config.languages[0], {}).get(sense_id)
    values = {
        "i": sense.number or sense.id,
        "t": sense.type,
        "c": sense.category,
        "f": sense.field,
        "w": gloss.terms if gloss else "",
        "d": gloss.definition if gloss else "",
        "o": sense.origin,
        "r": sense.source,
        "q": status_value(lexicon, sense.status, sense.note),
    }
    for kind in RELATION_KEYS:
        values[kind] = markup.join_list(lexicon.relation_items(sense_id, kind))
    return values, gloss.text if gloss else ""


def sense_line(lexicon: Lexicon, sense_id: str) -> str:
    values, text = sense_values(lexicon, sense_id)
    return markup.render_sense(lexicon.word_of(sense_id).spelling, values, SENSE_ORDER, text)


def redirect_line(lexicon: Lexicon, word_id: str) -> str:
    """The row of a word that only points to another word; empty when it does not."""
    targets = lexicon.relation_items(word_id, "see")
    if not targets:
        return ""
    return markup.render_sense(lexicon.words[word_id].spelling, {"t": "see"}, SENSE_ORDER, f"<{targets[0]}>")


def example_line(lexicon: Lexicon, example_id: str, sense_id: str, with_id: bool = True) -> str:
    example = lexicon.examples[example_id]
    usage = lexicon.usages[example_id][sense_id]
    keyword = lexicon.word_of(sense_id).spelling
    zolai = markup.blank(example.text, keyword, usage.starts(), int(usage.length))
    english = lexicon.translations.get(lexicon.config.languages[0], {}).get(example_id, "")
    return markup.render_example(
        lexicon.key(sense_id), zolai, english, example.source, example_id if with_id else ""
    )


def word_lines(lexicon: Lexicon, word_id: str) -> List[str]:
    """Every row of a word: the redirect, then each sense followed by its examples."""
    lines: List[str] = []
    redirect = redirect_line(lexicon, word_id)
    if redirect:
        lines.append(redirect)
    for sense_id in lexicon.senses_of.get(word_id, []):
        lines.append(sense_line(lexicon, sense_id))
        lines.extend(example_line(lexicon, example.id, sense_id) for example, _ in lexicon.examples_of(sense_id))
    if not lines:
        lines.append(lexicon.words[word_id].spelling)
    return lines


def version(lines: List[str]) -> str:
    """Stamp of the rows of a word: equal exactly when the rows are equal."""
    return hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest()[:12]
