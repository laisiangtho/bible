"""A local SQLite index of the tables, for fast reading.

The index lives in the cache folder of the cite directory and is never part
of the repository. It is rebuilt whenever a table file, the configuration or
a Bible text it counts changes, so a reader never sees stale rows. Commands
that change the tables read the tables themselves.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from assist.cite import check, lexicon as model, markup, tables, words
from assist.cite.config import ID_KINDS, CiteError, Config
from assist.cite.lexicon import Lexicon

NAME = "index.sqlite"
VERSION = "1"
WORD = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", re.UNICODE)

SCHEMA = """
create table meta (key text primary key, value text not null);
create table word (id text primary key, spelling text not null, status text not null, fold text not null, squash text not null);
create table sense (id text primary key, word text not null, number text, type text, category text, field text,
                    "set" text, status text, origin text, source text, note text);
create table gloss (language text not null, sense text not null, terms text, definition text, text text);
create table term (language text not null, fold text not null, squash text not null, sense text not null);
create table relation (source text not null, kind text not null, target text not null, ord integer not null);
create table example (id text primary key, number integer not null, source text, text text not null);
create table usage (example text not null, sense text not null, start text not null, length text not null);
create table translation (language text not null, example text not null, text text not null);
create table link (language text not null, term text not null, senses text, source text, status text, note text);
create table note (kind text, subject text, source text, text text);
create table frequency (fold text primary key, bible integer not null, examples integer not null);
"""
INDEXES = """
create index word_fold on word (fold);
create index word_squash on word (squash);
create index sense_word on sense (word);
create index gloss_sense on gloss (sense);
create index term_fold on term (fold);
create index term_squash on term (squash);
create index relation_source on relation (source);
create index relation_target on relation (target);
create index usage_sense on usage (sense);
create index usage_example on usage (example);
create index translation_example on translation (example);
create index link_term on link (term);
"""


def squash(text: str) -> str:
    """Comparison key that ignores case, hyphens, spaces and apostrophes."""
    return "".join(character for character in text.casefold() if character not in " -'’")


def path(config: Config) -> Path:
    return config.cache / NAME


def _sources(config: Config) -> List[Path]:
    """Every file the index is built from."""
    found = [config.directory / "configuration.json", Path(__file__)]
    for name in tables.stored(config):
        table = tables.definition(config, name)
        location = tables._location(config, table, name)
        found.extend(sorted(location.glob(f"*{config.extension}")) if table.sharded else [location])
    found.extend(config.bible_path(identify) for identify in config.raw["bible"]["source"])
    return found


def fingerprint(config: Config) -> str:
    digest = hashlib.sha1(VERSION.encode())
    for source in _sources(config):
        state = source.stat() if source.exists() else None
        digest.update(f"{source}|{state.st_size if state else -1}|{state.st_mtime_ns if state else -1}\n".encode())
    return digest.hexdigest()


def build(config: Config, target: Path) -> None:
    """Write a fresh index of the stored tables to ``target``."""
    data = tables.read_all(config)
    found = check.structure(config, data)
    if found:
        raise CiteError(
            f"the tables have {len(found)} structural errors, first: {found[0].describe(config)}; "
            f"see: python3 -m assist cite check"
        )
    lexicon = model.build(config, data)
    temporary = target.with_suffix(".part")
    if temporary.exists():
        temporary.unlink()
    connection = sqlite3.connect(temporary)
    try:
        connection.executescript(SCHEMA)
        insert = connection.executemany
        insert("insert into word values (?, ?, ?, ?, ?)", (
            (w.id, w.spelling, w.status, w.spelling.casefold(), squash(w.spelling)) for w in lexicon.words.values()
        ))
        insert('insert into sense values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
            (s.id, s.word, s.number, s.type, s.category, s.field, s.set, s.status, s.origin, s.source, s.note)
            for s in lexicon.senses.values()
        ))
        for language, glosses in lexicon.gloss.items():
            insert("insert into gloss values (?, ?, ?, ?, ?)", (
                (language, sense, g.terms, g.definition, g.text) for sense, g in glosses.items()
            ))
            insert("insert into term values (?, ?, ?, ?)", (
                (language, term.casefold(), squash(term), sense)
                for sense, g in glosses.items() for term in markup.split_list(g.terms)
            ))
        insert("insert into relation values (?, ?, ?, ?)", (
            (source, r.kind, r.to, r.order) for source, found in lexicon.relations.items() for r in found
        ))
        insert("insert into example values (?, ?, ?, ?)", (
            (e.id, int(e.id[len(config.prefix["example"]):]), e.source, e.text) for e in lexicon.examples.values()
        ))
        insert("insert into usage values (?, ?, ?, ?)", (
            (example, sense, u.start, u.length) for example, found in lexicon.usages.items() for sense, u in found.items()
        ))
        for language, translations in lexicon.translations.items():
            insert("insert into translation values (?, ?, ?)", ((language, e, t) for e, t in translations.items()))
        for language, links in lexicon.links.items():
            insert("insert into link values (?, ?, ?, ?, ?, ?)", (
                (language, l.term, l.senses, l.source, l.status, l.note) for l in links.values()
            ))
        insert("insert into note values (?, ?, ?, ?)", lexicon.notes)
        in_examples: Dict[str, int] = {}
        for example in lexicon.examples.values():
            for token in {token.casefold() for token in WORD.findall(example.text)}:
                in_examples[token] = in_examples.get(token, 0) + 1
        in_bible = {form.casefold(): number for form, number, _ in words.count(config)}
        insert("insert into frequency values (?, ?, ?)", (
            (fold, in_bible.get(fold, 0), in_examples.get(fold, 0)) for fold in set(in_bible) | set(in_examples)
        ))
        insert("insert into meta values (?, ?)", [(f"last {kind}", str(lexicon.last[kind])) for kind in ID_KINDS])
        connection.executescript(INDEXES)
        connection.execute("insert into meta values ('fingerprint', ?)", (fingerprint(config),))
        connection.commit()
    finally:
        connection.close()
    os.replace(temporary, target)


class Index:
    """Read access to the index; rebuilt first when it is missing or stale."""

    def __init__(self, config: Config, rebuilt=None) -> None:
        self.config = config
        target = path(config)
        target.parent.mkdir(parents=True, exist_ok=True)
        current = fingerprint(config)
        if not self._fresh(target, current):
            if rebuilt:
                rebuilt()
            build(config, target)
        self.db = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
        self.retired = config.status_code("sense", "retired")

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Index":
        return self

    def __exit__(self, *exception) -> None:
        self.close()

    @staticmethod
    def _fresh(target: Path, current: str) -> bool:
        if not target.is_file():
            return False
        try:
            connection = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
            try:
                row = connection.execute("select value from meta where key = 'fingerprint'").fetchone()
            finally:
                connection.close()
        except sqlite3.DatabaseError:
            return False
        return bool(row) and row[0] == current

    def rows(self, sql: str, parameters: Sequence = ()) -> List[Tuple]:
        return self.db.execute(sql, tuple(parameters)).fetchall()

    def _in(self, sql: str, values: Iterable[str], extra: Sequence = ()) -> List[Tuple]:
        """Rows of a query with ``in ({})`` filled by the values, run in batches."""
        values = list(dict.fromkeys(values))
        found: List[Tuple] = []
        for start in range(0, len(values), 500):
            part = values[start:start + 500]
            found.extend(self.rows(sql.format(",".join("?" * len(part))), list(part) + list(extra)))
        return found

    # Finding.

    def words_for(self, query: str) -> List[str]:
        """Word ids for a Zolai spelling: exact, then without case, then without hyphens, spaces and apostrophes."""
        query = markup.collapse(query)
        for sql, value in (
            ("select id from word where spelling = ?", query),
            ("select id from word where fold = ?", query.casefold()),
            ("select id from word where squash = ?", squash(query)),
        ):
            found = [row[0] for row in self.rows(sql + " order by id", [value])]
            if found:
                return sorted(found, key=lambda value: int(value[1:]))
        return []

    def senses_for_term(self, query: str, languages: Sequence[str]) -> Dict[str, List[str]]:
        """Active sense ids that have the term, per language; a whole word inside a term is tried last."""
        query = markup.collapse(query)
        folded = query.casefold()
        result: Dict[str, List[str]] = {}
        marks = ",".join("?" * len(languages))
        base = (
            "select t.language, t.sense from term t join sense s on s.id = t.sense "
            f"where t.language in ({marks}) and s.status != ? and "
        )
        for condition, value in (("t.fold = ?", folded), ("t.squash = ?", squash(query))):
            for language, sense in self.rows(base + condition, list(languages) + [self.retired, value]):
                result.setdefault(language, []).append(sense)
            if result:
                break
        if not result:
            whole = re.compile(rf"(?<!\w){re.escape(folded)}(?!\w)")
            for language, sense, term in self.rows(
                "select t.language, t.sense, t.fold from term t join sense s on s.id = t.sense "
                f"where t.language in ({marks}) and s.status != ? and t.fold like ?",
                list(languages) + [self.retired, f"%{folded}%"],
            ):
                if whole.search(term):
                    result.setdefault(language, []).append(sense)
        return {language: list(dict.fromkeys(found)) for language, found in result.items()}

    def linked(self, query: str, languages: Sequence[str]) -> Dict[str, Tuple[str, str, List[str]]]:
        """Status, remark and senses of the link row of a word, per language."""
        found = {}
        for language, senses, status, note in self.rows(
            f"select language, senses, status, note from link where term = ? and language in ({','.join('?' * len(languages))})",
            [markup.collapse(query).casefold()] + list(languages),
        ):
            found[language] = (status, note, markup.split_list(senses))
        return found

    def find(self, query: str, limit: int) -> Dict[str, List[str]]:
        """Lines that hold the text, without regard to case: spellings, glosses, examples and translations."""
        like = f"%{markup.collapse(query)}%"
        if like == "%%":
            raise CiteError("the query is empty")
        found: Dict[str, List[str]] = {}
        spelling = "w.spelling || case when s.number != '' then '.' || s.number else '' end"
        queries = {
            "word": ("select id || '  ' || spelling from word where spelling like ? order by length(spelling), spelling", 1),
            "gloss": (
                f"select g.sense || '  ' || {spelling} || '  [' || g.language || ']  ' || g.terms || '  ' || g.definition "
                "from gloss g join sense s on s.id = g.sense join word w on w.id = s.word "
                "where g.terms like ? or g.definition like ? or g.text like ?", 3,
            ),
            "example": (
                "select e.id || '  ' || e.text || ' | ' || coalesce((select group_concat(t.text, ' | ') from translation t where t.example = e.id), '') "
                "from example e where e.text like ? or e.id in (select example from translation where text like ?) order by e.number", 2,
            ),
        }
        for kind, (sql, count) in queries.items():
            rows = [row[0] for row in self.rows(sql, [like] * count)]
            shown = rows if not limit else rows[:limit]
            if len(rows) > len(shown):
                shown.append(f"and {len(rows) - len(shown)} more")
            found[kind] = shown
        return found

    # Reading a part of the lexicon as a model.

    def subset(self, word_ids: Iterable[str] = (), sense_ids: Iterable[str] = (), example_ids: Iterable[str] = ()) -> Lexicon:
        """The model of the words and senses named, with everything their display needs.

        The senses of a named word are complete; a word or sense that is only a
        relation target is present with its own row and nothing more.
        """
        word_ids, sense_ids, example_ids = set(word_ids), set(sense_ids), set(example_ids)
        for (word,) in self._in("select word from sense where id in ({})", sense_ids):
            word_ids.add(word)
        for (sense,) in self._in("select sense from usage where example in ({})", example_ids):
            sense_ids.add(sense)
            word_ids.update(row[0] for row in self.rows("select word from sense where id = ?", [sense]))
        senses = {row[0]: row for row in self._in("select * from sense where word in ({})", word_ids)}
        senses.update({row[0]: row for row in self._in("select * from sense where id in ({})", sense_ids)})
        owners = set(word_ids) | set(senses)
        relations = self._in("select * from relation where source in ({})", owners)
        relations += self._in("select * from relation where target in ({}) and kind in ('v', 'see')", word_ids)
        named = {row[0] for row in relations} | {row[2] for row in relations}
        for row in self._in("select * from sense where id in ({})", named):
            senses.setdefault(row[0], row)
        all_words = word_ids | {row[1] for row in senses.values()} | {value for value in named if value[:1] == self.config.prefix["word"]}
        word_rows = self._in("select id, spelling, status from word where id in ({})", all_words)
        shown = set(word_ids)
        main = [sense for sense, row in senses.items() if row[1] in shown]
        usage_rows = self._in("select * from usage where sense in ({})", main)
        usage_rows += [row for row in self._in("select * from usage where example in ({})", example_ids) if row[1] in senses]
        examples = {row[0] for row in usage_rows}
        example_rows = self._in("select id, source, text from example where id in ({}) ", examples)
        number = {row[0]: int(row[0][len(self.config.prefix["example"]):]) for row in example_rows}
        usage_rows = sorted(set(usage_rows), key=lambda row: number[row[0]])
        data: tables.Tables = {
            "word": word_rows,
            "sense": list(senses.values()),
            "relation": [(row[0], row[1], row[2], str(row[3])) for row in relations],
            "example": example_rows,
            "usage": usage_rows,
            self.config.tables["note"].path: [],
            "sequence": [(kind, value) for kind, value in (
                (key.split()[1], value) for key, value in self.rows("select key, value from meta where key like 'last %'")
            )],
        }
        for language, sense, terms, definition, text in self._in(
            "select * from gloss where sense in ({})", senses
        ):
            data.setdefault(self.config.tables["gloss"].instance(language), []).append((sense, terms, definition, text))
        for language, example, text in self._in("select * from translation where example in ({})", examples):
            data.setdefault(self.config.tables["translation"].instance(language), []).append((example, text))
        return model.build(self.config, data)

    # The work queue.

    def queue(self) -> List[Tuple]:
        """Every active sense with what the work queue needs: id, key, word, type, set, status, examples, frequency."""
        return self.rows(
            "select s.id, w.spelling || case when s.number != '' then '.' || s.number else '' end, w.id, s.type, "
            "s.\"set\", s.status, (select count(*) from usage u where u.sense = s.id), "
            "coalesce(f.bible, 0) + coalesce(f.examples, 0), coalesce((select terms from gloss g where g.sense = s.id "
            "and g.language = ?), '') "
            "from sense s join word w on w.id = s.word left join frequency f on f.fold = w.fold where s.status != ?",
            [self.config.languages[0], self.retired],
        )

    def senses_of(self, word_id: str) -> List[str]:
        return [row[0] for row in self.rows("select id from sense where word = ?", [word_id])]


def open_index(config: Config, rebuilt=None) -> Index:
    return Index(config, rebuilt)


def known(index: Index, value: str) -> Optional[str]:
    """The kind of an id that exists in the index: word, sense or example."""
    for kind, table in (("word", "word"), ("sense", "sense"), ("example", "example")):
        if index.rows(f"select 1 from {table} where id = ?", [value]):
            return kind
    return None


def sense_by_key(index: Index, key: str) -> Optional[str]:
    parts = markup.split_key(key)
    if not parts:
        return None
    row = index.rows(
        "select s.id from sense s join word w on w.id = s.word where w.spelling = ? and s.number = ?", list(parts)
    )
    return row[0][0] if row else None

