"""The rules of ``cite/Format.md`` applied to the tables. Rule ids: configuration.

The check has two stages. ``structure`` reads the raw rows: ids, references
between tables, codes. ``content`` reads the model built from sound rows:
spellings, meanings, marks, examples.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from assist.cite import credits, lexicon as model, markup, tables
from assist.cite.config import ID_KINDS, SENSE_RELATIONS, CiteError, Config
from assist.cite.lexicon import Lexicon
from assist.cite.tables import Tables

LINK_TERM = re.compile(r"^[a-z]+(?:[ '-][a-z]+)*$")
NUMBER = re.compile(r"^[1-9][0-9]*$")
UNTYPABLE = ("(", ")", markup.PLACEHOLDER, markup.TRANSLATION)


@dataclass(frozen=True)
class Finding:
    table: str
    subject: str
    rule: str
    detail: str

    def describe(self, config: Config) -> str:
        name = config.rules.get(self.rule, {}).get("name", "")
        return f"{self.table} {self.subject}: {self.rule} {name}: {self.detail}"


def structure(config: Config, data: Tables, problems: Optional[List[str]] = None) -> List[Finding]:
    """Findings on ids, references between tables and codes."""
    found: List[Finding] = []
    stored = {name: table.path for name, table in config.tables.items() if not table.per_language}

    def per_language(table: str) -> List[str]:
        return [
            config.tables[table].instance(language) for language in config.languages
            if config.tables[table].instance(language) in data
        ]

    for message in problems or []:
        place, _, detail = message.partition(": ")
        found.append(Finding("file", place, "E01", detail))

    # Sequence.
    last: Dict[str, int] = {}
    for kind, value in data[stored["sequence"]]:
        if kind not in ID_KINDS or kind in last or not re.fullmatch(r"[0-9]+", value):
            found.append(Finding(stored["sequence"], kind, "E03", f"'{value}': one row per kind of id, a whole number"))
        else:
            last[kind] = int(value)
    for kind in ID_KINDS:
        if kind not in last:
            found.append(Finding(stored["sequence"], kind, "E03", "no row"))

    # Ids of the three tables that give them.
    ids: Dict[str, Set[str]] = {}
    for kind in ID_KINDS:
        known: Set[str] = set()
        for row in data[stored[kind]]:
            number = config.id_number(kind, row[0])
            if number is None:
                found.append(Finding(stored[kind], row[0], "E02", f"not an id of a {kind}"))
            elif row[0] in known:
                found.append(Finding(stored[kind], row[0], "E02", "the id occurs twice"))
            elif kind in last and number > last[kind]:
                found.append(Finding(stored[kind], row[0], "E03", f"above the last id given, {last[kind]}"))
            known.add(row[0])
        ids[kind] = known

    def refer(table: str, subject: str, value: str, *kinds: str) -> None:
        if not any(value in ids[kind] for kind in kinds):
            found.append(Finding(table, subject, "E04", f"'{value}' is not the id of a {' or '.join(kinds)}"))

    def unique(table: str, keys: List[Tuple[str, ...]], what: str) -> None:
        for key, count in Counter(keys).items():
            if count > 1:
                found.append(Finding(table, " ".join(key), "E02", f"{count} rows for one {what}"))

    def coded(table: str, subject: str, column: str, value: str, codes, many: bool = False) -> None:
        items = value.split(config.list_separator) if many and value else [value]
        if not many or value:
            for item in items:
                if item not in codes:
                    found.append(Finding(table, subject, "E05", f"{column} '{item}' is not listed"))
            if len(set(items)) != len(items):
                found.append(Finding(table, subject, "E05", f"{column} '{value}' names a code twice"))

    for word, _, status in data[stored["word"]]:
        coded(stored["word"], word, "status", status, config.word_status)
    for row in data[stored["sense"]]:
        sense = model.Sense(*row)
        refer(stored["sense"], sense.id, sense.word, "word")
        coded(stored["sense"], sense.id, "type", sense.type, config.types)
        if sense.type == "see":
            found.append(Finding(stored["sense"], sense.id, "E05", "a redirect is a relation, not a sense"))
        coded(stored["sense"], sense.id, "category", sense.category, config.categories, many=True)
        coded(stored["sense"], sense.id, "field", sense.field, config.fields, many=True)
        coded(stored["sense"], sense.id, "set", sense.set, config.sets)
        coded(stored["sense"], sense.id, "status", sense.status, config.sense_status)
    for name in per_language("gloss"):
        for row in data[name]:
            refer(name, row[0], row[0], "sense")
        unique(name, [(row[0],) for row in data[name]], "sense")
    relation = stored["relation"]
    for source, kind, target, order in data[relation]:
        subject = f"{source} {kind} {target}"
        coded(relation, subject, "kind", kind, config.relations)
        refer(relation, subject, source, "sense", "word")
        refer(relation, subject, target, "sense", "word")
        if not NUMBER.match(order):
            found.append(Finding(relation, subject, "E12", f"order '{order}' is not a positive whole number"))
    unique(relation, [(row[0], row[1], row[2]) for row in data[relation]], "target")
    for example, sense, _, _ in data[stored["usage"]]:
        refer(stored["usage"], f"{example} {sense}", example, "example")
        refer(stored["usage"], f"{example} {sense}", sense, "sense")
    unique(stored["usage"], [(row[0], row[1]) for row in data[stored["usage"]]], "example and sense")
    for name in per_language("translation"):
        for row in data[name]:
            refer(name, row[0], row[0], "example")
        unique(name, [(row[0],) for row in data[name]], "example")
    for name in per_language("link"):
        for term, senses, _, status, _ in data[name]:
            coded(name, term, "status", status, config.sense_status)
            for sense in senses.split(config.list_separator) if senses else []:
                refer(name, term, sense, "sense")
        unique(name, [(row[0],) for row in data[name]], "term")
    for kind, subject, _, _ in data[stored["note"]]:
        coded(stored["note"], subject, "kind", kind, config.notes)
    for kind, form, _, _, _ in data[stored["pattern"]]:
        coded(stored["pattern"], form, "kind", kind, config.patterns)
    return found


def content(config: Config, lexicon: Lexicon) -> List[Finding]:
    """Findings on what the rows say. The structure of the tables is sound."""
    found: List[Finding] = []
    separator = config.list_separator

    def add(table: str, subject: str, rule: str, detail: str) -> None:
        found.append(Finding(table, subject, rule, detail))

    def untypable(table: str, subject: str, column: str, value: str, marks: bool) -> None:
        for mark in UNTYPABLE + (() if marks else ("<", ">", "{", "}")):
            if mark in value:
                add(table, subject, "E09", f"'{mark}' in {column}: '{_short(value)}'")
                return
        if value != markup.collapse(value):
            add(table, subject, "E09", f"spaces in {column} are not single: '{_short(value)}'")

    def sources(table: str, subject: str, value: str) -> None:
        for part in value.split(separator) if value else []:
            if not config.valid_reference(part):
                add(table, subject, "E13", f"'{part}'")

    # Words.
    standard: Set[str] = set()
    spellings: Dict[str, str] = {}
    for word in lexicon.words.values():
        subject = f"{word.id} {word.spelling}"
        if not config.keyword.match(word.spelling):
            add("word", subject, "E06", f"'{word.spelling}' is not written as a keyword")
        if word.spelling in spellings:
            add("word", subject, "E06", f"same spelling as {spellings[word.spelling]}")
        spellings[word.spelling] = word.id
        if config.word_status[word.status] == "standard":
            standard.add(word.spelling)

    retired_words = {
        word.spelling for word in lexicon.words.values() if config.word_status[word.status] == "retired"
    }

    def marks(table: str, subject: str, column: str, value: str, own: str, active: bool) -> None:
        """Links and mentions inside prose. Prose of a retired sense may name what is retired."""
        if "<" in value or ">" in value:
            if "<" in markup.XREF.sub("", value) or ">" in markup.XREF.sub("", value):
                add(table, subject, "E10", f"unbalanced < > in {column}: '{_short(value)}'")
            else:
                for inner in markup.XREF.findall(value):
                    for target in markup.xref_targets(inner):
                        parts = markup.split_key(target)
                        if config.keyword.match(target):
                            if target not in lexicon.spelling:
                                add(table, subject, "E10", f"<{target}> names no word")
                            elif target in retired_words and active:
                                add(table, subject, "E10", f"<{target}> names a retired word")
                        elif parts and config.keyword.match(parts[0]):
                            named = lexicon.sense_by_key(target)
                            if named is None:
                                add(table, subject, "E10", f"<{target}> names no sense")
                            elif active and not lexicon.active(named):
                                add(table, subject, "E10", f"<{target}> names a retired sense")
                        else:
                            add(table, subject, "E10", f"'{target}' in <{inner}> is not a keyword or a sense key")
        if "{" in value or "}" in value:
            leftover = markup.MENTION.sub("", value)
            if "{" in leftover or "}" in leftover:
                add(table, subject, "E11", f"unbalanced braces in {column}: '{_short(value)}'")
                return
            for inner in markup.MENTION.findall(value):
                mention = markup.collapse(inner)
                if not mention:
                    add(table, subject, "E11", "empty braces")
                elif "<" in mention or ">" in mention:
                    add(table, subject, "E11", f"a link inside braces: '{_short(mention)}'")
                elif mention in standard and mention != own:
                    add(table, subject, "E11", f"'{mention}' is a word of the lexicon; write <{mention}>")

    # Senses and their glosses.
    primary = config.languages[0]
    seen: Dict[Tuple, str] = {}
    terms_of: Dict[str, Set[str]] = {language: set() for language in lexicon.gloss}
    for word_id, sense_ids in lexicon.senses_of.items():
        numbers: Dict[str, str] = {}
        for sense_id in sense_ids:
            sense = lexicon.senses[sense_id]
            spelling = lexicon.words[word_id].spelling
            subject = f"{sense_id} {lexicon.key(sense_id)}"
            if sense.number:
                if not NUMBER.match(sense.number):
                    add("sense", subject, "E07", f"'{sense.number}' is not a positive whole number")
                elif sense.number in numbers:
                    add("sense", subject, "E07", f"same number as {numbers[sense.number]}")
                numbers[sense.number] = sense_id
            elif config.has_meaning(sense.type):
                add("sense", subject, "E07", "no number")
            joins = [r for r in lexicon.relations.get(sense_id, []) if r.kind == "j"]
            glosses = {language: found_in.get(sense_id) for language, found_in in lexicon.gloss.items()}
            if config.has_meaning(sense.type) and len(joins) != 1 and not any(
                gloss and (gloss.terms or gloss.definition) for gloss in glosses.values()
            ):
                add("sense", subject, "E08", "neither a term nor a definition in any language")
            for language, gloss in glosses.items():
                if gloss is None:
                    continue
                table = config.tables["gloss"].instance(language)
                if gloss.empty:
                    add(table, subject, "E09", "the row holds nothing")
                items = gloss.terms.split(separator) if gloss.terms else []
                if any(not item for item in items):
                    add(table, subject, "E09", f"an empty term in '{gloss.terms}'")
                if len(set(items)) != len(items):
                    add(table, subject, "E09", f"a term twice in '{gloss.terms}'")
                terms_of[language].update(item.casefold() for item in items)
                untypable(table, subject, "terms", gloss.terms, marks=False)
                untypable(table, subject, "definition", gloss.definition, marks=True)
                untypable(table, subject, "text", gloss.text, marks=True)
                marks(table, subject, "definition", gloss.definition, spelling, lexicon.active(sense_id))
                marks(table, subject, "text", gloss.text, spelling, lexicon.active(sense_id))
            untypable("sense", subject, "note", sense.note, marks=True)
            marks("sense", subject, "note", sense.note, spelling, lexicon.active(sense_id))
            untypable("sense", subject, "origin", sense.origin, marks=False)
            sources("sense", subject, sense.source)
            if sense.type == "name" and not re.match(r"[A-Z0-9]", spelling):
                add("sense", subject, "E18", f"'{spelling}'")
            gloss = glosses.get(primary) or model.Gloss()
            identity = (word_id, sense.type, sense.category, gloss.terms, gloss.definition)
            if identity in seen and lexicon.active(sense_id):
                add("sense", subject, "E19", f"same type, category, terms and definition as {seen[identity]}")
            elif lexicon.active(sense_id):
                seen[identity] = sense_id

    # Relations.
    for source, relations in lexicon.relations.items():
        by_kind: Dict[str, List[model.Relation]] = {}
        for relation in relations:
            by_kind.setdefault(relation.kind, []).append(relation)
        subject = f"{source} {lexicon.name(source)}"
        live = lexicon.active(source) if source in lexicon.senses else lexicon.words[source].spelling not in retired_words
        for relation in relations if live else []:
            gone = (
                not lexicon.active(relation.to) if relation.to in lexicon.senses
                else lexicon.words[relation.to].spelling in retired_words
            )
            if gone:
                add("relation", subject, "E12", f"{relation.kind} leads to the retired {lexicon.name(relation.to)}")
        if not live and "see" in by_kind:
            add("relation", subject, "E12", "a retired word is not redirected")
        for kind, group in by_kind.items():
            if sorted(r.order for r in group) != list(range(1, len(group) + 1)):
                add("relation", subject, "E12", f"the order of the {kind} targets does not run from 1")
            if (kind == "see") != (source in lexicon.words):
                add("relation", subject, "E12", "see leads from a word; every other kind leads from a sense")
                continue
            for relation in group:
                target = lexicon.name(relation.to)
                if kind in ("see", "v") and relation.to not in lexicon.words:
                    add("relation", subject, "E12", f"{kind} leads to a word, not to the sense {target}")
                elif kind == "v":
                    word = lexicon.words[relation.to]
                    if config.word_status[word.status] != "variant" or lexicon.senses_of.get(word.id):
                        add("relation", subject, "E12", f"the variant '{target}' is a word with the status variant and no sense")
                elif kind == "j" and relation.to == lexicon.senses[source].word:
                    add("relation", subject, "E12", "j names the keyword of the sense")
                elif kind == "see" and relation.to == source:
                    add("relation", subject, "E12", "see leads to the word itself")
        if len(by_kind.get("see", [])) > 1:
            add("relation", subject, "E12", "a redirected word has one target")

    # Examples, usages and translations.
    identities: Dict[Tuple, str] = {}
    for example in lexicon.examples.values():
        subject = example.id
        if not example.text:
            add("example", subject, "E14", "no text")
        for mark in UNTYPABLE + ("<", ">"):
            if mark in example.text:
                add("example", subject, "E14", f"'{mark}' in the text: '{_short(example.text)}'")
                break
        if example.text != markup.collapse(example.text):
            add("example", subject, "E14", f"spaces are not single: '{_short(example.text)}'")
        sources("example", subject, example.source)
        if example.id not in lexicon.usages:
            add("example", subject, "E14", "no sense uses the example")
        shown = tuple(lexicon.translations[language].get(example.id, "") for language in lexicon.translations)
        if not any(shown):
            add("example", subject, "E16", "no translation in any language")
        identity = (example.text, example.source) + shown
        if identity in identities:
            add("example", subject, "E14", f"same text, source and translation as {identities[identity]}")
        identities[identity] = example.id
    for example_id, usages in lexicon.usages.items():
        text = lexicon.examples[example_id].text
        for sense_id, usage in usages.items():
            subject = f"{example_id} {lexicon.key(sense_id)}"
            keyword = lexicon.word_of(sense_id).spelling
            items = usage.start.split(separator)
            if not usage.start or not all(NUMBER.match(item) for item in items) or not NUMBER.match(usage.length):
                add("usage", subject, "E15", f"start '{usage.start}' and length '{usage.length}' are positive whole numbers")
                continue
            starts = [int(item) for item in items]
            if starts != sorted(starts):
                add("usage", subject, "E15", f"the positions '{usage.start}' are not in order")
            if int(usage.length) != len(keyword.split(" ")):
                add("usage", subject, "E15", f"length {usage.length}, but '{keyword}' has {len(keyword.split(' '))} words")
                continue
            try:
                markup.blank(text, keyword, starts, int(usage.length))
            except CiteError as error:
                add("usage", subject, "E15", str(error))
    for language, translations in lexicon.translations.items():
        table = config.tables["translation"].instance(language)
        for example_id, text in translations.items():
            if not text:
                add(table, example_id, "E16", "no text")
            for mark in UNTYPABLE:
                if mark in text:
                    add(table, example_id, "E16", f"'{mark}' in '{_short(text)}'")
                    break
            if text != markup.collapse(text):
                add(table, example_id, "E16", f"spaces are not single: '{_short(text)}'")

    # Links of words of another language.
    for language, links in lexicon.links.items():
        table = config.tables["link"].instance(language)
        for link in links.values():
            if not LINK_TERM.match(link.term):
                add(table, link.term, "E17", "a linked word is written in lowercase letters")
            elif link.term in terms_of.get(language, set()):
                add(table, link.term, "E17", "the word is already a term of a sense")
            senses = link.senses.split(separator) if link.senses else []
            if not senses:
                add(table, link.term, "E17", "no sense")
            if len(set(senses)) != len(senses):
                add(table, link.term, "E17", "a sense is named twice")
            sources(table, link.term, link.source)
            untypable(table, link.term, "note", link.note, marks=True)

    for kind, subject, source, text in lexicon.notes:
        if not subject:
            add("note", kind, "E20", f"no subject: '{_short(text)}'")

    found.extend(language_lexicons(config, lexicon))

    # Patterns of word building and spelling.
    affixes = {
        lexicon.word_of(sense_id).spelling for sense_id, sense in lexicon.senses.items()
        if sense.type in ("prefix", "suffix") and lexicon.active(sense_id)
    }
    for kind, form, result, context, note in lexicon.patterns:
        def wrong(detail: str) -> None:
            add("pattern", f"{kind} {form}", "E22", detail)
        if not note:
            wrong("a pattern says in its note what it does")
        if kind == "stem":
            if not (form and result and context) or form == result:
                wrong("a stem pattern has a form, a different result and the affix it stands before")
            for affix in markup.split_list(context):
                if affix not in affixes:
                    wrong(f"'{affix}' is not a word with an active prefix or suffix sense")
        elif kind == "double":
            if form not in config.types or result or context:
                wrong("a double pattern names a type code as its form, and has no result or context")
        elif kind == "letter":
            if not re.fullmatch(r"[a-z]", form) or result or context:
                wrong("a letter pattern is one lowercase letter, with no result or context")
    return found


def language_lexicons(config: Config, lexicon: Lexicon) -> List[Finding]:
    """Findings on the lexicon of each language in its folder."""
    found: List[Finding] = []
    for language in config.languages:
        name = {table: config.tables[table].instance(language) for table in ("concept", "lang_sense", "lang_relation", "form", "equivalent")}
        if not any(table in lexicon.extra for table in name.values()):
            continue

        def add(table: str, subject: str, detail: str) -> None:
            found.append(Finding(name[table], subject, "E23", detail))

        concepts: Dict[str, str] = {}
        for concept, type_code, _, definition, origin in lexicon.extra.get(name["concept"], []):
            if concept in concepts:
                add("concept", concept, "the id occurs twice")
            concepts[concept] = type_code
            if type_code not in config.lexicon_types:
                add("concept", concept, f"'{type_code}' is not a part of speech of the lexicon")
            if not origin:
                add("concept", concept, "no origin: the release, or local")
        words: Set[str] = set()
        for word, concept, order in lexicon.extra.get(name["lang_sense"], []):
            words.add(word)
            if concept not in concepts:
                add("lang_sense", f"{word} {concept}", "names no concept")
            if not NUMBER.match(order):
                add("lang_sense", f"{word} {concept}", f"order '{order}' is not a positive whole number")
        for source, kind, target in lexicon.extra.get(name["lang_relation"], []):
            if kind not in config.lexicon_relations:
                add("lang_relation", f"{source} {kind}", f"'{kind}' is not a relation of the lexicon")
                continue
            ends = words if kind in ("antonym", "derivation", "pertains") else concepts
            for end in (source, target):
                if end not in ends:
                    add("lang_relation", f"{source} {kind} {target}", f"'{end}' is not a {'word' if ends is words else 'concept'} of the lexicon")
        for form, word in lexicon.extra.get(name["form"], []):
            if word not in words:
                add("form", form, f"'{word}' is not a word of the lexicon")
        for sense, concept, status, _ in lexicon.extra.get(name["equivalent"], []):
            subject = f"{sense} {concept}"
            if sense not in lexicon.senses or not lexicon.active(sense):
                add("equivalent", subject, "names no active Zolai sense")
            if concept not in concepts:
                add("equivalent", subject, "names no concept")
            if status not in config.sense_status:
                add("equivalent", subject, f"'{status}' is not a sense status")
    return found


def run(config: Config, data: Tables, problems: Optional[List[str]] = None) -> List[Finding]:
    """Every finding. The content is checked only when the structure is sound."""
    found = structure(config, data, problems)
    if any(finding.rule != "E01" for finding in found):
        return found
    found.extend(content(config, model.build(config, data)))
    if credits.stale(config):
        found.append(Finding("file", credits.NAME, "E21", "run: python3 -m assist cite credits --apply"))
    return found


def load(config: Config) -> Lexicon:
    """The model of the stored tables. Unsound tables stop the command."""
    data = tables.read_all(config)
    found = structure(config, data)
    if found:
        shown = "; ".join(finding.describe(config) for finding in found[:3])
        raise CiteError(
            f"the tables have {len(found)} structural errors, first: {shown}; see: python3 -m assist cite check"
        )
    return model.build(config, data)


def _short(text: str, limit: int = 48) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
