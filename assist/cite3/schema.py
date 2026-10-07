"""Tables, columns and codes of cite format 3.

The definitions live here until the configuration of format 3 replaces the
configuration of format 2; from then on they are read from that file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Tuple

from assist.cite.config import CiteError

EXTENSION = ".tsv"
SHARD_DIGITS = 4
LIST_SEPARATOR = "/"

ID = re.compile(r"^([wse])([1-9][0-9]*)$")
PREFIX = {"word": "w", "sense": "s", "example": "e"}
BLOCK = {"w": 5000, "s": 2000, "e": 5000}

SENSE_STATUS = {
    0: "retired",
    1: "low confidence",
    2: "draft",
    3: "reviewed",
    4: "confirmed",
    5: "disputed",
}
WORD_STATUS = {0: "retired", 1: "standard", 2: "variant", 3: "nonstandard"}
RELATION_KINDS = ("s", "a", "b", "j", "v", "see")
SETS = ("core", "bible", "name")


@dataclass(frozen=True)
class Table:
    """One table: where it is stored and what a row holds.

    ``sharded`` tables are split by the id block of the first column; the
    others are one file.
    """

    name: str
    columns: Tuple[str, ...]
    sharded: bool = True


TABLES: Dict[str, Table] = {
    table.name: table
    for table in (
        Table("word", ("id", "spelling", "status")),
        Table(
            "sense",
            ("id", "word", "number", "type", "category", "field", "set", "status", "origin", "source", "note"),
        ),
        Table("gloss/eng", ("sense", "terms", "definition", "text")),
        Table("relation", ("from", "kind", "to", "order")),
        Table("example", ("id", "source", "text")),
        Table("usage", ("example", "sense", "start", "length")),
        Table("translation/eng", ("example", "text")),
        Table("link/eng", ("term", "senses", "source", "status", "note"), sharded=False),
        Table("note/open", ("kind", "subject", "source", "text"), sharded=False),
        Table("sequence", ("table", "last"), sharded=False),
    )
}


def split_id(value: str) -> Tuple[str, int]:
    """Prefix and number of an id; an error for anything else."""
    match = ID.match(value)
    if not match:
        raise CiteError(f"'{value}' is not an id: w, s or e followed by a number")
    return match.group(1), int(match.group(2))


def make_id(prefix: str, number: int) -> str:
    return f"{prefix}{number}"


def shard_of(value: str) -> int:
    """Number of the shard that holds rows whose first column is this id."""
    prefix, number = split_id(value)
    return number // BLOCK[prefix]


def id_order(value: str) -> Tuple[str, int]:
    """Sort key of an id: by kind, then by number."""
    return split_id(value)
