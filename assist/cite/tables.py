"""Reading and writing of the table files.

A table is known by its stored name: ``word``, ``lang/eng/gloss``. Every
table is one file.
Rows are tuples of text in the order of the configured columns.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from assist.cite.config import CiteError, Config, Table

Row = Tuple[str, ...]
Tables = Dict[str, List[Row]]
FORBIDDEN = ("\t", "\n", "\r")


def definition(config: Config, name: str) -> Table:
    """The configured table behind a stored name."""
    for table in config.tables.values():
        if table.per_language:
            for language in config.languages:
                if table.instance(language) == name:
                    return table
        elif table.path == name:
            return table
    raise CiteError(f"'{name}' is not a table of the configuration")


def stored(config: Config) -> List[str]:
    """Stored names of every table: all fixed tables, and the per-language tables that exist."""
    names: List[str] = []
    for table in config.tables.values():
        if not table.per_language:
            names.append(table.path)
            continue
        for language in config.languages:
            name = table.instance(language)
            if location(config, name).exists():
                names.append(name)
    return names


def location(config: Config, name: str) -> Path:
    """File of a table by its stored name."""
    return config.directory / f"{name}{config.extension}"


def sort_key(row: Sequence[str]) -> Tuple:
    """Rows sort by their columns; an id sorts by its number, a number by its value."""
    key = []
    for value in row:
        tail = value[1:]
        if value.isascii() and value.isdigit():
            key.append((1, "", int(value), ""))
        elif tail.isdigit() and value.isascii() and value[0].islower() and tail[0] != "0":
            key.append((0, value[0], int(tail), ""))
        else:
            key.append((2, "", 0, value))
    return tuple(key)


def _line(table: Table, name: str, row: Sequence[str]) -> str:
    if len(row) != len(table.columns):
        raise CiteError(f"table {name}: a row has {len(row)} values, {len(table.columns)} expected: {row!r}")
    for column, value in zip(table.columns, row):
        if not isinstance(value, str):
            raise CiteError(f"table {name}, column {column}: {value!r} is not text")
        if any(mark in value for mark in FORBIDDEN):
            raise CiteError(f"table {name}, column {column}: a tab or line break in {value!r}")
    return "\t".join(row)


def render(config: Config, name: str, rows: Iterable[Sequence[str]]) -> Dict[Path, str]:
    """Text of the file of a table, rows sorted."""
    table = definition(config, name)
    header = "\t".join(table.columns)
    ordered = sorted((tuple(row) for row in rows), key=sort_key)
    for first, second in zip(ordered, ordered[1:]):
        if sort_key(first) == sort_key(second):
            raise CiteError(f"table {name}: the row {first!r} occurs twice")
    return {location(config, name): "\n".join([header] + [_line(table, name, row) for row in ordered]) + "\n"}


def changes(config: Config, tables: Tables) -> Dict[Path, str]:
    """Files whose text differs from the stored one."""
    write: Dict[Path, str] = {}
    for name, rows in tables.items():
        for path, text in render(config, name, rows).items():
            if not path.is_file() or path.read_bytes() != text.encode("utf-8"):
                write[path] = text
    return write


def write_all(config: Config, tables: Tables) -> List[Path]:
    """Store the tables. Only files that differ are written. Returns the written files."""
    write = changes(config, tables)
    for path, text in write.items():
        write_text(path, text)
    return list(write)


def _read_file(config: Config, path: Path, table: Table, problems: Optional[List[str]]) -> List[Row]:
    where = path.relative_to(config.directory)
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise CiteError(f"{where}: not UTF-8: {error}") from error
    if "\r" in text:
        raise CiteError(f"{where}: carriage return")
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise CiteError(f"{where}: the file ends with exactly one newline")
    lines = text[:-1].split("\n")
    if lines[0].split("\t") != list(table.columns):
        raise CiteError(f"{where}: the header is '{lines[0]}', expected '{' '.join(table.columns)}'")
    rows: List[Row] = []
    for number, line in enumerate(lines[1:], 2):
        row = tuple(line.split("\t"))
        if len(row) != len(table.columns):
            raise CiteError(f"{where}:{number}: {len(row)} values, {len(table.columns)} expected")
        rows.append(row)
    if problems is not None:
        keys = [sort_key(row) for row in rows]
        for number, (first, second) in enumerate(zip(keys, keys[1:]), 3):
            if first >= second:
                problems.append(f"{where}:{number}: the row is not after the row above; rows are sorted and unique")
                break
    return rows


def read(config: Config, name: str, problems: Optional[List[str]] = None) -> List[Row]:
    """Every row of a table, in stored order.

    A file that cannot be read as a table raises CiteError. The order of the
    rows is verified only when ``problems`` is given to collect the messages.
    """
    path = location(config, name)
    if not path.is_file():
        raise CiteError(f"{path.relative_to(config.directory)}: the table file is missing")
    return _read_file(config, path, definition(config, name), problems)


def _reject_unknown_files(config: Config) -> None:
    """In the language folder, only folders of listed languages holding files of per-language tables."""
    folder = config.directory / config.language_folder
    if not folder.exists():
        return
    if not folder.is_dir():
        raise CiteError(f"{config.language_folder}: not a folder")
    known = {
        table.instance(language): table for table in config.tables.values() if table.per_language
        for language in config.languages
    }
    for language in sorted(folder.iterdir()):
        where = language.relative_to(config.directory)
        if not language.is_dir() or language.name not in config.languages:
            raise CiteError(f"{where}: not a language of the configuration")
        for path in sorted(language.iterdir()):
            name = str(path.relative_to(config.directory).with_suffix(""))
            if path.suffix != config.extension or name not in known:
                raise CiteError(f"{path.relative_to(config.directory)}: not a table of the configuration")


def read_all(config: Config, problems: Optional[List[str]] = None) -> Tables:
    """Every stored table by its stored name."""
    _reject_unknown_files(config)
    return {name: read(config, name, problems) for name in stored(config)}


def write_text(path: Path, text: str) -> None:
    """Replace a file in one step, so an interrupted run leaves no partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".part")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
