"""The rules of ``cite/Markup.md`` applied to rows. Rule ids: configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple

from assist.cite import markup
from assist.cite.config import Config
from assist.cite.markup import Row


@dataclass(frozen=True)
class Finding:
    file: str
    number: int
    rule: str
    detail: str

    @property
    def is_error(self) -> bool:
        return self.rule.startswith("E")

    def describe(self, config: Config) -> str:
        name = config.rules.get(self.rule, {}).get("name", "")
        place = f"{self.file}:{self.number}" if self.number else self.file
        return f"{place}: {self.rule} {name}: {self.detail}"


def check_rows(config: Config, rows: Iterable[Row]) -> List[Finding]:
    """Every finding for the rows. Keywords resolve across all rows given."""
    rows = list(rows)
    keywords: Set[str] = {row.keyword for row in rows}
    seen: Dict[Tuple, str] = {}
    findings: List[Finding] = []
    for row in rows:
        findings.extend(_check_row(config, row, keywords, seen))
    return findings


def _check_row(config: Config, row: Row, keywords: Set[str], seen: Dict[Tuple, str]) -> List[Finding]:
    found: List[Finding] = []

    def add(rule: str, detail: str) -> None:
        found.append(Finding(row.file, row.number, rule, detail))

    attributes = config.attributes
    if not config.keyword.match(row.keyword):
        add("E02", f"'{row.keyword}'")
    if not row.described:
        _check_form(config, row, add)
        return found
    if not row.body.strip():
        add("E03", "nothing after the separator")
        return found
    if "(" in row.text or ")" in row.text:
        add("E04", f"'{_short(row.text)}'")

    values: Dict[str, str] = {}
    for key, value in row.attributes:
        if key not in attributes:
            add("E05", f"'{key}'")
        elif key in values:
            add("E06", f"'{key}'")
        else:
            values[key] = value
    items = {key: markup.split_items(attributes[key], value) for key, value in values.items()}
    for key, parts in items.items():
        if any(not part for part in parts):
            add("E07", f"'{key}'")
        items[key] = [part for part in parts if part]

    type_code = values.get("t", "").strip()
    if "t" not in values:
        add("E08", "attribute t is missing")
    elif type_code not in config.types:
        add("E08", f"'{type_code}' is not a type")
    for code in items.get("c", []):
        if code not in config.categories:
            add("E09", f"'{code}' is not a category")
    if config.has_meaning(type_code) and not items.get("w") and not items.get("d"):
        add("E10", "neither w nor d")

    for key, parts in items.items():
        for part in parts:
            if key == "e":
                zolai, _, english = part.partition(markup.TRANSLATION)
                if part.count(markup.TRANSLATION) > 1:
                    add("E11", f"more than one | in '{_short(part)}'")
                elif markup.PLACEHOLDER not in zolai:
                    add("E11", f"no ~ in '{_short(part)}'")
                elif markup.PLACEHOLDER in english:
                    add("E11", f"~ in the translation of '{_short(part)}'")
                elif markup.TRANSLATION in part and not english.strip():
                    add("E07", "'e' has an empty translation")
            elif markup.PLACEHOLDER in part or markup.TRANSLATION in part:
                add("E11", f"~ or | in attribute '{key}'")
    if markup.PLACEHOLDER in row.text or markup.TRANSLATION in row.text:
        add("E11", "~ or | in the description")

    references: List[str] = []
    for key, parts in list(items.items()) + [("", [row.text])]:
        allowed = key == "" or attributes[key].xref
        for part in parts:
            if "<" not in part and ">" not in part:
                continue
            leftover = markup.XREF.sub("", part)
            if not allowed:
                add("E12", f"< > in attribute '{key}'")
            elif "<" in leftover or ">" in leftover:
                add("E12", f"unbalanced < > in '{_short(part)}'")
            else:
                for target in markup.XREF.findall(part):
                    if config.keyword.match(target):
                        references.append(target)
                    else:
                        add("E12", f"<{target}> is not one keyword")
    for key, attribute in attributes.items():
        if not attribute.resolve:
            continue
        for part in items.get(key, []):
            if part not in keywords:
                add("E13", f"({key}:{part}) names no row")
    for target in references:
        if target not in keywords:
            add("E13", f"<{target}> names no row")
    for part in items.get("v", []):
        if not config.keyword.match(part):
            add("E14", f"'{part}' is not a valid keyword")
        elif part in keywords:
            add("E14", f"'{part}' has a row of its own")
    for key, attribute in attributes.items():
        if attribute.value != "reference":
            continue
        for part in items.get(key, []):
            if not attribute.pattern.match(part):
                add("E15", f"'{part}'")

    identity = (
        row.keyword, type_code, tuple(items.get("c", [])),
        tuple(items.get("w", [])), tuple(items.get("d", [])),
    )
    if identity in seen:
        add("E16", f"same as {seen[identity]}")
    else:
        seen[identity] = f"{row.file}:{row.number}"
    if type_code == "name" and not re.match(r"[A-Z0-9]", row.keyword):
        add("E17", f"'{row.keyword}'")
    if type_code == "see" and (set(values) != {"t"} or not markup.XREF.fullmatch(row.text)):
        add("E18", "a redirect is the type followed by one cross-reference")
    for key, required in config.files.get(_file_key(config, row.file), {}).get("require", {}).items():
        if required not in items.get(key, []):
            add("E19", f"({key}:{required}) is required in this file")

    _check_form(config, row, add)
    return found


def _check_form(config: Config, row: Row, add) -> None:
    """Form findings. Reported exactly when the canonical line differs."""
    canonical = markup.canonical(config, row)
    if canonical is None or canonical == row.line:
        return
    specific = False
    if row.described:
        if not re.match(r"^[^=]*[^ =] = [^ ]", row.line):
            add("F01", "write the separator as ' = '")
            specific = True
        keys = [key for key, _ in row.attributes]
        if keys != sorted(keys, key=lambda key: config.attributes[key].order):
            add("F03", f"order is {' '.join(keys)}")
            specific = True
        if row.text_before_attribute:
            add("F04", "the description is not last")
            specific = True
    without_separator = re.sub(r" *= *", " = ", row.line, count=1) if row.described else row.line
    if not specific or _has_spacing_issue(config, row, without_separator):
        add("F02", "spacing is not canonical")


def _has_spacing_issue(config: Config, row: Row, line: str) -> bool:
    if line != line.strip() or "  " in line:
        return True
    for key, value in row.attributes:
        attribute = config.attributes[key]
        if value != markup.canonical_value(attribute, value):
            return True
    return False


def _file_key(config: Config, file_name: str) -> str:
    prefix = f"{config.language}-"
    if file_name.startswith(prefix) and file_name.endswith(config.extension):
        return file_name[len(prefix):-len(config.extension)]
    return file_name


def _short(text: str, limit: int = 48) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
