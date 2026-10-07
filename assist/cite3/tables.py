"""Reading and writing of the table files."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from assist.cite import store
from assist.cite.config import CiteError
from assist.cite3 import schema

Row = Tuple[str, ...]
FORBIDDEN = ("\t", "\n", "\r")


def _line(table: schema.Table, row: Sequence[str]) -> str:
    if len(row) != len(table.columns):
        raise CiteError(f"table {table.name}: a row has {len(row)} values, {len(table.columns)} expected: {row!r}")
    for column, value in zip(table.columns, row):
        if not isinstance(value, str):
            raise CiteError(f"table {table.name}, column {column}: {value!r} is not text")
        if any(mark in value for mark in FORBIDDEN):
            raise CiteError(f"table {table.name}, column {column}: a tab or line break in {value!r}")
    return "\t".join(row)


def _sort_key(row: Sequence[str]) -> Tuple:
    """Rows sort by their columns; an id sorts by its number, a number by its value."""
    key = []
    for value in row:
        match = schema.ID.match(value)
        if match:
            key.append((0, match.group(1), int(match.group(2)), ""))
        elif value.isdigit():
            key.append((1, "", int(value), ""))
        else:
            key.append((2, "", 0, value))
    return tuple(key)


def shard_path(root: Path, table: schema.Table, shard: int) -> Path:
    return root / table.name / f"{shard:0{schema.SHARD_DIGITS}d}{schema.EXTENSION}"


def file_path(root: Path, table: schema.Table) -> Path:
    return root / f"{table.name}{schema.EXTENSION}"


def write(root: Path, name: str, rows: Iterable[Sequence[str]]) -> List[Path]:
    """Write every row of a table, sorted, replacing the files of that table."""
    table = schema.TABLES[name]
    header = "\t".join(table.columns)
    ordered = sorted((tuple(row) for row in rows), key=_sort_key)
    for first, second in zip(ordered, ordered[1:]):
        if first == second:
            raise CiteError(f"table {name}: the row {first!r} occurs twice")
    written: List[Path] = []
    if not table.sharded:
        path = file_path(root, table)
        store.write_text(path, "\n".join([header] + [_line(table, row) for row in ordered]) + "\n")
        return [path]
    shards: Dict[int, List[str]] = {}
    for row in ordered:
        shards.setdefault(schema.shard_of(row[0]), []).append(_line(table, row))
    folder = root / table.name
    if folder.is_dir():
        for stale in folder.glob(f"*{schema.EXTENSION}"):
            stale.unlink()
    for shard in sorted(shards):
        path = shard_path(root, table, shard)
        store.write_text(path, "\n".join([header] + shards[shard]) + "\n")
        written.append(path)
    return written


def _read_file(path: Path, table: schema.Table) -> List[Row]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise CiteError(f"{path}: not UTF-8: {error}") from error
    if "\r" in text:
        raise CiteError(f"{path}: carriage return")
    if not text.endswith("\n"):
        raise CiteError(f"{path}: the file does not end with a newline")
    lines = text[:-1].split("\n")
    if lines[0].split("\t") != list(table.columns):
        raise CiteError(f"{path}: the header is '{lines[0]}', expected '{' '.join(table.columns)}'")
    rows: List[Row] = []
    for number, line in enumerate(lines[1:], 2):
        row = tuple(line.split("\t"))
        if len(row) != len(table.columns):
            raise CiteError(f"{path}:{number}: {len(row)} values, {len(table.columns)} expected")
        rows.append(row)
    return rows


def read(root: Path, name: str) -> List[Row]:
    """Every row of a table, in stored order. A sharded row in the wrong file is an error."""
    table = schema.TABLES[name]
    if not table.sharded:
        path = file_path(root, table)
        if not path.is_file():
            raise CiteError(f"{path}: the table file is missing")
        return _read_file(path, table)
    folder = root / table.name
    if not folder.is_dir():
        raise CiteError(f"{folder}: the table folder is missing")
    rows: List[Row] = []
    for path in sorted(folder.glob(f"*{schema.EXTENSION}")):
        if not (path.stem.isdigit() and len(path.stem) == schema.SHARD_DIGITS):
            raise CiteError(f"{path}: a shard is named by {schema.SHARD_DIGITS} digits")
        for row in _read_file(path, table):
            if schema.shard_of(row[0]) != int(path.stem):
                raise CiteError(f"{path}: the row of {row[0]} belongs in shard {schema.shard_of(row[0])}")
            rows.append(row)
    return rows


def read_all(root: Path) -> Dict[str, List[Row]]:
    return {name: read(root, name) for name in schema.TABLES}


def write_all(root: Path, tables: Dict[str, List[Sequence[str]]]) -> List[Path]:
    missing = sorted(set(schema.TABLES) - set(tables))
    if missing:
        raise CiteError(f"no rows given for the tables: {', '.join(missing)}")
    written: List[Path] = []
    for name in schema.TABLES:
        written.extend(write(root, name, tables[name]))
    return written
