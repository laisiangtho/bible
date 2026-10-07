"""Shared reading of format 2 values: status in q, the placeholder of an example."""

from __future__ import annotations

from typing import List, Tuple

from assist.cite import markup
from assist.cite.config import CiteError

LOW = "draft, low confidence"
DRAFT = "draft"
STATUS_LOW = 1
STATUS_DRAFT = 2
Q_TEXT = {STATUS_LOW: LOW, STATUS_DRAFT: DRAFT}


def read_q(value: str) -> Tuple[int, str]:
    """Status and remark of a format 2 ``q``. A row without ``q`` is a draft."""
    value = markup.collapse(value)
    for status, text in ((STATUS_LOW, LOW), (STATUS_DRAFT, DRAFT)):
        if value == text:
            return status, ""
        if value.startswith(text + ", "):
            return status, value[len(text) + 2:]
    return STATUS_DRAFT, value


def write_q(status: int, note: str) -> str:
    """The format 2 ``q`` of a status and remark."""
    if status not in Q_TEXT:
        raise CiteError(f"status {status} has no format 2 form")
    return f"{Q_TEXT[status]}, {note}" if note else Q_TEXT[status]


def fill(zolai: str, keyword: str) -> Tuple[str, List[int], int]:
    """Full text of an example, the word positions of the keyword, and its length in words.

    Positions count the words of the full text from 1. A position is given
    once for every placeholder in that word, as in ``pau ~-~``.
    """
    length = len(keyword.split(" "))
    starts: List[int] = []
    position = 1
    for token in zolai.split(" "):
        count = token.count(markup.PLACEHOLDER)
        starts.extend([position] * count)
        position += length if count else 1
    return zolai.replace(markup.PLACEHOLDER, keyword), starts, length


def blank(text: str, keyword: str, starts: List[int], length: int) -> str:
    """The example with the keyword at each position replaced by the placeholder."""
    tokens = text.split(" ")
    for start in sorted(set(starts), reverse=True):
        span = " ".join(tokens[start - 1:start - 1 + length])
        times = starts.count(start)
        if span.count(keyword) < times:
            raise CiteError(f"'{keyword}' is not {times} times at word {start} of the example '{text}'")
        tokens[start - 1:start - 1 + length] = [span.replace(keyword, markup.PLACEHOLDER, times)]
    return " ".join(tokens)
