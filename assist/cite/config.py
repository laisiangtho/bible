"""Loading and validation of ``cite/configuration.json``."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "cite" / "configuration.json"
SUPPORTED_VERSION = 2

REQUIRED_KEYS = (
    "version", "language", "format", "file", "keyword", "symbol", "attribute",
    "text", "type", "category", "field", "source", "translation", "example",
    "index", "alias", "bible", "word", "rule",
)
VALUE_KINDS = ("code", "english", "keyword", "reference", "number")
SENSE_KEY = re.compile(r"^(?P<keyword>.+)\.(?P<number>[1-9][0-9]*)$")


class CiteError(Exception):
    """A condition that stops a command: bad configuration, missing input."""


@dataclass(frozen=True)
class Attribute:
    key: str
    name: str
    description: str
    value: str
    is_list: bool
    required: bool
    order: int
    xref: bool
    resolve: bool
    pattern: Optional[Pattern[str]]


@dataclass(frozen=True)
class Config:
    root: Path
    directory: Path
    raw: Dict[str, Any]
    language: str
    extension: str
    keyword: Pattern[str]
    attributes: Dict[str, Attribute]
    types: Dict[str, Dict[str, Any]]
    categories: Dict[str, Dict[str, Any]]
    fields: Dict[str, Dict[str, Any]]
    sources: Dict[str, Dict[str, Any]]
    translations: Dict[str, Dict[str, Any]]
    alias: Dict[str, Dict[str, str]]
    files: Dict[str, Dict[str, Any]]
    rules: Dict[str, Dict[str, str]]

    def data_name(self, file_key: str) -> str:
        return self.raw["format"]["filename"].format(
            language=self.language, file=file_key, extension=self.extension
        )

    def data_path(self, file_key: str) -> Path:
        return self.directory / self.data_name(file_key)

    def example_name(self, file_key: str) -> str:
        return self.raw["format"]["example"].format(
            language=self.language, file=file_key, extension=self.extension
        )

    def example_path(self, file_key: str) -> Path:
        return self.directory / self.example_name(file_key)

    def translation_name(self, code: str) -> str:
        return self.raw["format"]["translation"].format(
            language=self.language, code=code, extension=self.extension
        )

    def translation_path(self, code: str) -> Path:
        return self.directory / self.translation_name(code)

    def link_name(self) -> str:
        return self.raw["format"]["link"].format(language=self.language, extension=self.extension)

    def link_path(self) -> Path:
        return self.directory / self.link_name()

    def index_path(self, code: str) -> Path:
        return self.directory / self.raw["format"]["index"].format(code=code)

    def bible_path(self, identify: str) -> Path:
        return self.root / self.raw["bible"]["path"].format(identify=identify)

    def word_path(self, language: str, model: str) -> Path:
        return self.root / self.raw["word"]["path"].format(language=language, model=model)

    def has_meaning(self, type_code: str) -> bool:
        """False for types whose rows carry no term or definition."""
        return bool(self.types.get(type_code, {}).get("meaning", True))


def _reject_duplicates(pairs: List[Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CiteError(f"configuration: key '{key}' occurs twice in one object")
        result[key] = value
    return result


def _need(mapping: Dict[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in mapping:
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
            f"configuration: version {raw['version']!r} is not supported "
            f"(supported: {SUPPORTED_VERSION})"
        )

    language = _need(_need(raw["language"], "keyword", dict, "language"), "code", str, "language.keyword")
    extension = _need(raw["format"], "extension", str, "format")
    filename = _need(raw["format"], "filename", str, "format")
    for field in ("{language}", "{file}", "{extension}"):
        if field not in filename:
            raise CiteError(f"configuration: format.filename lacks {field}")
    keyword = _compile(_need(raw["keyword"], "pattern", str, "keyword"), "keyword")

    types = _need(raw, "type", dict, "top level")
    categories = _need(raw, "category", dict, "top level")
    fields = _need(raw, "field", dict, "top level")
    sources = _need(raw, "source", dict, "top level")
    translations = _need(raw, "translation", dict, "top level")
    for code in list(sources) + list(translations):
        if not re.fullmatch(r"[a-z][a-z0-9]*", code):
            raise CiteError(f"configuration: code '{code}' is not lowercase letters and digits")
    for template, parts in (("example", ("{language}", "{file}", "{extension}")),
                            ("translation", ("{language}", "{code}", "{extension}")),
                            ("link", ("{language}", "{extension}")),
                            ("index", ("{code}",))):
        value = _need(raw["format"], template, str, "format")
        for part in parts:
            if part not in value:
                raise CiteError(f"configuration: format.{template} lacks {part}")
    for key in ("keyword", "term"):
        _need(_need(raw, "index", dict, "top level"), key, str, "index")
    for label, table in (
        ("type", types), ("category", categories), ("field", fields),
        ("source", sources), ("translation", translations),
    ):
        for code, entry in table.items():
            _need(entry, "name", str, f"{label} '{code}'")
            _need(entry, "description", str, f"{label} '{code}'")

    attributes: Dict[str, Attribute] = {}
    for key, entry in _need(raw, "attribute", dict, "top level").items():
        where = f"attribute '{key}'"
        if not re.fullmatch(r"[a-z]", key):
            raise CiteError(f"configuration: {where}: a key is one lowercase letter")
        value = _need(entry, "value", str, where)
        if value not in VALUE_KINDS:
            raise CiteError(f"configuration: {where}: unknown value kind '{value}'")
        pattern = _compile(entry["pattern"], where) if "pattern" in entry else None
        if value == "reference" and pattern is None:
            raise CiteError(f"configuration: {where}: a reference attribute needs a pattern")
        attributes[key] = Attribute(
            key=key,
            name=_need(entry, "name", str, where),
            description=_need(entry, "description", str, where),
            value=value,
            is_list=_need(entry, "list", bool, where),
            required=_need(entry, "required", bool, where),
            order=_need(entry, "order", int, where),
            xref=bool(entry.get("xref", False)),
            resolve=bool(entry.get("resolve", False)),
            pattern=pattern,
        )
    orders = [a.order for a in attributes.values()]
    if len(set(orders)) != len(orders):
        raise CiteError("configuration: two attributes share one order")
    for key in ("i", "t", "c", "f", "w", "d", "r"):
        if key not in attributes:
            raise CiteError(f"configuration: attribute '{key}' is required by the tooling")
    attributes = dict(sorted(attributes.items(), key=lambda item: item[1].order))

    def valid_pair(key: str, value: Any, where: str) -> None:
        if key == "t" and value not in types:
            raise CiteError(f"configuration: {where}: unknown type '{value}'")
        if key == "c" and value not in categories:
            raise CiteError(f"configuration: {where}: unknown category '{value}'")
        if key not in ("t", "c"):
            raise CiteError(f"configuration: {where}: only 't' and 'c' are allowed, found '{key}'")

    alias = _need(_need(raw, "alias", dict, "top level"), "type", dict, "alias")
    for old, target in alias.items():
        if "t" not in target:
            raise CiteError(f"configuration: alias '{old}': missing 't'")
        for key, value in target.items():
            valid_pair(key, value, f"alias '{old}'")

    files = _need(raw, "file", dict, "top level")
    if not files:
        raise CiteError("configuration: no data file is listed")
    for file_key, entry in files.items():
        _need(entry, "name", str, f"file '{file_key}'")
        _need(entry, "description", str, f"file '{file_key}'")
        for key, value in entry.get("require", {}).items():
            valid_pair(key, value, f"file '{file_key}' require")

    rules: Dict[str, Dict[str, str]] = {}
    levels = _need(raw, "level", dict, "top level")
    for entry in _need(raw, "rule", list, "top level"):
        rule_id = _need(entry, "id", str, "rule")
        if rule_id in rules:
            raise CiteError(f"configuration: rule '{rule_id}' is listed twice")
        if _need(entry, "level", str, f"rule '{rule_id}'") not in levels:
            raise CiteError(f"configuration: rule '{rule_id}': unknown level '{entry['level']}'")
        _need(entry, "name", str, f"rule '{rule_id}'")
        _need(entry, "description", str, f"rule '{rule_id}'")
        rules[rule_id] = entry

    bible = raw["bible"]
    _need(bible, "path", str, "bible")
    for key in ("source", "reference"):
        if not _need(bible, key, list, "bible") or not all(isinstance(x, str) for x in bible[key]):
            raise CiteError(f"configuration: bible.{key} is not a list of translation ids")
    word = raw["word"]
    _need(word, "path", str, "word")
    _need(word, "language", dict, "word")
    _need(word, "model", dict, "word")

    return Config(
        root=path.parent.parent,
        directory=path.parent,
        raw=raw,
        language=language,
        extension=extension,
        keyword=keyword,
        attributes=attributes,
        types=types,
        categories=categories,
        fields=fields,
        sources=sources,
        translations=translations,
        alias=alias,
        files=files,
        rules=rules,
    )
