"""Proof that the tables of format 3 hold everything the format 2 files hold.

The tables are rendered back to format 2 rows and compared, as multisets,
with the rows of the files. The only differences allowed are the ones named
in ``expected``: the status in ``q`` is written out in its fixed form.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from assist.cite import markup
from assist.cite.config import CiteError, Config
from assist.cite.store import Data
from assist.cite3 import convert, legacy, render

SAMPLE = 5


@dataclass
class Part:
    """Comparison of one kind of row."""

    name: str
    rows: int
    missing: List[str] = field(default_factory=list)
    extra: List[str] = field(default_factory=list)

    @property
    def equal(self) -> bool:
        return not self.missing and not self.extra


@dataclass
class Report:
    parts: List[Part]
    expected: Dict[str, int]

    @property
    def equal(self) -> bool:
        return all(part.equal for part in self.parts)


def _compare(name: str, original: Sequence[str], rebuilt: Sequence[str]) -> Part:
    before, after = Counter(original), Counter(rebuilt)
    return Part(name, len(original), sorted((before - after).elements()), sorted((after - before).elements()))


def _with_fixed_q(config: Config, row: markup.Row, expected: Dict[str, int], link: bool = False) -> str:
    """The row as format 3 can return it: its status written in the fixed form."""
    values = dict(row.values())
    q = values.get("q", "")
    fixed = legacy.write_q(*legacy.read_q(q))
    if not q:
        expected["rows without q, now draft"] += 1
    elif fixed != markup.collapse(q):
        expected["q that did not start with draft, now a remark of a draft"] += 1
    values["q"] = fixed
    if link:
        return markup.render_link(config, row.keyword, markup.link_keys(row), {k: values[k] for k in ("r", "q") if k in values})
    return markup.render(config, row.keyword, values, row.text)


def compare(
    config: Config, data: Data, tables: render.Tables, notes: Optional[List[convert.Note]] = None
) -> Report:
    """Compare the format 2 files with the tables."""
    expected: Dict[str, int] = Counter()
    lexicon: List[str] = []
    for row in data.rows():
        if not row.described:
            lexicon.append(row.keyword)
        elif row.values().get("t") == "see":
            canonical = markup.canonical(config, row)
            if canonical is None:
                raise CiteError(f"{row.file}:{row.number}: the row has no canonical form")
            lexicon.append(canonical)
        else:
            lexicon.append(_with_fixed_q(config, row, expected))
    examples = [row.line for row in data.example_rows() if row.described]
    links = [_with_fixed_q(config, row, expected, link=True) for row in data.link_rows() if row.described]
    noted = []
    for kind, _, subject, source, text in convert.read_notes(config.directory) if notes is None else notes:
        parts = [subject] + ([source] if source else []) + ([text] if text else [])
        noted.append(f"{kind}: {convert.NOTE_SEPARATOR.join(parts)}")
    parts = [
        _compare("lexicon rows", lexicon, render.lexicon_lines(config, tables)),
        _compare("example rows", examples, render.example_lines(tables)),
        _compare("link rows", links, render.link_lines(config, tables)),
        _compare("notes", noted, render.note_lines(tables)),
    ]
    return Report(parts, dict(expected))


def text(report: Report) -> List[str]:
    lines: List[str] = []
    for part in report.parts:
        state = "equal" if part.equal else f"{len(part.missing)} lost, {len(part.extra)} not in the files"
        lines.append(f"{part.name}: {part.rows} in the files, {state}")
        for label, rows in (("lost", part.missing), ("not in the files", part.extra)):
            for row in rows[:SAMPLE]:
                lines.append(f"  {label}: {row}")
    for label, count in sorted(report.expected.items()):
        lines.append(f"expected difference: {count} {label}")
    return lines
