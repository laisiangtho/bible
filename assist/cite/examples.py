"""Examples of a row measured against its English terms.

An example item is ``zolai | english``. An example covers a term of ``w``
when its English translation uses the term, in any inflected form.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from assist.cite import markup
from assist.cite.config import Config
from assist.cite.markup import Row

PER_TERM = 3
WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")
MINOR = frozenset(
    "a an the to of be is are was were been being it one someone something "
    "oneself up out off in on at by for with from as or and not".split()
)
IRREGULAR = {
    form: base
    for base, forms in {
        "be": "am is are was were been being", "have": "has had having", "do": "does did done doing",
        "go": "goes went gone", "come": "came", "say": "said", "see": "saw seen", "give": "gave given",
        "take": "took taken", "make": "made", "know": "knew known", "eat": "ate eaten", "drink": "drank drunk",
        "speak": "spoke spoken", "tell": "told", "bring": "brought", "send": "sent", "find": "found",
        "leave": "left", "keep": "kept", "hear": "heard", "stand": "stood", "sit": "sat", "lie": "lay lain lying",
        "lay": "laid", "rise": "rose risen", "fall": "fell fallen", "run": "ran", "begin": "began begun",
        "break": "broke broken", "build": "built", "buy": "bought", "sell": "sold", "pay": "paid",
        "bear": "bore born borne", "bind": "bound", "bite": "bit bitten", "blow": "blew blown",
        "burn": "burnt", "choose": "chose chosen", "die": "dying", "dig": "dug", "draw": "drew drawn",
        "drive": "drove driven", "dwell": "dwelt", "feed": "fed", "feel": "felt", "fight": "fought",
        "flee": "fled", "fly": "flew flown", "forget": "forgot forgotten", "forgive": "forgave forgiven",
        "get": "got gotten", "grow": "grew grown", "hang": "hung", "hide": "hid hidden", "hold": "held",
        "kneel": "knelt", "lead": "led", "lose": "lost", "mean": "meant", "meet": "met", "ride": "rode ridden",
        "seek": "sought", "shake": "shook shaken", "shine": "shone", "shoot": "shot", "sing": "sang sung",
        "sink": "sank sunk", "sleep": "slept", "slay": "slew slain", "sow": "sown", "spend": "spent",
        "steal": "stole stolen", "strike": "struck stricken", "swear": "swore sworn", "teach": "taught",
        "tear": "tore torn", "think": "thought", "throw": "threw thrown", "tread": "trod trodden",
        "understand": "understood", "wake": "woke woken", "wear": "wore worn", "weep": "wept",
        "win": "won", "write": "wrote written", "man": "men", "woman": "women", "child": "children",
        "foot": "feet", "tooth": "teeth", "ox": "oxen", "sheep": "sheep", "good": "better best",
        "bad": "worse worst", "wife": "wives", "life": "lives", "knife": "knives", "leaf": "leaves",
        "thief": "thieves", "half": "halves", "calf": "calves", "wolf": "wolves", "loaf": "loaves",
    }.items()
    for form in forms.split()
}
SUFFIXES = ("ingly", "ing", "edly", "ies", "ied", "ed", "es", "ly", "s")


def stem(word: str) -> str:
    """A crude stem: equal for the inflected forms of one English word."""
    word = IRREGULAR.get(word, word)
    if word.endswith(("ies", "ied")) and len(word) > 4:
        word = word[:-3] + "y"
    else:
        for suffix in SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
    if len(word) > 3 and word[-1] == word[-2] and word[-1] not in "aeiou":
        word = word[:-1]
    if len(word) > 3 and word[-1] in "ey":
        word = word[:-1]
    return word


def stems(text: str) -> List[str]:
    return [stem(word) for word in WORD.findall(text.lower().replace("’", "'"))]


def term_stems(term: str) -> List[str]:
    """Stems of the words of a term that an example has to show."""
    words = WORD.findall(term.lower().replace("’", "'"))
    major = [word for word in words if word not in MINOR]
    return [stem(word) for word in (major or words)]


def uses(term: str, english: str) -> bool:
    """True when the English text uses every main word of the term."""
    wanted = term_stems(term)
    present = set(stems(english))
    return bool(wanted) and all(word in present for word in wanted)


def split(item: str) -> Tuple[str, str]:
    """Zolai and English part of one example item; English is empty when absent."""
    zolai, _, english = item.partition(markup.TRANSLATION)
    return zolai.strip(), english.strip()


@dataclass(frozen=True)
class Measure:
    """Examples of one row counted per term."""

    row: Row
    examples: int
    untranslated: int
    terms: Tuple[Tuple[str, int], ...]

    @property
    def short(self) -> List[Tuple[str, int]]:
        return [(term, count) for term, count in self.terms if count < PER_TERM]

    @property
    def complete(self) -> bool:
        return not self.untranslated and not self.short and (bool(self.terms) or self.examples >= PER_TERM)


def measure(config: Config, row: Row) -> Measure:
    values = row.values()
    attributes = config.attributes
    items = [i for i in markup.split_items(attributes["e"], values.get("e", "")) if i]
    terms = [t for t in markup.split_items(attributes["w"], values.get("w", "")) if t]
    pairs = [split(item) for item in items]
    counts = tuple((term, sum(uses(term, english) for _, english in pairs)) for term in terms)
    return Measure(row, len(items), sum(not english for _, english in pairs), counts)


def measurable(config: Config, row: Row) -> bool:
    """Rows expected to carry examples: described, with a meaning, not a name."""
    code = row.values().get("t", "")
    return row.described and config.has_meaning(code) and code != "name"


def incomplete(config: Config, rows: Iterable[Row]) -> List[Measure]:
    result = []
    for row in rows:
        if measurable(config, row):
            measured = measure(config, row)
            if not measured.complete:
                result.append(measured)
    return result
