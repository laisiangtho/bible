"""Mechanical upgrade of rows to markup version 2, and renaming of a keyword.

Two steps bring a row to version 2: a row with a meaning receives the next
free sense number of its keyword, and examples written in the attribute ``e``
move to the example file of the data file. Upgrading a version 2 row changes
nothing.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

from assist.cite import bible, markup, words
from assist.cite.config import CiteError, Config
from assist.cite.store import Data, DataFile, to_text

INLINE = "e"
VERSE = re.compile(r"^\d+\.\d+\.\d+")
Locate = Callable[[str, str, List[str]], Optional[str]]


def _plain(text: str) -> str:
    return " ".join(words.CURLY_APOSTROPHE.sub("'", text).replace("’", "'").split()).casefold()


def bible_locator(config: Config) -> Locate:
    """A function naming the verse, among given references, that contains an example."""
    texts: Dict[str, List[str]] = {}

    def load() -> None:
        for identify in config.raw["bible"]["source"]:
            for book, chapter, verse, text in bible.verses(bible.load(config, identify), identify):
                texts.setdefault(f"{book}.{chapter}.{verse}", []).append(_plain(text))

    def locate(keyword: str, zolai: str, references: List[str]) -> Optional[str]:
        if not texts:
            load()
        fragment = _plain(zolai.replace(markup.PLACEHOLDER, keyword))
        for reference in references:
            if VERSE.match(reference) and any(
                fragment in text for text in texts.get(reference.split("-")[0], [])
            ):
                return reference
        return None

    return locate


def _upgradable(config: Config, row: markup.Row) -> bool:
    keys = [key for key, _ in row.attributes]
    return (
        row.described
        and bool(row.body.strip())
        and all(key in config.attributes or key == INLINE for key in keys)
        and len(set(keys)) == len(keys)
        and "(" not in row.text
        and ")" not in row.text
    )


def upgrade(config: Config, data: Data, locate: Locate) -> Dict[DataFile, List[str]]:
    """New lines of every data file and example file that the upgrade changes or creates."""
    numbers: Dict[str, int] = {}
    for row in data.rows():
        key = markup.row_key(row)
        if key:
            numbers[row.keyword] = max(numbers.get(row.keyword, 0), int(row.values()["i"]))
    reference = config.attributes["r"]
    result: Dict[DataFile, List[str]] = {}
    existing = data.examples_by_file
    for file in data.files:
        if not file.readable:
            raise CiteError(f"cannot read {file.name}; run the check")
        lines: List[str] = []
        moved: List[Tuple[str, str]] = []
        order: Dict[str, int] = {}
        for number, line in enumerate(file.lines, 1):
            if not markup.is_row(line):
                lines.append(line)
                continue
            row = markup.parse(line, file.name, number)
            if not _upgradable(config, row):
                lines.append(line)
                order.setdefault(markup.row_key(row), len(order))
                continue
            values = row.values()
            code = values.get("t", "")
            if "i" not in values and code in config.types and config.has_meaning(code):
                numbers[row.keyword] = numbers.get(row.keyword, 0) + 1
                values["i"] = str(numbers[row.keyword])
            key = markup.sense_key(row.keyword, values.get("i", ""))
            order.setdefault(key, len(order))
            if INLINE in values:
                if "i" not in values:
                    raise CiteError(
                        f"{file.name}:{number}: examples cannot move from a row without a meaning"
                    )
                references = [r for r in markup.split_items(reference, values.get("r", "")) if r]
                used: List[str] = []
                for item in values.pop(INLINE).split(markup.LIST_SEPARATOR):
                    zolai, bar, english = item.partition(markup.TRANSLATION)
                    if not zolai.strip():
                        continue
                    if not bar or not english.strip():
                        raise CiteError(
                            f"{file.name}:{number}: example '{zolai.strip()}' has no translation"
                        )
                    found = locate(row.keyword, zolai, references)
                    if found:
                        used.append(found)
                    moved.append((key, markup.render_example(key, zolai, english, [found] if found else [])))
                left = [r for r in references if r not in used]
                if left:
                    values["r"] = markup.LIST_SEPARATOR.join(left)
                else:
                    values.pop("r", None)
            lines.append(markup.render(config, markup.collapse(row.keyword), values, row.text))
        if lines != file.lines:
            result[file] = lines
        side = existing.get(file.key) or DataFile(
            file.key, config.example_name(file.key), config.example_path(file.key), "example"
        )
        if moved or side.lines:
            comments = [line for line in side.lines if line.startswith(markup.COMMENT)]
            rows = [(markup.parse(line).keyword, line) for line in side.lines if markup.is_row(line)]
            rows.extend(moved)
            position = {key: index for index, key in enumerate(order)}
            rows.sort(key=lambda entry: position.get(entry[0], len(position)))
            new = comments + [line for _, line in rows]
            if new != side.lines:
                result[side] = new
    return result


def sort_key(keyword: str) -> Tuple[str, str]:
    """Order of keywords in a data file: letters first, lowercase before uppercase."""
    return keyword.casefold(), keyword.swapcase()


def _ordered(lines: List[str], position: Dict[str, int]) -> List[str]:
    comments = [line for line in lines if line.startswith(markup.COMMENT)]
    rows = [line for line in lines if markup.is_row(line)]
    rows.sort(key=lambda line: position.get(markup.parse(line).keyword, len(position)))
    return comments + rows


def move(config: Config, data: Data, keys: List[str], target: str) -> Dict[DataFile, List[str]]:
    """New lines of every file when the senses named by ``keys`` move to the data file ``target``.

    A sense moves with its examples and keeps its sense key. The target file
    stays sorted by keyword; a moved row follows the rows its keyword already
    has there.
    """
    if target not in config.files:
        raise CiteError(f"'{target}' is not a listed file; listed: {', '.join(config.files)}")
    wanted = list(dict.fromkeys(keys))
    home: Dict[str, Tuple[DataFile, str]] = {}
    for file in data.files:
        for row in file.rows():
            key = markup.row_key(row)
            if key in wanted:
                home[key] = (file, row.line)
    missing = [key for key in wanted if key not in home]
    if missing:
        raise CiteError(f"no row has the sense key: {', '.join(missing)}")
    goal = next(file for file in data.files if file.key == target)
    moving = [key for key in wanted if home[key][0] is not goal]
    if not moving:
        return {}
    taken = {key: home[key][1] for key in moving}
    lines: Dict[DataFile, List[str]] = {}
    for file in {home[key][0] for key in moving}:
        gone = {taken[key] for key in moving if home[key][0] is file}
        lines[file] = [line for line in file.lines if line not in gone]
    comments = [line for line in goal.lines if not markup.is_row(line)]
    rows = [line for line in goal.lines if markup.is_row(line)] + [taken[key] for key in moving]
    rows.sort(key=lambda line: sort_key(markup.parse(line).keyword))
    lines[goal] = comments + rows

    sides = data.examples_by_file
    carried: List[str] = []
    moved = set(moving)
    for file in data.files:
        side = sides.get(file.key)
        if side is None or file is goal:
            continue
        kept = []
        for line in side.lines:
            if markup.is_row(line) and markup.parse(line).keyword in moved:
                carried.append(line)
            else:
                kept.append(line)
        if kept != side.lines:
            lines[side] = kept
    side = sides.get(target) or DataFile(
        target, config.example_name(target), config.example_path(target), "example"
    )
    if carried or side.lines:
        position: Dict[str, int] = {}
        for line in lines[goal]:
            if markup.is_row(line):
                position.setdefault(markup.row_key(markup.parse(line)), len(position))
        new = _ordered(side.lines + carried, position)
        if new != side.lines:
            lines[side] = new
    return lines


def rename(config: Config, data: Data, old: str, new: str) -> Dict[DataFile, List[str]]:
    """New lines of every file in which the keyword ``old`` becomes ``new``."""
    if not config.keyword.match(new):
        raise CiteError(f"'{new}' is not a valid keyword")
    rows = data.rows()
    if old not in {row.keyword for row in rows}:
        raise CiteError(f"'{old}' is not a keyword of the data")
    taken = {row.values().get("i") for row in rows if row.keyword == new and row.described}
    clash = sorted(
        number for number in (row.values().get("i") for row in rows if row.keyword == old) if number in taken
    )
    if clash:
        raise CiteError(
            f"'{new}' already has sense {', '.join(clash)}; renumber the senses of one keyword first"
        )
    resolving = [key for key, attribute in config.attributes.items() if attribute.resolve]
    result: Dict[DataFile, List[str]] = {}

    def keyed(line: str) -> str:
        row = markup.parse(line)
        parts = markup.split_key(row.keyword)
        if not row.described or not parts or parts[0] != old:
            return line
        return f"{markup.sense_key(new, parts[1])} {line[line.index(markup.SEPARATOR):]}"

    def lexicon(line: str) -> str:
        row = markup.parse(line)
        if not row.described:
            return new if row.keyword == old else line
        if markup.canonical(config, row) is None:
            return line
        values = row.values()
        for key in resolving:
            if key in values:
                items = markup.split_items(config.attributes[key], values[key])
                values[key] = markup.LIST_SEPARATOR.join(new if item == old else item for item in items)
        for key, attribute in config.attributes.items():
            if attribute.xref and key in values:
                values[key] = values[key].replace(f"<{old}>", f"<{new}>")
        text = row.text.replace(f"<{old}>", f"<{new}>")
        keyword = new if row.keyword == old else markup.collapse(row.keyword)
        changed = markup.render(config, keyword, values, text)
        return changed if changed != markup.canonical(config, row) else line

    def link(line: str) -> str:
        row = markup.parse(line)
        keys = markup.link_keys(row)
        renamed = [
            markup.sense_key(new, parts[1]) if parts and parts[0] == old else key
            for key, parts in ((key, markup.split_key(key)) for key in keys)
        ]
        if renamed == keys or markup.canonical_link(config, row) is None:
            return line
        return markup.render_link(config, markup.collapse(row.keyword), renamed, row.values())

    for file in data.every_file():
        change = {"lexicon": lexicon, "link": link}.get(file.kind, keyed)
        lines = [change(line) if markup.is_row(line) else line for line in file.lines]
        if lines != file.lines:
            result[file] = lines
    return result


def texts(changes: Dict[DataFile, List[str]]) -> Dict[DataFile, str]:
    return {file: to_text(lines) for file, lines in changes.items()}
