"""Reading and writing of the table files.

A table is known by its stored name: ``word``, ``gloss/eng``, ``link/eng``.
Rows are tuples of text in the order of the configured columns.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from assist.cite.config import ID_KINDS, LANGUAGE, CiteError, Config, Table

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
            if _location(config, table, name).exists():
                names.append(name)
    return names


def _location(config: Config, table: Table, name: str) -> Path:
    """Folder of a sharded table, file of any other."""
    return config.directory / name if table.sharded else config.directory / f"{name}{config.extension}"


def shard_of(config: Config, value: str) -> int:
    """Number of the shard that holds rows whose first column is this id."""
    for kind in ID_KINDS:
        if value.startswith(config.prefix[kind]):
            number = config.id_number(kind, value)
            if number is not None:
                return number // config.block[kind]
    raise CiteError(f"'{value}' is not an id: {', '.join(config.prefix.values())} followed by a number")


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
    """Text of every file of a table, rows sorted."""
    table = definition(config, name)
    header = "\t".join(table.columns)
    ordered = sorted((tuple(row) for row in rows), key=sort_key)
    for first, second in zip(ordered, ordered[1:]):
        if sort_key(first) == sort_key(second):
            raise CiteError(f"table {name}: the row {first!r} occurs twice")
    location = _location(config, table, name)
    if not table.sharded:
        return {location: "\n".join([header] + [_line(table, name, row) for row in ordered]) + "\n"}
    shards: Dict[int, List[str]] = {}
    for row in ordered:
        shards.setdefault(shard_of(config, row[0]), []).append(_line(table, name, row))
    return {
        location / f"{config.shard.format(block=shard)}{config.extension}": "\n".join([header] + lines) + "\n"
        for shard, lines in sorted(shards.items())
    }


def _existing(config: Config, name: str) -> List[Path]:
    table = definition(config, name)
    location = _location(config, table, name)
    if not table.sharded:
        return [location] if location.is_file() else []
    return sorted(location.glob(f"*{config.extension}")) if location.is_dir() else []


def changes(config: Config, tables: Tables) -> Tuple[Dict[Path, str], List[Path]]:
    """Files whose text differs from the stored one, and stored files that hold no row any more."""
    write: Dict[Path, str] = {}
    remove: List[Path] = []
    for name, rows in tables.items():
        files = render(config, name, rows)
        for path, text in files.items():
            if not path.is_file() or path.read_bytes() != text.encode("utf-8"):
                write[path] = text
        remove.extend(path for path in _existing(config, name) if path not in files)
    return write, remove


def write_all(config: Config, tables: Tables) -> Tuple[List[Path], List[Path]]:
    """Store the tables. Only files that differ are written. Returns written and removed files."""
    write, remove = changes(config, tables)
    for path, text in write.items():
        write_text(path, text)
    for path in remove:
        path.unlink()
    return list(write), remove


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
    table = definition(config, name)
    location = _location(config, table, name)
    if not table.sharded:
        if not location.is_file():
            raise CiteError(f"{location.relative_to(config.directory)}: the table file is missing")
        return _read_file(config, location, table, problems)
    if not location.is_dir():
        raise CiteError(f"{location.relative_to(config.directory)}: the table folder is missing")
    rows: List[Row] = []
    for path in sorted(location.iterdir()):
        where = path.relative_to(config.directory)
        if path.suffix != config.extension or not path.is_file():
            raise CiteError(f"{where}: not a file of the table {name}")
        found = _read_file(config, path, table, problems)
        # Every row is placed by the full check; any other reader trusts the first and the last.
        firsts = {row[0] for row in found} if problems is not None else {row[0] for row in found[:1] + found[-1:]}
        for first in firsts:
            expected = f"{config.shard.format(block=shard_of(config, first))}{config.extension}"
            if path.name != expected:
                raise CiteError(f"{where}: the row of {first} belongs in {expected}")
        rows.extend(found)
    return rows


def _reject_unknown_languages(config: Config) -> None:
    """A folder or file named by a language code that the configuration does not list is an error."""
    for table in config.tables.values():
        if not table.per_language:
            continue
        folder = config.directory / table.path.split(LANGUAGE)[0]
        known = {table.instance(language).rsplit("/", 1)[-1] for language in config.languages}
        for path in sorted(folder.iterdir()) if folder.is_dir() else []:
            if (path.name if table.sharded else path.stem) not in known:
                raise CiteError(f"{path.relative_to(config.directory)}: not a language of the configuration")


def read_all(config: Config, problems: Optional[List[str]] = None) -> Tables:
    """Every stored table by its stored name."""
    _reject_unknown_languages(config)
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
