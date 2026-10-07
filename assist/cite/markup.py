"""The markup in which entries are typed and shown. Grammar: ``cite/Format.md``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from assist.cite.config import CiteError

SEPARATOR = "="
COMMENT = "#"
REMOVE = "-"
DONE = "# done"
LIST_SEPARATOR = "/"
PLACEHOLDER = "~"
TRANSLATION = "|"
NEW = "+"
ATTRIBUTE = re.compile(r"\(([^():\s]*):([^()]*)\)")
XREF = re.compile(r"<([^<>]*)>")
MENTION = re.compile(r"\{([^{}]*)\}")
MARK = re.compile(r"<([^<>]*)>|\{([^{}]*)\}")
SENSE_KEY = re.compile(r"^(?P<keyword>.+)\.(?P<number>[1-9][0-9]*)$")
_MARK = "\x00"


@dataclass(frozen=True)
class Row:
    """One typed row. ``body`` is None for a row that is a keyword alone."""

    number: int
    line: str
    remove: bool
    keyword: str
    body: Optional[str]
    attributes: Tuple[Tuple[str, str], ...]
    text: str

    @property
    def described(self) -> bool:
        return self.body is not None

    @property
    def is_example(self) -> bool:
        """An example row is keyed by a sense key; a keyword never holds a dot."""
        return self.described and SENSE_KEY.match(self.keyword) is not None

    def values(self) -> Dict[str, str]:
        """Value of each key, spaces collapsed."""
        return {key: collapse(value) for key, value in self.attributes}


def collapse(text: str) -> str:
    """Single spaces, no space at either end."""
    return " ".join(text.split())


def is_row(line: str) -> bool:
    return bool(line.strip()) and not line.startswith(COMMENT)


def parse(line: str, number: int = 0) -> Row:
    """Split a row line into keyword, attributes and text."""
    content = line.strip()
    remove = content.startswith(REMOVE)
    if remove:
        content = content[len(REMOVE):]
    if SEPARATOR not in content:
        return Row(number, line, remove, collapse(content), None, (), "")
    keyword, body = content.split(SEPARATOR, 1)
    attributes = tuple((m.group(1), m.group(2)) for m in ATTRIBUTE.finditer(body))
    text = collapse(ATTRIBUTE.sub(_MARK, body).replace(_MARK, " "))
    return Row(number, line, remove, collapse(keyword), body, attributes, text)


def split_list(value: str) -> List[str]:
    """Items of a list value, spaces collapsed. An empty value has no item."""
    return [collapse(item) for item in value.split(LIST_SEPARATOR)] if value.strip() else []


def join_list(items: Iterable[str]) -> str:
    return LIST_SEPARATOR.join(items)


def sense_key(keyword: str, number: str) -> str:
    return f"{keyword}.{number}" if number else keyword


def split_key(key: str) -> Optional[Tuple[str, str]]:
    """Keyword and sense number of a sense key, or None when it is not one."""
    match = SENSE_KEY.match(key)
    return (match.group("keyword"), match.group("number")) if match else None


def xref_targets(inner: str) -> List[str]:
    """Keywords or sense keys named inside one link, as written between < and >."""
    return [collapse(item) for item in inner.split(LIST_SEPARATOR)]


@dataclass(frozen=True)
class Segment:
    """A piece of prose: plain ``text``, a ``link`` to a keyword or sense, or a ``mention``."""

    kind: str
    text: str


def segments(text: str) -> List[Segment]:
    """Split prose at its marks, for display.

    ``<a>`` gives one link, ``<a/b>`` gives the links a and b with the
    separator between them as text, and ``{a b}`` gives one mention.
    """
    result: List[Segment] = []

    def plain(piece: str) -> None:
        if piece:
            result.append(Segment("text", piece))

    position = 0
    for match in MARK.finditer(text):
        plain(text[position:match.start()])
        if match.group(1) is not None:
            for index, target in enumerate(xref_targets(match.group(1))):
                if index:
                    plain(LIST_SEPARATOR)
                result.append(Segment("link", target))
        else:
            result.append(Segment("mention", collapse(match.group(2))))
        position = match.end()
    plain(text[position:])
    return result


def split_example(text: str) -> Tuple[str, str, int]:
    """Zolai, translation and the number of translation separators of an example row text."""
    zolai, _, english = text.partition(TRANSLATION)
    return collapse(zolai), collapse(english), text.count(TRANSLATION)


def fill(zolai: str, keyword: str) -> Tuple[str, List[int], int]:
    """Full text of an example, the word positions of the keyword, and its length in words.

    Positions count the words of the full text from 1. A position is given
    once for every placeholder in that word, as in ``pau ~-~``.
    """
    length = len(keyword.split(" "))
    starts: List[int] = []
    position = 1
    for token in zolai.split(" "):
        count = token.count(PLACEHOLDER)
        starts.extend([position] * count)
        position += length if count else 1
    return zolai.replace(PLACEHOLDER, keyword), starts, length


def blank(text: str, keyword: str, starts: Sequence[int], length: int) -> str:
    """The example with the keyword at each position replaced by the placeholder."""
    tokens = text.split(" ")
    for start in sorted(set(starts), reverse=True):
        if start < 1 or start - 1 + length > len(tokens):
            raise CiteError(f"word {start} is outside the example '{text}'")
        span = " ".join(tokens[start - 1:start - 1 + length])
        times = list(starts).count(start)
        if span.count(keyword) < times:
            raise CiteError(f"'{keyword}' is not {times} times at word {start} of the example '{text}'")
        tokens[start - 1:start - 1 + length] = [span.replace(keyword, PLACEHOLDER, times)]
    return " ".join(tokens)


def render_sense(keyword: str, values: Dict[str, str], order: Sequence[str], text: str = "") -> str:
    """Canonical line of a sense row: attributes in the configured order, the text last."""
    parts = [f"({key}:{values[key]})" for key in order if values.get(key)]
    if text:
        parts.append(text)
    return f"{keyword} {SEPARATOR} {' '.join(parts)}"


def render_example(key: str, zolai: str, english: str, source: str = "", example: str = "") -> str:
    """Canonical line of an example row."""
    line = f"{key} {SEPARATOR} {zolai} {TRANSLATION} {english}"
    if source:
        line += f" (r:{source})"
    if example:
        line += f" (e:{example})"
    return line
