"""Reading and writing of one row. Grammar: ``cite/Markup.md``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from assist.cite.config import SENSE_KEY, Attribute, Config

SEPARATOR = "="
COMMENT = "#"
LIST_SEPARATOR = "/"
PLACEHOLDER = "~"
TRANSLATION = "|"
ATTRIBUTE = re.compile(r"\(([^():\s]*):([^()]*)\)")
XREF = re.compile(r"<([^<>]*)>")
_MARK = "\x00"


@dataclass(frozen=True)
class Row:
    """One row as written. ``body`` is None for a keyword-only row."""

    file: str
    number: int
    line: str
    keyword: str
    body: Optional[str]
    attributes: Tuple[Tuple[str, str], ...]
    text: str
    text_before_attribute: bool

    @property
    def described(self) -> bool:
        return self.body is not None

    def values(self) -> Dict[str, str]:
        """First value of each key, spaces collapsed."""
        result: Dict[str, str] = {}
        for key, value in self.attributes:
            result.setdefault(key, collapse(value))
        return result


def collapse(text: str) -> str:
    """Single spaces, no space at either end."""
    return " ".join(text.split())


def is_row(line: str) -> bool:
    return bool(line.strip()) and not line.startswith(COMMENT)


def parse(line: str, file: str = "", number: int = 0) -> Row:
    """Split a row line into keyword, attributes and description."""
    if SEPARATOR not in line:
        return Row(file, number, line, line.strip(), None, (), "", False)
    keyword, body = line.split(SEPARATOR, 1)
    attributes = tuple((m.group(1), m.group(2)) for m in ATTRIBUTE.finditer(body))
    rest = ATTRIBUTE.sub(_MARK, body)
    text = " ".join(rest.replace(_MARK, " ").split())
    last = rest.rfind(_MARK)
    before = last >= 0 and bool(rest[:last].replace(_MARK, "").strip())
    return Row(file, number, line, keyword.strip(), body, attributes, text, before)


def split_items(attribute: Attribute, value: str) -> List[str]:
    """Items of a value, stripped. A value that is not a list is one item."""
    if not attribute.is_list:
        return [collapse(value)]
    return [collapse(item) for item in value.split(LIST_SEPARATOR)]


def canonical_value(attribute: Attribute, value: str) -> str:
    return LIST_SEPARATOR.join(split_items(attribute, value))


def render(config: Config, keyword: str, values: Dict[str, str], text: str) -> str:
    """Canonical line for a described row."""
    parts = [
        f"({key}:{canonical_value(config.attributes[key], values[key])})"
        for key in config.attributes
        if key in values
    ]
    if text:
        parts.append(text)
    return f"{keyword} {SEPARATOR} {' '.join(parts)}"


def canonical(config: Config, row: Row) -> Optional[str]:
    """Canonical form of a row, or None when the row cannot be rewritten safely.

    A row is left alone when it has an unknown or repeated attribute, an empty
    body, or a parenthesis outside an attribute.
    """
    keyword = " ".join(row.keyword.split())
    if not row.described:
        return keyword
    keys = [key for key, _ in row.attributes]
    if (
        not row.body.strip()
        or any(key not in config.attributes for key in keys)
        or len(set(keys)) != len(keys)
        or "(" in row.text
        or ")" in row.text
    ):
        return None
    return render(config, keyword, row.values(), row.text)


def record(config: Config, row: Row, examples: Iterable["Example"] = ()) -> Dict[str, Any]:
    """A row as plain data, for JSON output."""
    data: Dict[str, Any] = {"keyword": row.keyword, "file": row.file, "line": row.number}
    key = row_key(row)
    if key:
        data["key"] = key
    for name, value in row.values().items():
        attribute = config.attributes.get(name)
        if attribute is None:
            continue
        items = [item for item in split_items(attribute, value) if item]
        if attribute.value == "number":
            data[name] = int(items[0]) if items and items[0].isdigit() else (items[0] if items else "")
        elif attribute.is_list:
            data[name] = items
        else:
            data[name] = items[0] if items else ""
    if row.text:
        data["text"] = row.text
    shown = [example.record() for example in examples]
    if shown:
        data["example"] = shown
    return data


def sense_key(keyword: str, number: str) -> str:
    return f"{keyword}.{number}"


def split_key(key: str) -> Optional[Tuple[str, str]]:
    """Keyword and sense number of a sense key, or None when it is not one."""
    match = SENSE_KEY.match(key)
    return (match.group("keyword"), match.group("number")) if match else None


def row_key(row: Row) -> str:
    """Sense key of a lexicon row; empty when the row has no valid sense number."""
    number = row.values().get("i", "")
    return sense_key(row.keyword, number) if re.fullmatch(r"[1-9][0-9]*", number) else ""


@dataclass(frozen=True)
class Example:
    """One row of an example file: ``key = zolai | english (r:reference)``."""

    row: Row
    zolai: str
    english: str
    translated: bool

    @property
    def key(self) -> str:
        return self.row.keyword

    @property
    def references(self) -> List[str]:
        return [item for item in collapse(self.row.values().get("r", "")).split(LIST_SEPARATOR) if item]

    def record(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"text": self.zolai, "translation": self.english}
        if self.references:
            data["r"] = self.references
        return data


def example(row: Row) -> Example:
    """Read a parsed row of an example file."""
    zolai, bar, english = row.text.partition(TRANSLATION)
    return Example(row, collapse(zolai), collapse(english), bool(bar))


def render_example(key: str, zolai: str, english: str, references: Iterable[str] = ()) -> str:
    line = f"{key} {SEPARATOR} {collapse(zolai)} {TRANSLATION} {collapse(english)}"
    references = [reference for reference in references if reference]
    return f"{line} (r:{LIST_SEPARATOR.join(references)})" if references else line


def canonical_example(row: Row) -> Optional[str]:
    """Canonical form of an example row, or None when it cannot be rewritten safely."""
    if not row.described or row.text.count(TRANSLATION) != 1 or "(" in row.text or ")" in row.text:
        return None
    keys = [name for name, _ in row.attributes]
    if any(name != "r" for name in keys) or len(keys) > 1:
        return None
    item = example(row)
    if not item.zolai or not item.english:
        return None
    return render_example(collapse(row.keyword), item.zolai, item.english, item.references)


def canonical_translation(config: Config, row: Row) -> Optional[str]:
    """Canonical form of a translation row, or None when it cannot be rewritten safely."""
    keys = [name for name, _ in row.attributes]
    if not row.described or not keys or row.text or len(set(keys)) != len(keys):
        return None
    if any(name not in TRANSLATED for name in keys):
        return None
    return render(config, collapse(row.keyword), row.values(), "")


TRANSLATED = ("w", "d")
