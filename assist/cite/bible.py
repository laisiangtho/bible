"""Read-only access to the Bible translations under ``json/``."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterator, Tuple

from assist.cite.config import CiteError, Config

Verse = Tuple[int, int, int, str]


def load(config: Config, identify: str) -> Dict[str, Any]:
    path = config.bible_path(identify)
    if not path.is_file():
        raise CiteError(f"translation '{identify}' not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CiteError(f"translation '{identify}' is not valid JSON: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("book"), dict):
        raise CiteError(f"translation '{identify}' has no 'book' object")
    return data


def _numeric(mapping: Dict[str, Any], where: str) -> Iterator[Tuple[int, Any]]:
    try:
        keys = sorted(mapping, key=int)
    except ValueError as error:
        raise CiteError(f"{where}: an id is not a number: {error}") from error
    for key in keys:
        yield int(key), mapping[key]


def verses(data: Dict[str, Any], identify: str = "") -> Iterator[Verse]:
    """Every verse as (book, chapter, verse, text), in canonical order."""
    for book_id, book in _numeric(data["book"], f"translation '{identify}'"):
        where = f"translation '{identify}' book {book_id}"
        for chapter_id, chapter in _numeric(book.get("chapter", {}), where):
            for verse_id, verse in _numeric(chapter.get("verse", {}), f"{where} chapter {chapter_id}"):
                yield book_id, chapter_id, verse_id, verse.get("text", "")


def verse_text(data: Dict[str, Any], book: int, chapter: int, verse: int) -> str:
    try:
        return data["book"][str(book)]["chapter"][str(chapter)]["verse"][str(verse)].get("text", "")
    except KeyError:
        return ""


def book_name(data: Dict[str, Any], book: int) -> str:
    return data["book"].get(str(book), {}).get("info", {}).get("name", str(book))


def language(data: Dict[str, Any]) -> str:
    return data.get("info", {}).get("language", {}).get("name", "")
