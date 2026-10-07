"""Typed markup turned into changes of the tables.

A file is imported as a whole or not at all. Every row is read against the
model, the changed model is checked in full, and only then are the tables
written and the rows of the file marked as done.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from assist.cite import check, markup, render
from assist.cite.config import CiteError, Config
from assist.cite.lexicon import Example, Gloss, Lexicon, Relation, Sense, Usage

STAMP = re.compile(r"^# pulled (?P<word>.+) version (?P<version>[0-9a-f]{12})$")
STAMP_START = "# pulled "
SENSE_KEYS = ("i", "t", "c", "f", "w", "d", "s", "a", "b", "j", "v", "o", "r", "q")
EXAMPLE_KEYS = ("r", "e")
OLD_LOW = "low confidence"

INSERTED = "inserted"
REPLACED = "replaced"
UNCHANGED = "unchanged"
REMOVED = "removed"


@dataclass
class Action:
    """What one row of the file does."""

    row: markup.Row
    verb: str
    subject: str

    def done(self) -> str:
        return f"{markup.DONE} {self.subject} {self.verb}: {self.row.line.strip()}"


@dataclass
class Plan:
    actions: List[Action] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    words: List[str] = field(default_factory=list)
    stamps: List[int] = field(default_factory=list)


class _Problem(Exception):
    """A row that cannot be imported; the message names what to change."""


def stamp_line(word: str, version: str) -> str:
    return f"# pulled {word} version {version}"


def plan(config: Config, lexicon: Lexicon, lines: List[str]) -> Plan:
    """Apply the rows of a file to the model. Errors are collected, one per row."""
    return _Import(config, lexicon, lines).run()


def mark_done(lines: List[str], result: Plan) -> List[str]:
    """The lines of the file after the import: every imported row is a comment."""
    marked = list(lines)
    for action in result.actions:
        marked[action.row.number - 1] = action.done()
    for number in result.stamps:
        marked[number - 1] = f"{markup.DONE} {marked[number - 1][2:]}"
    return marked


class _Import:
    def __init__(self, config: Config, lexicon: Lexicon, lines: List[str]) -> None:
        self.config = config
        self.lexicon = lexicon
        self.lines = lines
        self.result = Plan()
        self.primary = config.languages[0]
        self.by_text: Optional[Dict[Tuple[str, str], List[str]]] = None
        self.new_words: Set[str] = set()
        self.pending: List[Tuple[markup.Row, str, Dict[str, List[str]]]] = []
        self.before: Dict[str, Tuple] = {}
        self.touched: Dict[str, int] = {}
        self.stored: Dict[str, Tuple[str, str, str]] = {}
        self.edited: Dict[str, Tuple[Tuple[str, str, str], int]] = {}

    def run(self) -> Plan:
        rows: List[markup.Row] = []
        for number, line in enumerate(self.lines, 1):
            match = STAMP.match(line.rstrip())
            if match:
                self.result.stamps.append(number)
                self._stamp(number, match.group("word"), match.group("version"))
            elif line.startswith(STAMP_START):
                self.result.errors.append(
                    f"line {number}: the version stamp is damaged; pull the word again and repeat the edit"
                )
            elif markup.is_row(line):
                rows.append(markup.parse(line, number))
        if self.result.errors:
            return self.result
        if not rows:
            self.result.errors.append("the file holds no row to import")
            return self.result
        senses = [row for row in rows if row.described and not row.is_example]
        steps = (
            (self._words, [row for row in rows if not row.is_example and not row.remove]),
            (self._sense, senses),
            (self._relations, None),
            (self._example, [row for row in rows if row.is_example]),
            (self._bare, [row for row in rows if not row.described]),
        )
        for step, selected in steps:
            if selected is None:
                step()
                continue
            for row in selected:
                try:
                    step(row)
                except _Problem as problem:
                    self.result.errors.append(f"line {row.number}: {problem}")
            if self.result.errors:
                break
        self.result.actions.sort(key=lambda action: action.row.number)
        return self.result

    def _stamp(self, number: int, spelling: str, version: str) -> None:
        word = self.lexicon.spelling.get(spelling)
        current = render.version(render.word_lines(self.lexicon, word)) if word else ""
        if current != version:
            self.result.errors.append(
                f"line {number}: the rows of '{spelling}' changed in the tables after the file was pulled; "
                f"pull the word again and repeat the edit"
            )

    def _done(self, row: markup.Row, verb: str, subject: str) -> None:
        self.result.actions.append(Action(row, verb, subject))

    def _keyword(self, row: markup.Row) -> str:
        if not self.config.keyword.match(row.keyword):
            raise _Problem(f"'{row.keyword}' is not written as a keyword")
        return row.keyword

    def _values(self, row: markup.Row, allowed: Tuple[str, ...], kind: str) -> Dict[str, str]:
        keys = [key for key, _ in row.attributes]
        for key in keys:
            if key not in allowed:
                raise _Problem(f"({key}:) is not an attribute of {kind}; allowed: {' '.join(allowed)}")
            if keys.count(key) > 1:
                raise _Problem(f"({key}:) is written twice")
        for key, value in row.attributes:
            if not value.strip():
                raise _Problem(f"({key}:) is empty")
        if "(" in row.text or ")" in row.text:
            raise _Problem(f"a parenthesis outside an attribute: '{row.text}'")
        return row.values()

    # Words.

    def _words(self, row: markup.Row) -> None:
        """Make the keyword of a row, and the variants it names, exist before anything refers to them."""
        keyword = self._keyword(row)
        if keyword not in self.lexicon.spelling:
            word = self.lexicon.add_word(keyword, self.config.status_code("word", "standard"))
            self.new_words.add(keyword)
            self.result.words.append(f"{word.id} {keyword}")
        if not row.described:
            return
        for key, value in row.attributes:
            if key != "v":
                continue
            for item in markup.split_list(value):
                if not self.config.keyword.match(item):
                    raise _Problem(f"(v:{item}) is not written as a keyword")
                if item not in self.lexicon.spelling:
                    word = self.lexicon.add_word(item, self.config.status_code("word", "variant"))
                    self.result.words.append(f"{word.id} {item}, variant")

    def _bare(self, row: markup.Row) -> None:
        """A row that is a keyword alone: the word exists, or with the remove mark is retired."""
        keyword = self._keyword(row)
        word_id = self.lexicon.spelling.get(keyword)
        if not row.remove:
            word = self.lexicon.words[word_id]
            verb = INSERTED if keyword in self.new_words else UNCHANGED
            if self.config.word_status[word.status] == "retired":
                word.status, verb = self.config.status_code("word", "standard"), REPLACED
            self._done(row, verb, f"{word_id} {keyword}")
            return
        if word_id is None:
            raise _Problem(f"'{keyword}' is not a word of the lexicon")
        word = self.lexicon.words[word_id]
        active = [s for s in self.lexicon.senses_of.get(word_id, []) if self.lexicon.active(s)]
        if active:
            raise _Problem(
                f"'{keyword}' still has the senses {', '.join(self.lexicon.key(s) for s in active)}; "
                f"remove them first"
            )
        retired = self.config.status_code("word", "retired")
        self._done(row, UNCHANGED if word.status == retired else REMOVED, f"{word_id} {keyword}")
        word.status = retired

    # Senses.

    def _status(self, value: str) -> Tuple[str, str]:
        """Code and remark of q. No q is a draft."""
        if not value:
            return self.config.status_code("sense", "draft"), ""
        name, _, note = value.partition(",")
        name, note = name.strip(), note.strip()
        if name not in self.config.sense_status.values():
            raise _Problem(
                f"(q:{value}): '{name}' is not a status; known: {', '.join(self.config.sense_status.values())}"
            )
        if note == OLD_LOW:
            raise _Problem(f"(q:{value}): thin evidence is written (q:low)")
        return self.config.status_code("sense", name), note

    def _target_sense(self, row: markup.Row, word_id: str, value: str) -> Optional[str]:
        """The sense named by i; None for a new sense."""
        lexicon = self.lexicon
        if value in ("", markup.NEW):
            return None
        if self.config.id_number("sense", value) is not None:
            if value not in lexicon.senses:
                raise _Problem(f"(i:{value}) is not a sense")
            if lexicon.senses[value].word != word_id:
                raise _Problem(f"(i:{value}) is the sense {lexicon.key(value)}, not a sense of '{row.keyword}'")
            return value
        if not check.NUMBER.match(value):
            raise _Problem(f"(i:{value}) is a sense number, a sense id or {markup.NEW}")
        found = lexicon.sense_by_key(markup.sense_key(row.keyword, value))
        if found is None:
            raise _Problem(f"'{row.keyword}' has no sense {value}; a new sense is written without i")
        return found

    def _snapshot(self, sense_id: str) -> Tuple:
        lexicon = self.lexicon
        sense = lexicon.senses[sense_id]
        gloss = lexicon.gloss.get(self.primary, {}).get(sense_id) or Gloss()
        relations = sorted(
            (r.kind, r.to, r.order) for r in lexicon.relations.get(sense_id, []) if r.kind in render.RELATION_KEYS
        )
        return (
            sense.type, sense.category, sense.field, sense.status, sense.origin, sense.source, sense.note,
            gloss.terms, gloss.definition, gloss.text, tuple(relations),
        )

    def _redirect(self, row: markup.Row, values: Dict[str, str]) -> None:
        lexicon = self.lexicon
        targets = markup.XREF.findall(row.text)
        if set(values) != {"t"} or len(targets) != 1 or row.text != f"<{targets[0]}>":
            raise _Problem("a redirect is (t:see) followed by one link, as in (t:see) <Be-ersheba>")
        source = lexicon.spelling.get(row.keyword)
        target = lexicon.spelling.get(markup.collapse(targets[0]))
        if source is None:
            raise _Problem(f"'{row.keyword}' is not a word of the lexicon")
        if target is None:
            raise _Problem(f"<{targets[0]}> names no word")
        current = [r.to for r in lexicon.relations.get(source, []) if r.kind == "see"]
        subject = f"{source} {row.keyword}"
        if row.remove:
            if current != [target]:
                raise _Problem(f"'{row.keyword}' is not redirected to <{targets[0]}>")
            lexicon.set_relations(source, ("see",), [])
            self._done(row, REMOVED, subject)
        elif current == [target]:
            self._done(row, UNCHANGED, subject)
        else:
            lexicon.set_relations(source, ("see",), [Relation("see", target, 1)])
            self._done(row, REPLACED if current else INSERTED, subject)

    def _duplicate(self, word_id: str, type_code: str, terms: List[str], definition: str) -> Optional[Tuple[str, str]]:
        """An active sense of the word with the same type that shares a term, or the definition."""
        wanted = {term.casefold() for term in terms}
        for sense_id in self.lexicon.senses_of.get(word_id, []):
            sense = self.lexicon.senses[sense_id]
            if sense.type != type_code or not self.lexicon.active(sense_id):
                continue
            gloss = self.lexicon.gloss.get(self.primary, {}).get(sense_id) or Gloss()
            shared = wanted & {term.casefold() for term in markup.split_list(gloss.terms)}
            if shared:
                return sense_id, f"the term '{sorted(shared)[0]}'"
            if not wanted and gloss.definition == definition:
                return sense_id, "the same definition" if definition else "no meaning either"
        return None

    def _sense(self, row: markup.Row) -> None:
        config, lexicon = self.config, self.lexicon
        keyword = self._keyword(row)
        values = self._values(row, SENSE_KEYS, "a sense row")
        if values.get("t") == "see":
            self._redirect(row, values)
            return
        word_id = lexicon.spelling.get(keyword)
        if word_id is None:
            raise _Problem(f"'{keyword}' is not a word of the lexicon")
        target = self._target_sense(row, word_id, values.get("i", ""))
        if target is not None:
            if target in self.touched:
                raise _Problem(f"{lexicon.key(target)} ({target}) is already given on line {self.touched[target]}")
            self.touched[target] = row.number
        if row.remove:
            if target is None:
                raise _Problem("a sense is removed by its number or id, as in - khut = (i:2)")
            retired = config.status_code("sense", "retired")
            verb = UNCHANGED if lexicon.senses[target].status == retired else REMOVED
            lexicon.senses[target].status = retired
            self._done(row, verb, f"{target} {lexicon.key(target)}")
            return
        type_code = values.get("t", "")
        if type_code not in config.types:
            raise _Problem(f"(t:{type_code}) is not a type" if type_code else "(t:) is missing")
        lists = {key: markup.split_list(values.get(key, "")) for key in ("c", "f", "w", "s", "a", "b", "j", "v", "r")}
        for key, items in lists.items():
            if any(not item for item in items):
                raise _Problem(f"({key}:{values[key]}) has an empty item")
            if len(items) > 1 and not config.attributes[key].is_list:
                raise _Problem(f"({key}:{values[key]}) takes one item")
        status, note = self._status(values.get("q", ""))
        terms = markup.join_list(lists["w"])
        definition = values.get("d", "")
        if target is None and values.get("i") != markup.NEW:
            duplicate = self._duplicate(word_id, type_code, lists["w"], definition)
            if duplicate:
                other, reason = duplicate
                number = lexicon.senses[other].number or other
                raise _Problem(
                    f"{lexicon.key(other)} ({other}) has the same type and {reason}; "
                    f"write (i:{number}) to replace it or (i:{markup.NEW}) to add a further sense"
                )
        before = self._snapshot(target) if target else None
        if target is None:
            number = self._next_number(word_id) if config.has_meaning(type_code) else ""
            target = lexicon.new_id("sense")
            self.touched[target] = row.number
            lexicon.add_sense(Sense(target, word_id, number, "", "", "", self._set(lists["r"]), "", "", "", ""))
        sense = lexicon.senses[target]
        if not sense.number and config.has_meaning(type_code):
            sense.number = self._next_number(word_id)
        sense.type = type_code
        sense.category = markup.join_list(lists["c"])
        sense.field = markup.join_list(lists["f"])
        sense.status, sense.note = status, note
        word = lexicon.words[word_id]
        if lexicon.active(target) and config.word_status[word.status] in ("retired", "variant"):
            word.status = config.status_code("word", "standard")
        sense.origin = values.get("o", "")
        sense.source = markup.join_list(lists["r"])
        gloss = Gloss(terms, definition, row.text)
        glosses = lexicon.gloss.setdefault(self.primary, {})
        if gloss.empty:
            glosses.pop(target, None)
        else:
            glosses[target] = gloss
        self.pending.append((row, target, {key: lists[key] for key in render.RELATION_KEYS}))
        if before is None:
            self._done(row, INSERTED, f"{target} {lexicon.key(target)}")
        else:
            self._done(row, REPLACED, f"{target} {lexicon.key(target)}")
            self.before[target] = before

    def _next_number(self, word_id: str) -> str:
        """The number after the highest one the word ever had; a number is never reused."""
        senses = (self.lexicon.senses[sense_id] for sense_id in self.lexicon.senses_of.get(word_id, []))
        return str(max((int(sense.number) for sense in senses if sense.number), default=0) + 1)

    def _set(self, sources: List[str]) -> str:
        """Set of a new sense: bible when every source is a Bible verse, core otherwise."""
        verses = [part for part in sources if self.config.reference.match(part) and part[0].isdigit()]
        return "bible" if sources and len(verses) == len(sources) else "core"

    def _relations(self) -> None:
        """Resolve the keywords and sense keys of s, a, b, j and v once every sense of the file exists."""
        lexicon = self.lexicon
        for row, sense_id, lists in self.pending:
            relations: List[Relation] = []
            try:
                for kind, items in lists.items():
                    for order, item in enumerate(items, 1):
                        target = lexicon.spelling.get(item) or lexicon.sense_by_key(item)
                        if target is None:
                            raise _Problem(
                                f"({kind}:{item}) names no word and no sense; "
                                f"a word is added by a row of its own or by a line with the word alone"
                            )
                        if items.count(item) > 1:
                            raise _Problem(f"({kind}:{markup.join_list(items)}) names '{item}' twice")
                        relations.append(Relation(kind, target, order))
            except _Problem as problem:
                self.result.errors.append(f"line {row.number}: {problem}")
                continue
            lexicon.set_relations(sense_id, render.RELATION_KEYS, relations)
            if sense_id in self.before and self.before[sense_id] == self._snapshot(sense_id):
                for action in self.result.actions:
                    if action.row is row:
                        action.verb = UNCHANGED

    # Examples.

    def _index(self) -> Dict[Tuple[str, str], List[str]]:
        if self.by_text is None:
            self.by_text = {}
            for example in self.lexicon.examples.values():
                self.by_text.setdefault((example.text, example.source), []).append(example.id)
        return self.by_text

    def _remove_usage(self, example_id: str, sense_id: str) -> None:
        example = self.lexicon.examples[example_id]
        self.lexicon.remove_usage(example_id, sense_id)
        if example_id not in self.lexicon.examples:
            self._index()[(example.text, example.source)].remove(example_id)

    def _example(self, row: markup.Row) -> None:
        lexicon = self.lexicon
        values = self._values(row, EXAMPLE_KEYS, "an example row")
        sense_id = lexicon.sense_by_key(row.keyword)
        if sense_id is None:
            raise _Problem(f"'{row.keyword}' is not a sense")
        named = values.get("e", "")
        index = self._index()

        def subject(example_id: str) -> str:
            return f"{example_id} {row.keyword}"

        if row.remove and named:
            if named not in lexicon.shown_by.get(sense_id, []):
                raise _Problem(f"(e:{named}) is not an example of {row.keyword}")
            self._remove_usage(named, sense_id)
            self._done(row, REMOVED, subject(named))
            return
        keyword = lexicon.word_of(sense_id).spelling
        zolai, english, bars = markup.split_example(row.text)
        if bars != 1 or not zolai or not english:
            raise _Problem(f"an example is the Zolai text, {markup.TRANSLATION} and the translation")
        if markup.PLACEHOLDER not in zolai or markup.PLACEHOLDER in english:
            raise _Problem(f"the keyword is written {markup.PLACEHOLDER} in the Zolai text, and only there")
        text, starts, length = markup.fill(zolai, keyword)
        try:
            located = markup.blank(text, keyword, starts, length) == zolai
        except CiteError:
            located = False
        if not located:
            raise _Problem(f"the place of '{keyword}' in '{zolai}' cannot be told by counting words")
        source = markup.join_list(markup.split_list(values.get("r", "")))
        usage = Usage(markup.join_list(str(start) for start in starts), str(length))
        translations = lexicon.translations.setdefault(self.primary, {})

        if row.remove:
            found = [e for e in lexicon.shown_by.get(sense_id, []) if lexicon.examples[e].text == text]
            if len(found) != 1:
                raise _Problem(f"{len(found)} examples of {row.keyword} have this text; name the example with (e:)")
            self._remove_usage(found[0], sense_id)
            self._done(row, REMOVED, subject(found[0]))
            return

        if named and named != markup.NEW:
            if named not in lexicon.examples:
                raise _Problem(f"(e:{named}) is not an example")
            example = lexicon.examples[named]
            content = (text, source, english)
            stored = self.stored.setdefault(named, (example.text, example.source, translations.get(named, "")))
            current = lexicon.usages.get(named, {}).get(sense_id)
            if content != stored:
                if named in self.edited and self.edited[named][0] != content:
                    raise _Problem(
                        f"{named} is given another text, source or translation on line {self.edited[named][1]}; "
                        f"the rows of one example agree, or keep what is stored"
                    )
                self.edited[named] = (content, row.number)
                index[(example.text, example.source)].remove(named)
                example.text, example.source = text, source
                index.setdefault((text, source), []).append(named)
                translations[named] = english
            lexicon.set_usage(named, sense_id, usage)
            self._done(row, UNCHANGED if content == stored and current == usage else REPLACED, subject(named))
            return

        candidates = index.get((text, source), [])
        equal = [e for e in candidates if translations.get(e) == english]
        if equal:
            current = lexicon.usages.get(equal[0], {}).get(sense_id)
            lexicon.set_usage(equal[0], sense_id, usage)
            verb = INSERTED if current is None else UNCHANGED if current == usage else REPLACED
            self._done(row, verb, subject(equal[0]))
            return
        if candidates and named != markup.NEW:
            raise _Problem(
                f"{candidates[0]} has the same text and source with the translation "
                f"'{translations.get(candidates[0], '')}'; write (e:{candidates[0]}) to replace it "
                f"or (e:{markup.NEW}) to keep both"
            )
        example = Example(lexicon.new_id("example"), source, text)
        lexicon.examples[example.id] = example
        index.setdefault((text, source), []).append(example.id)
        translations[example.id] = english
        lexicon.set_usage(example.id, sense_id, usage)
        self._done(row, INSERTED, subject(example.id))
