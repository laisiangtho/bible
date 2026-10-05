"""Reading and writing of the data files listed in the configuration."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from assist.cite import markup
from assist.cite.config import CiteError, Config
from assist.cite.markup import Example, Row
from assist.cite.rules import Finding


@dataclass(eq=False)
class DataFile:
    key: str
    name: str
    path: Path
    kind: str = "lexicon"
    lines: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    readable: bool = True

    def rows(self) -> List[Row]:
        return [
            markup.parse(line, self.name, number)
            for number, line in enumerate(self.lines, 1)
            if markup.is_row(line)
        ]


def _read(data: DataFile) -> None:
    """Fill the lines of an existing file. File-level defects become findings."""
    raw = data.path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        data.readable = False
        data.findings.append(Finding(data.name, 0, "E01", f"not UTF-8: {error}"))
        return
    if text.startswith("\ufeff"):
        data.findings.append(Finding(data.name, 1, "E01", "byte order mark"))
        text = text[1:]
    for mark, label in (("\t", "tab"), ("\r", "carriage return")):
        if mark in text:
            number = text[: text.index(mark)].count("\n") + 1
            data.findings.append(Finding(data.name, number, "E01", label))
    if text and (not text.endswith("\n") or text.endswith("\n\n")):
        data.findings.append(Finding(data.name, 0, "F05", "end the file with exactly one newline"))
    data.lines = text.split("\n")
    while data.lines and not data.lines[-1]:
        data.lines.pop()


def read_files(config: Config, only: str = "") -> List[DataFile]:
    """Read every listed data file. File-level defects become findings."""
    if only and only not in config.files:
        raise CiteError(f"'{only}' is not a listed file; listed: {', '.join(config.files)}")
    files: List[DataFile] = []
    for key in config.files:
        data = DataFile(key, config.data_name(key), config.data_path(key))
        files.append(data)
        if not data.path.is_file():
            data.readable = False
            data.findings.append(Finding(data.name, 0, "E01", "the listed file does not exist"))
            continue
        _read(data)
    known = {data.name for data in files} | {config.example_name(key) for key in config.files}
    stray = sorted(
        path.name for path in config.directory.glob(f"*{config.extension}") if path.name not in known
    )
    folder = config.translation_path("x").parent
    listed = {config.translation_path(code) for code in config.translations}
    if folder.is_dir():
        stray.extend(
            str(path.relative_to(config.directory))
            for path in sorted(folder.iterdir())
            if path.is_file() and path not in listed
        )
    if stray:
        files[0].findings.extend(
            Finding(name, 0, "E01", "the file is not listed in the configuration") for name in stray
        )
    if only:
        files = [data for data in files if data.key == only]
    return files


def read_examples(config: Config) -> List[DataFile]:
    """Read the example file of every listed data file that has one."""
    files: List[DataFile] = []
    for key in config.files:
        data = DataFile(key, config.example_name(key), config.example_path(key), "example")
        if data.path.is_file():
            _read(data)
            files.append(data)
    return files


def read_translations(config: Config) -> List[DataFile]:
    """Read the translation file of every listed language that has one."""
    files: List[DataFile] = []
    for code in config.translations:
        data = DataFile(code, config.translation_name(code), config.translation_path(code), "translation")
        if data.path.is_file():
            _read(data)
            files.append(data)
    return files


@dataclass
class Data:
    """Everything read from the cite directory."""

    files: List[DataFile]
    examples: List[DataFile]
    translations: List[DataFile]

    def rows(self) -> List[Row]:
        return all_rows(self.files)

    def example_rows(self) -> List[Row]:
        return all_rows(self.examples)

    def translation_rows(self) -> List[Row]:
        return all_rows(self.translations)

    def every_file(self) -> List[DataFile]:
        return self.files + self.examples + self.translations

    @property
    def examples_by_file(self) -> Dict[str, DataFile]:
        return {file.key: file for file in self.examples}

    def by_key(self) -> Dict[str, List[Example]]:
        """Examples of each sense key, in file order."""
        result: Dict[str, List[Example]] = {}
        for row in self.example_rows():
            if row.described:
                result.setdefault(row.keyword, []).append(markup.example(row))
        return result


def load(config: Config) -> Data:
    return Data(read_files(config), read_examples(config), read_translations(config))


def all_rows(files: List[DataFile]) -> List[Row]:
    return [row for data in files for row in data.rows()]


def to_text(lines: List[str]) -> str:
    lines = list(lines)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n" if lines else ""


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
