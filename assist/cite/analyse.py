"""Reading of a Zolai word that is not in the lexicon as parts that are.

The parts are words of the lexicon with an active sense. A part at the start
may be a prefix and a part at the end a suffix; the stem patterns restore a
stem that changed before a suffix, and the double patterns read a word that
is written twice. Nothing is stored: an analysis is shown as such.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Sequence, Tuple

MAX_PARTS = 4


@dataclass(frozen=True)
class Meaning:
    """One active sense of a part."""

    sense: str
    key: str
    type: str
    terms: str


@dataclass(frozen=True)
class Part:
    written: str
    keyword: str
    role: str
    meanings: Tuple[Meaning, ...]
    pattern: str = ""


@dataclass
class Analysis:
    word: str
    parts: List[Part] = field(default_factory=list)

    @property
    def plan(self) -> str:
        return " + ".join(part.keyword for part in self.parts)


Lookup = Callable[[str], List[Meaning]]


@dataclass(frozen=True)
class Patterns:
    """The patterns of the pattern table that an analysis applies."""

    stems: Tuple[Tuple[str, str, Tuple[str, ...], str], ...]
    doubles: Dict[str, str]

    @classmethod
    def of(cls, rows: Sequence[Tuple[str, str, str, str, str]], separator: str) -> "Patterns":
        stems = tuple(
            (form, result, tuple(item for item in context.split(separator) if item), note)
            for kind, form, result, context, note in rows if kind == "stem"
        )
        doubles = {form: note for kind, form, _, _, note in rows if kind == "double"}
        return cls(stems, doubles)


def _by_role(meanings: List[Meaning], role: str) -> Tuple[Meaning, ...]:
    """The meanings a part has in its role: a prefix or a suffix only as such, a base not as an affix."""
    if role in ("prefix", "suffix"):
        return tuple(m for m in meanings if m.type == role)
    return tuple(m for m in meanings if m.type not in ("prefix", "suffix"))


def analyse(word: str, lookup: Lookup, patterns: Patterns, limit: int = 3) -> List[Analysis]:
    """Readings of the word as parts of the lexicon, the most likely first."""
    text = word.casefold()
    if not text.isalpha() or len(text) < 2:
        return []
    cache: Dict[str, List[Meaning]] = {}

    def meanings(piece: str) -> List[Meaning]:
        if piece not in cache:
            cache[piece] = lookup(piece)
        return cache[piece]

    found: List[Analysis] = []
    half = len(text) // 2
    if len(text) % 2 == 0 and text[:half] == text[half:]:
        base = meanings(text[:half])
        for type_code, note in patterns.doubles.items():
            matching = tuple(m for m in base if m.type == type_code)
            if matching:
                found.append(Analysis(word, [
                    Part(text[:half], text[:half], "double", matching, note),
                ]))

    def split(rest: str, parts: List[Part]) -> None:
        if len(parts) >= MAX_PARTS:
            return
        for end in range(len(rest), 0, -1):
            piece, tail = rest[:end], rest[end:]
            readings = [(piece, "")]
            if tail:
                for form, result, context, note in patterns.stems:
                    if piece.endswith(result) and any(tail.startswith(affix) for affix in context):
                        readings.append((piece[: len(piece) - len(result)] + form, note))
            roles = ["prefix", "base"] if not parts and tail else ["suffix", "base"] if parts else ["base"]
            for keyword, note in readings:
                for role in roles:
                    if role == "base" and len(keyword) < 2:
                        continue
                    own = _by_role(meanings(keyword), role)
                    if not own:
                        continue
                    part = Part(piece, keyword, role, own, note or _unchanged(keyword, tail, patterns))
                    if tail:
                        split(tail, parts + [part])
                    elif parts:
                        found.append(Analysis(word, parts + [part]))
                    break

    split(text, [])
    unique: Dict[str, Analysis] = {}
    for analysis in sorted(found, key=_rank):
        unique.setdefault(analysis.plan + "|" + "/".join(p.role for p in analysis.parts), analysis)
    return list(unique.values())[:limit]


def _unchanged(keyword: str, tail: str, patterns: Patterns) -> str:
    """A remark when a stem that changes before the following affix is written unchanged."""
    for form, result, context, _ in patterns.stems:
        for affix in context:
            if keyword.endswith(form) and tail.startswith(affix):
                return f"before {affix} this is written {keyword[: len(keyword) - len(form)] + result}"
    return ""


def _rank(analysis: Analysis) -> Tuple:
    """Fewer parts first; then readings whose edges are affixes; then the longest first part."""
    parts = analysis.parts
    affixes = sum(part.role in ("prefix", "suffix") for part in parts)
    bases = len(parts) - affixes
    return (len(parts) if parts[0].role != "double" else 0, bases, -affixes, -len(parts[0].written))


def describe(analysis: Analysis, terms_shown: int = 2) -> str:
    """The analysis as lines for the terminal."""
    lines = [f"  {analysis.plan}" if analysis.parts[0].role != "double" else f"  {analysis.parts[0].keyword} written twice"]
    label = {id(part): part.written if part.written == part.keyword else f"{part.written} = {part.keyword}" for part in analysis.parts}
    width = max(len(text) for text in label.values())
    for part in analysis.parts:
        shown = "; ".join(
            f"{m.terms or '(no term)'} ({m.key}, {m.type})" for m in part.meanings[:terms_shown]
        )
        more = f"; and {len(part.meanings) - terms_shown} more" if len(part.meanings) > terms_shown else ""
        lines.append(f"    {label[id(part)]:<{width}}  {part.role:<7} {shown}{more}")
        if part.pattern:
            lines.append(f"    {'':<{width}}  {'':<7} {part.pattern}")
    return "\n".join(lines)


def record(analysis: Analysis) -> Dict[str, object]:
    return {
        "word": analysis.word,
        "parts": [
            {
                "written": part.written, "keyword": part.keyword, "role": part.role, "pattern": part.pattern,
                "senses": [{"id": m.sense, "key": m.key, "type": m.type, "terms": m.terms} for m in part.meanings],
            }
            for part in analysis.parts
        ],
    }


def from_index(index) -> Tuple[Lookup, Patterns]:
    """Lookup and patterns answered by the index."""
    language = index.config.languages[0]

    def lookup(piece: str) -> List[Meaning]:
        rows = index.rows(
            "select s.id, w.spelling, s.number, s.type, coalesce(g.terms, '') from word w "
            "join sense s on s.word = w.id left join gloss g on g.sense = s.id and g.language = ? "
            "where w.spelling = ? and s.status != ? and s.number != '' order by cast(s.number as integer)",
            [language, piece, index.retired],
        )
        return [Meaning(sense, f"{spelling}.{number}", type_code, terms) for sense, spelling, number, type_code, terms in rows]

    rows = index.rows("select kind, form, result, context, note from pattern")
    return lookup, Patterns.of(rows, index.config.list_separator)


def analyse_with_index(index, word: str, limit: int = 3) -> List[Analysis]:
    lookup, patterns = from_index(index)
    return analyse(word, lookup, patterns, limit)


__all__ = ["Analysis", "Meaning", "Part", "Patterns", "analyse", "analyse_with_index", "describe", "record"]
