"""One-time conversion of rows written before markup version 1.

Only mechanical steps are taken; see ``Rows written before version 1`` in
``cite/Markup.md``. A row that needs a decision is left for an editor and is
reported by the check. Converting a version 1 row changes nothing.
"""

from __future__ import annotations

from assist.cite import markup
from assist.cite.config import Config

UNSURE = "??"


def convert_line(config: Config, line: str) -> str:
    if not markup.is_row(line):
        return line
    row = markup.parse(line)
    if not row.described:
        return markup.canonical(config, row) or line
    keys = [key for key, _ in row.attributes]
    if (
        not row.body.strip()
        or any(key not in config.attributes for key in keys)
        or len(set(keys)) != len(keys)
    ):
        return line

    values = row.values()
    text = row.text
    old_type = values.get("t", "")
    if old_type in config.alias:
        target = config.alias[old_type]
        values["t"] = target["t"]
        if "c" in target and "c" not in values:
            values["c"] = target["c"]
    if text.startswith("(") and text.endswith(")") and text.count("(") == 1 and text.count(")") == 1:
        text = text[1:-1].strip()
    if text == UNSURE and "q" not in values:
        values["q"] = "?"
        text = ""
    plain = "(" not in text and ")" not in text
    if (
        text
        and plain
        and markup.PLACEHOLDER not in text
        and "w" not in values
        and "d" not in values
        and config.has_meaning(values.get("t", ""))
    ):
        values["d"] = text
        text = ""
    return markup.render(config, " ".join(row.keyword.split()), values, text)
