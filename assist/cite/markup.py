"""Reading and writing of one row. Grammar: ``cite/Markup.md``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from assist.cite.config import Attribute, Config

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
    items = split_items(attribute, value)
    if attribute.key == "e":
        items = [canonical_example(item) for item in items]
    return LIST_SEPARATOR.join(items)


def canonical_example(item: str) -> str:
    if item.count(TRANSLATION) != 1:
        return item
    zolai, english = item.split(TRANSLATION)
    return f"{zolai.strip()} {TRANSLATION} {english.strip()}"


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


def record(config: Config, row: Row) -> Dict[str, Any]:
    """A row as plain data, for JSON output."""
    data: Dict[str, Any] = {"keyword": row.keyword, "file": row.file, "line": row.number}
    for key, value in row.values().items():
        attribute = config.attributes.get(key)
        if attribute is None:
            continue
        items = [item for item in split_items(attribute, value) if item]
        if key == "e":
            examples = []
            for item in items:
                zolai, _, english = item.partition(TRANSLATION)
                example = {"text": zolai.strip()}
                if english.strip():
                    example["translation"] = english.strip()
                examples.append(example)
            data[key] = examples
        elif attribute.is_list:
            data[key] = items
        else:
            data[key] = items[0] if items else ""
    if row.text:
        data["text"] = row.text
    return data
