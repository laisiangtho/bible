"""Loading and validation of ``cite/configuration.json``."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "cite" / "configuration.json"
SUPPORTED_VERSION = 3

REQUIRED_KEYS = (
    "version", "language", "format", "id", "table", "status", "relation", "set", "note",
    "keyword", "markup", "attribute", "reference", "type", "category", "field", "source",
    "bible", "rule",
)
ID_KINDS = ("word", "sense", "example")
TABLES = (
    "word", "sense", "gloss", "relation", "example", "usage", "translation", "link", "note", "sequence",
)
ATTRIBUTES = ("i", "t", "c", "f", "w", "d", "s", "a", "b", "j", "v", "o", "r", "q", "e")
RELATIONS = ("s", "a", "b", "j", "v", "see")
SENSE_STATUS = ("retired", "low", "draft", "reviewed", "confirmed", "disputed")
WORD_STATUS = ("retired", "standard", "variant", "nonstandard")
SOURCE_KEYS = ("name", "description", "owner", "credit", "license", "permission", "url")
LANGUAGE = "{language}"


class CiteError(Exception):
    """A condition that stops a command: bad configuration, bad input, broken data."""


@dataclass(frozen=True)
class Table:
    """One table of the configuration.

    ``path`` is relative to the cite directory and has no extension. A table
    whose path holds ``{language}`` exists once per language.
    """

    name: str
    path: str
    columns: Tuple[str, ...]
    sharded: bool

    @property
    def per_language(self) -> bool:
        return LANGUAGE in self.path

    def instance(self, language: str = "") -> str:
        """Name of the table as stored: the path with the language filled in."""
        if self.per_language and not language:
            raise CiteError(f"table {self.name}: a language code is needed")
        return self.path.replace(LANGUAGE, language)


@dataclass(frozen=True)
class Attribute:
    key: str
    name: str
    description: str
    is_list: bool


@dataclass(frozen=True)
class Config:
    root: Path
    directory: Path
    raw: Dict[str, Any]
    extension: str
    list_separator: str
    shard: str
    inbox: Path
    cache: Path
    markup_extension: str
    keyword: Pattern[str]
    reference: Pattern[str]
    tables: Dict[str, Table]
    languages: Tuple[str, ...]
    prefix: Dict[str, str]
    block: Dict[str, int]
    sense_status: Dict[str, str]
    word_status: Dict[str, str]
    relations: Dict[str, Dict[str, Any]]
    sets: Dict[str, Dict[str, Any]]
    notes: Dict[str, Dict[str, Any]]
    types: Dict[str, Dict[str, Any]]
    categories: Dict[str, Dict[str, Any]]
    fields: Dict[str, Dict[str, Any]]
    sources: Dict[str, Dict[str, Any]]
    attributes: Dict[str, Attribute]
    rules: Dict[str, Dict[str, str]]

    def has_meaning(self, type_code: str) -> bool:
        """False for the types whose rows carry no term or definition."""
        return bool(self.types.get(type_code, {}).get("meaning", True))

    def status_code(self, kind: str, name: str) -> str:
        """Code of a status name; ``kind`` is sense or word."""
        table = self.sense_status if kind == "sense" else self.word_status
        for code, known in table.items():
            if known == name:
                return code
        raise CiteError(f"'{name}' is not a {kind} status; known: {', '.join(table.values())}")

    def bible_path(self, identify: str) -> Path:
        return self.root / self.raw["bible"]["path"].format(identify=identify)

    def valid_reference(self, part: str) -> bool:
        """True for a Bible verse or a listed source with an optional locator."""
        match = self.reference.match(part)
        if not match:
            return False
        source = match.groupdict().get("source")
        return source is None or source in self.sources

    def id_number(self, kind: str, value: str) -> Optional[int]:
        """Number of an id of the kind; None when the value is not such an id."""
        prefix = self.prefix[kind]
        number = value[len(prefix):]
        if value.startswith(prefix) and number.isascii() and number.isdigit() and number[0] != "0":
            return int(number)
        return None

    def id_kind(self, value: str) -> str:
        """Kind of an id: word, sense or example; empty when the value is not an id."""
        for kind in ID_KINDS:
            if self.id_number(kind, value) is not None:
                return kind
        return ""


def _reject_duplicates(pairs: List[Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CiteError(f"configuration: key '{key}' occurs twice in one object")
        result[key] = value
    return result


def _need(mapping: Any, key: str, kind: type, where: str) -> Any:
    if not isinstance(mapping, dict) or key not in mapping:
        raise CiteError(f"configuration: {where}: missing '{key}'")
    value = mapping[key]
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise CiteError(f"configuration: {where}: '{key}' is not of type {kind.__name__}")
    return value


def _compile(pattern: str, where: str) -> Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as error:
        raise CiteError(f"configuration: {where}: invalid pattern: {error}") from error


def _named(raw: Dict[str, Any], key: str) -> Dict[str, Dict[str, Any]]:
    """A closed list: every entry has a name and a description."""
    table = _need(raw, key, dict, "top level")
    for code, entry in table.items():
        _need(entry, "name", str, f"{key} '{code}'")
        _need(entry, "description", str, f"{key} '{code}'")
    return table


def _status(raw: Dict[str, Any], kind: str, names: Tuple[str, ...]) -> Dict[str, str]:
    entries = _need(raw["status"], kind, dict, "status")
    result = {code: _need(entry, "name", str, f"status {kind} '{code}'") for code, entry in entries.items()}
    for code, entry in entries.items():
        _need(entry, "description", str, f"status {kind} '{code}'")
        if not re.fullmatch(r"[0-9]", code):
            raise CiteError(f"configuration: status {kind}: the code '{code}' is not one digit")
    if sorted(result.values()) != sorted(names):
        raise CiteError(f"configuration: status {kind}: the tooling needs exactly the names {', '.join(names)}")
    return result


def load(path: Optional[Path] = None) -> Config:
    """Read and validate the configuration. Any defect raises CiteError."""
    path = path or CONFIG_PATH
    if not path.is_file():
        raise CiteError(f"configuration not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CiteError(f"configuration: {path.name} is not valid JSON: {error}") from error
    if not isinstance(raw, dict):
        raise CiteError("configuration: the top level is not an object")
    for key in REQUIRED_KEYS:
        if key not in raw:
            raise CiteError(f"configuration: missing '{key}'")
    if raw["version"] != SUPPORTED_VERSION:
        raise CiteError(
            f"configuration: version {raw['version']!r} is not supported (supported: {SUPPORTED_VERSION})"
        )

    form = _need(raw, "format", dict, "top level")
    for key, expected in (("encoding", "utf-8"), ("newline", "\n"), ("separator", "\t")):
        if _need(form, key, str, "format") != expected:
            raise CiteError(f"configuration: format.{key}: the tooling supports {expected!r} only")
    extension = _need(form, "extension", str, "format")
    separator = _need(form, "list", str, "format")
    shard = _need(form, "shard", str, "format")
    try:
        shard.format(block=0)
    except (KeyError, IndexError, ValueError) as error:
        raise CiteError(f"configuration: format.shard is not a template with {{block}}: {error}") from error
    if len(separator) != 1 or not extension.startswith("."):
        raise CiteError("configuration: format: 'list' is one character and 'extension' starts with a dot")
    folders = {}
    for key in ("inbox", "cache"):
        folder = Path(_need(form, key, str, "format"))
        if folder.is_absolute() or ".." in folder.parts or not folder.parts:
            raise CiteError(f"configuration: format.{key} is a folder inside the cite directory")
        folders[key] = path.parent / folder

    languages = tuple(_need(_need(raw, "language", dict, "top level"), "gloss", dict, "language"))
    for code in languages:
        if not re.fullmatch(r"[a-z]{3}", code):
            raise CiteError(f"configuration: language code '{code}' is not three lowercase letters")

    prefix: Dict[str, str] = {}
    block: Dict[str, int] = {}
    for kind in ID_KINDS:
        entry = _need(raw["id"], kind, dict, "id")
        prefix[kind] = _need(entry, "prefix", str, f"id {kind}")
        block[kind] = _need(entry, "block", int, f"id {kind}")
        if not re.fullmatch(r"[a-z]", prefix[kind]) or block[kind] < 1:
            raise CiteError(f"configuration: id {kind}: a prefix is one lowercase letter, a block is positive")
    if len(set(prefix.values())) != len(prefix):
        raise CiteError("configuration: id: two kinds share one prefix")

    tables: Dict[str, Table] = {}
    for name in TABLES:
        entry = _need(raw["table"], name, dict, "table")
        columns = tuple(_need(entry, "columns", dict, f"table {name}"))
        tables[name] = Table(
            name, _need(entry, "path", str, f"table {name}"), columns, _need(entry, "shard", bool, f"table {name}")
        )
        _need(entry, "description", str, f"table {name}")
        if not columns:
            raise CiteError(f"configuration: table {name} has no column")
    unknown = sorted(set(raw["table"]) - set(TABLES))
    if unknown:
        raise CiteError(f"configuration: table: unknown table {', '.join(unknown)}")
    paths = [table.path for table in tables.values()]
    if len(set(paths)) != len(paths):
        raise CiteError("configuration: table: two tables share one path")

    relations = _named(raw, "relation")
    if sorted(relations) != sorted(RELATIONS):
        raise CiteError(f"configuration: relation: the tooling needs exactly the kinds {', '.join(RELATIONS)}")
    types = _named(raw, "type")
    for code in ("see", "todo", "name"):
        if code not in types:
            raise CiteError(f"configuration: type '{code}' is required by the tooling")
    sets = _named(raw, "set")
    for code in ("core", "bible"):
        if code not in sets:
            raise CiteError(f"configuration: set '{code}' is required by the tooling")
    sources = _named(raw, "source")
    for code, entry in sources.items():
        if not re.fullmatch(r"[a-z][a-z0-9]*", code):
            raise CiteError(f"configuration: source code '{code}' is not lowercase letters and digits")
        for key, value in entry.items():
            if key not in SOURCE_KEYS:
                raise CiteError(
                    f"configuration: source '{code}': unknown key '{key}'; allowed: {', '.join(SOURCE_KEYS)}"
                )
            if not isinstance(value, str) or not value.strip():
                raise CiteError(f"configuration: source '{code}': '{key}' is not a text")

    attributes: Dict[str, Attribute] = {}
    for key, entry in _need(raw, "attribute", dict, "top level").items():
        where = f"attribute '{key}'"
        attributes[key] = Attribute(
            key, _need(entry, "name", str, where), _need(entry, "description", str, where),
            _need(entry, "list", bool, where),
        )
    if tuple(attributes) != ATTRIBUTES:
        raise CiteError(f"configuration: attribute: the tooling needs exactly {' '.join(ATTRIBUTES)}, in this order")

    marks = _need(raw, "markup", dict, "top level")
    for key, expected in (
        ("separator", "="), ("comment", "#"), ("remove", "-"), ("placeholder", "~"), ("translation", "|"),
        ("done", "# done"),
    ):
        if _need(marks, key, str, "markup") != expected:
            raise CiteError(f"configuration: markup.{key}: the tooling supports {expected!r} only")

    rules: Dict[str, Dict[str, str]] = {}
    for entry in _need(raw, "rule", list, "top level"):
        rule_id = _need(entry, "id", str, "rule")
        if rule_id in rules:
            raise CiteError(f"configuration: rule '{rule_id}' is listed twice")
        _need(entry, "name", str, f"rule '{rule_id}'")
        _need(entry, "description", str, f"rule '{rule_id}'")
        rules[rule_id] = entry

    bible = _need(raw, "bible", dict, "top level")
    _need(bible, "path", str, "bible")
    for key in ("source", "reference"):
        if not _need(bible, key, list, "bible") or not all(isinstance(x, str) for x in bible[key]):
            raise CiteError(f"configuration: bible.{key} is not a list of translation ids")

    return Config(
        root=path.parent.parent,
        directory=path.parent,
        raw=raw,
        extension=extension,
        list_separator=separator,
        shard=shard,
        inbox=folders["inbox"],
        cache=folders["cache"],
        markup_extension=_need(form, "markup", str, "format"),
        keyword=_compile(_need(raw["keyword"], "pattern", str, "keyword"), "keyword"),
        reference=_compile(_need(raw, "reference", str, "top level"), "reference"),
        tables=tables,
        languages=languages,
        prefix=prefix,
        block=block,
        sense_status=_status(raw, "sense", SENSE_STATUS),
        word_status=_status(raw, "word", WORD_STATUS),
        relations=relations,
        sets=sets,
        notes=_named(raw, "note"),
        types=types,
        categories=_named(raw, "category"),
        fields=_named(raw, "field"),
        sources=sources,
        attributes=attributes,
        rules=rules,
    )
