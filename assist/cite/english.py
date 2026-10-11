"""The lexicon of another language: concepts, the words that express them, their
relations and forms, and the equivalences between Zolai senses and concepts.

The English lexicon is imported from Open English WordNet (WN-LMF XML) and is
then data of the cite directory like any other: rows whose origin is the
upstream release are replaced by the next release; rows whose origin is
``local`` belong to this lexicon and are never replaced.
"""

from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from assist.cite.config import CiteError, Config

LOCAL = "local"
TABLES = ("concept", "lang_sense", "lang_relation", "form", "equivalent")
# WN-LMF relation types kept, by the kind they are stored as.
SYNSET_RELATIONS = {
    "hypernym": "broader", "similar": "similar", "also": "also", "holo_part": "part", "holo_member": "member",
    "holo_substance": "substance", "domain_topic": "topic", "entails": "entails", "causes": "causes",
}
SENSE_RELATIONS = {"antonym": "antonym", "derivation": "derivation", "pertainym": "pertains"}
WORD = re.compile(r"^[^\t\n\r]+$")
# Endings of inflected forms and what replaces them, by part of speech, as WordNet's morphy applies them.
DETACH = {
    "n": (("s", ""), ("ses", "s"), ("xes", "x"), ("zes", "z"), ("ches", "ch"), ("shes", "sh"), ("men", "man"),
          ("ies", "y")),
    "v": (("s", ""), ("ies", "y"), ("es", "e"), ("es", ""), ("ed", "e"), ("ed", ""), ("ing", "e"), ("ing", "")),
    "a": (("er", ""), ("est", ""), ("er", "e"), ("est", "e")),
}


def names(config: Config, language: str) -> Dict[str, str]:
    """Stored names of the lexicon tables of a language."""
    return {table: config.tables[table].instance(language) for table in TABLES}


@dataclass
class Release:
    """The rows of one upstream release."""

    label: str
    concepts: Dict[str, Tuple[str, str, str, str]] = field(default_factory=dict)
    senses: Set[Tuple[str, str, str]] = field(default_factory=set)
    relations: Set[Tuple[str, str, str]] = field(default_factory=set)
    forms: Set[Tuple[str, str]] = field(default_factory=set)


def _clean(text: Optional[str]) -> str:
    return " ".join((text or "").replace("\t", " ").split())


def read_release(path: Path) -> Release:
    """Concepts, senses, relations and forms of a WN-LMF file, plain or gzip."""
    if not path.is_file():
        raise CiteError(f"{path}: not a file")
    opener = gzip.open if path.suffix == ".gz" else open
    sense_word: Dict[str, str] = {}
    sense_relations: List[Tuple[str, str, str]] = []
    release: Optional[Release] = None
    entry_word = ""
    order: Dict[str, int] = {}
    with opener(path, "rb") as stream:
        try:
            for event, element in ElementTree.iterparse(stream, events=("start", "end")):
                tag = element.tag
                if event == "start":
                    if tag == "Lexicon":
                        label = f"{element.get('id', '')} {element.get('version', '')}".strip()
                        release = Release(label)
                    continue
                if release is None:
                    raise CiteError(f"{path}: no Lexicon element before the entries")
                if tag == "Lemma":
                    entry_word = _clean(element.get("writtenForm"))
                elif tag == "Form":
                    form = _clean(element.get("writtenForm"))
                    if form and form != entry_word:
                        release.forms.add((form, entry_word))
                elif tag == "Sense":
                    sense_id, synset = element.get("id", ""), element.get("synset", "")
                    sense_word[sense_id] = entry_word
                    order[entry_word] = order.get(entry_word, 0) + 1
                    release.senses.add((entry_word, synset, str(order[entry_word])))
                    for relation in element.findall("SenseRelation"):
                        kind = SENSE_RELATIONS.get(relation.get("relType", ""))
                        if kind:
                            sense_relations.append((sense_id, kind, relation.get("target", "")))
                elif tag == "LexicalEntry":
                    element.clear()
                elif tag == "Synset":
                    synset = element.get("id", "")
                    definition = _clean(element.findtext("Definition"))
                    release.concepts[synset] = (
                        element.get("partOfSpeech", ""), element.get("lexfile", ""), definition, release.label
                    )
                    for relation in element.findall("SynsetRelation"):
                        kind = SYNSET_RELATIONS.get(relation.get("relType", ""))
                        if kind:
                            release.relations.add((synset, kind, relation.get("target", "")))
                    element.clear()
        except ElementTree.ParseError as error:
            raise CiteError(f"{path}: not WN-LMF XML: {error}") from error
    if release is None:
        raise CiteError(f"{path}: no Lexicon element")
    # A sense relation is kept between words: the source word to the target word, by kind.
    for source, kind, target in sense_relations:
        if source in sense_word and target in sense_word and sense_word[source] != sense_word[target]:
            release.relations.add((sense_word[source], kind, sense_word[target]))
    bad = sorted(word for word, _, _ in release.senses if not WORD.match(word))
    if bad:
        raise CiteError(f"{path}: words that a table cannot hold: {', '.join(bad[:5])}")
    return release


@dataclass
class Update:
    """What an import of a release changes in the stored rows."""

    rows: Dict[str, List[Tuple[str, ...]]]
    added: Dict[str, int]
    removed: Dict[str, int]
    kept_local: int
    conflicts: List[str]


def update(stored: Dict[str, List[Tuple[str, ...]]], release: Release, table: Dict[str, str]) -> Update:
    """Replace every upstream row by the release, keep every local row.

    A local concept with the id of a concept of the release is a conflict: the
    upstream concept changed under a local edit, and is reported, not applied.
    """
    concepts_now = stored.get(table["concept"], [])
    local_concepts = {row[0]: row for row in concepts_now if row[4] == LOCAL}
    conflicts = [
        f"concept {cid}: edited locally; the release has '{release.concepts[cid][2][:60]}'"
        for cid in sorted(local_concepts) if cid in release.concepts
        and release.concepts[cid][:3] != local_concepts[cid][1:4]
    ]
    concepts = [row for row in concepts_now if row[4] == LOCAL] + [
        (cid,) + values for cid, values in release.concepts.items() if cid not in local_concepts
    ]
    known = {row[0] for row in concepts}

    def merge(name: str, upstream: Iterable[Tuple[str, ...]], is_local) -> List[Tuple[str, ...]]:
        mine = [row for row in stored.get(name, []) if is_local(row)]
        return sorted(set(mine) | set(upstream))

    local_ids = set(local_concepts)
    senses = merge(table["lang_sense"], release.senses, lambda row: row[1] in local_ids)
    words = {row[0] for row in senses}
    word_kinds = set(SENSE_RELATIONS.values())

    def sound(row: Tuple[str, ...]) -> bool:
        ends = words if row[1] in word_kinds else known
        return row[0] in ends and row[2] in ends

    relations = [
        row for row in merge(
            table["lang_relation"], release.relations,
            lambda row: row[1] not in word_kinds and (row[0] in local_ids or row[2] in local_ids),
        ) if sound(row)
    ]
    forms = merge(table["form"], release.forms, lambda row: False)
    forms = [row for row in forms if row[1] in words]
    rows = {
        table["concept"]: concepts, table["lang_sense"]: senses, table["lang_relation"]: relations,
        table["form"]: forms,
    }
    added = {name: len(set(rows[name]) - set(stored.get(name, []))) for name in rows}
    removed = {name: len(set(stored.get(name, [])) - set(rows[name])) for name in rows}
    return Update(rows, added, removed, len(local_concepts), conflicts)


def bases(word: str, part: str = "") -> List[str]:
    """Candidate base forms of an inflected English word, the word itself first."""
    word = word.casefold().strip()
    found = [word]
    for pos, endings in DETACH.items():
        if part and part != pos:
            continue
        for ending, replacement in endings:
            if word.endswith(ending) and len(word) > len(ending) + 1:
                candidate = word[: len(word) - len(ending)] + replacement
                tries = [candidate]
                if not replacement and ending in ("ing", "ed", "er", "est") and len(candidate) > 2 \
                        and candidate[-1] == candidate[-2] and candidate[-1] not in "aeiouls":
                    tries.append(candidate[:-1])
                found.extend(item for item in tries if item not in found)
    return found


# Types of the Zolai lexicon and the parts of speech of WordNet that can be the same meaning.
POS_OF_TYPE = {"n": ("n",), "name": ("n",), "v": ("v",), "adj": ("a", "s"), "adv": ("r",), "num": ("a", "s", "n")}
WORD_RE = re.compile(r"[a-z]+")
STOP = set("a an the of to in on at by for with and or as is be it its from that this which who what not no into".split())


def _words(text: str) -> Set[str]:
    return {w for w in WORD_RE.findall(text.casefold()) if w not in STOP and len(w) > 2}


@dataclass(frozen=True)
class Match:
    sense: str
    concept: str
    why: str


def propose(
    senses: Sequence[Tuple[str, str, str, str]],
    members: Dict[str, List[Tuple[str, str, str]]],
    concepts: Dict[str, Tuple[str, str, str]],
) -> Tuple[List[Match], Dict[str, int]]:
    """Equivalences of Zolai senses with concepts, found through the English terms.

    ``senses`` holds (sense id, type, terms, definition); ``members`` maps a
    lowercase English word to its (concept, order, word as written); ``concepts`` maps a
    concept id to (part of speech, members joined, definition). A sense gets a
    concept only when one concept is clearly best: it holds a term, written with
    a capital for a name and without one otherwise, and
    either it is the only one of the right part of speech and shares a word of
    the definition or a further term, or more of the terms and definition words
    point at it than at any other. A sample judged by hand found about 81% the
    same meaning, 16% a near meaning and 3% wrong; the equivalences are stored
    with the status low.
    """
    found: List[Match] = []
    counts = {"matched": 0, "unconfirmed": 0, "ambiguous": 0, "no concept": 0, "no term": 0}
    for sense_id, type_code, terms_value, definition in senses:
        terms = [t.strip().casefold() for t in terms_value.split("/") if t.strip()]
        allowed = POS_OF_TYPE.get(type_code)
        if not terms or not allowed:
            counts["no term"] += 1
            continue
        candidates: List[str] = []
        for position, term in enumerate(terms):
            for base in bases(term)[:1] if " " in term else bases(term):
                proper = type_code == "name"
                candidates = [
                    c for c, _, written in members.get(base, [])
                    if concepts[c][0] in allowed and written[:1].isupper() == proper
                ]
                if candidates:
                    break
            if candidates:
                terms = terms[position:] + terms[:position]
                break
        if not candidates:
            counts["no concept"] += 1
            continue
        if len(candidates) == 1:
            concept = candidates[0]
            confirmed = (
                not definition
                or _words(definition) & _words(concepts[concept][2])
                or any(term in concepts[concept][1].split("/") for term in terms[1:])
            )
            if confirmed:
                found.append(Match(sense_id, concept, "the only concept of the term"))
                counts["matched"] += 1
            else:
                counts["unconfirmed"] += 1
            continue
        scores = []
        context = _words(definition)
        for concept in candidates:
            member_words = set(concepts[concept][1].split("/"))
            shared_terms = sum(term in member_words for term in terms[1:])
            shared_words = len(context & _words(concepts[concept][2]))
            scores.append((shared_terms * 2 + shared_words, shared_terms, concept))
        scores.sort(reverse=True)
        best, second = scores[0], scores[1]
        if best[1] >= 1 and best[0] >= second[0] + 2:
            found.append(Match(sense_id, best[2], f"{best[1]} more terms in the concept"))
            counts["matched"] += 1
        else:
            counts["ambiguous"] += 1
    return found, counts
