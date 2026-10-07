"""Words counted in the Bible translations of the keyword language.

A form that starts a sentence is counted under its lowercase spelling when,
inside sentences, the lowercase spelling is more frequent than the spelling
as written; otherwise it is counted as written. Names therefore keep their
capital and ordinary words lose the capital that only marks the start of a
sentence.

A right single quotation mark directly after a letter is read as an
apostrophe and written as a straight one; after punctuation it is a closing
quotation mark.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, Iterator, List, Tuple

from assist.cite import bible
from assist.cite.config import Config

WRITTEN = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*'?|\d+")
LETTERS = re.compile(r"[^\W\d_]+")
CURLY_APOSTROPHE = re.compile(r"(?<=[^\W\d_])\u2019")
SENTENCE_END = set(".!?:;“‘\"(")

Token = Tuple[str, str, bool]


def tokens(text: str) -> Iterator[Token]:
    """Yield (model, form, starts_sentence) for every form in a verse text."""
    text = CURLY_APOSTROPHE.sub("'", text)
    previous_end = 0
    first = True
    for match in WRITTEN.finditer(text):
        form = match.group()
        gap = text[previous_end:match.start()]
        initial = first or any(character in SENTENCE_END for character in gap)
        first = False
        previous_end = match.end()
        following = text[match.end():match.end() + 1]
        if form.isdigit():
            yield "number", form, False
            continue
        for index, part in enumerate(LETTERS.findall(form)):
            yield "plain", part, initial and index == 0
        if "-" in form:
            yield "dash", form, initial
        if "'" in form:
            yield "apostrophe", form, initial
        if following == "!":
            yield "exclamation", form + "!", False
        if following == "?":
            yield "question", form + "?", False


def count(config: Config) -> List[Tuple[str, int, str]]:
    """Every plain word of the source translations: spelling, occurrences, first verse; most frequent first."""
    inside: Counter = Counter()
    starting: Counter = Counter()
    first_seen: Dict[str, str] = {}
    for identify in config.raw["bible"]["source"]:
        data = bible.load(config, identify)
        for book, chapter, verse, text in bible.verses(data, identify):
            for model, form, initial in tokens(text):
                if model != "plain":
                    continue
                (starting if initial else inside)[form] += 1
                first_seen.setdefault(form, f"{book}.{chapter}.{verse}")
    counts = Counter(inside)
    first = {form: first_seen[form] for form in counts}
    for form, number in starting.items():
        lowered = form[0].lower() + form[1:]
        target = lowered if inside[lowered] > inside[form] else form
        counts[target] += number
        reference = first_seen[form]
        if target not in first or _order(reference) < _order(first[target]):
            first[target] = reference
    return [(form, number, first[form]) for form, number in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _order(reference: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in reference.split("."))
