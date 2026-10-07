"""The rows of a word written as a markup file, with the context an editor needs."""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from assist.cite import importer, markup, render
from assist.cite.config import CiteError
from assist.cite.lexicon import Lexicon


class Context:
    """What points at each word and sense: relations, links in prose, linked words of other languages."""

    def __init__(self, lexicon: Lexicon) -> None:
        self.lexicon = lexicon
        self.relations: Dict[str, List[Tuple[str, str]]] = {}
        for source, relations in lexicon.relations.items():
            for relation in relations:
                self.relations.setdefault(relation.to, []).append((relation.kind, source))
        self.prose: Dict[str, List[str]] = {}
        for glosses in lexicon.gloss.values():
            for sense_id, gloss in glosses.items():
                for inner in markup.XREF.findall(f"{gloss.definition} {gloss.text}"):
                    for target in markup.xref_targets(inner):
                        self.prose.setdefault(target, []).append(sense_id)
        self.links: Dict[str, List[Tuple[str, str]]] = {}
        for language, links in lexicon.links.items():
            for link in links.values():
                for sense_id in markup.split_list(link.senses):
                    self.links.setdefault(sense_id, []).append((language, link.term))

    def comments(self, word_id: str) -> List[str]:
        lexicon = self.lexicon
        word = lexicon.words[word_id]
        senses = lexicon.senses_of.get(word_id, [])
        examples = sum(len(lexicon.shown_by.get(sense_id, [])) for sense_id in senses)
        lines = [
            f"# word {word.id} '{word.spelling}', {lexicon.config.word_status[word.status]}; "
            f"senses {len(senses)}, examples {examples}"
        ]
        for target in [word_id] + senses:
            name = lexicon.name(target)
            sense = lexicon.senses.get(target)
            if sense:
                lines.append(f"# {name} is {target}, set {sense.set}")
            named = [f"({kind}) of {lexicon.name(source)}" for kind, source in sorted(self.relations.get(target, []))]
            if named:
                lines.append(f"# {name} is named by: {', '.join(named)}")
            linked = sorted({lexicon.key(sense_id) for sense_id in self.prose.get(name, [])})
            if linked:
                lines.append(f"# <{name}> is linked in the prose of: {', '.join(linked)}")
            words = [f"{term} ({language})" for language, term in sorted(self.links.get(target, []))]
            if words:
                lines.append(f"# {name} is the closest sense of: {', '.join(words)}")
        return lines

    def related(self, word_id: str) -> List[str]:
        """Words one step away: targets and sources of relations, words linked in the prose either way."""
        lexicon = self.lexicon
        found: Set[str] = set()

        def add(target: str) -> None:
            found.add(lexicon.senses[target].word if target in lexicon.senses else target)

        for target in [word_id] + lexicon.senses_of.get(word_id, []):
            for relation in lexicon.relations.get(target, []):
                add(relation.to)
            for _, source in self.relations.get(target, []):
                add(source)
            for sense_id in self.prose.get(lexicon.name(target), []):
                add(sense_id)
            for glosses in lexicon.gloss.values():
                gloss = glosses.get(target)
                for inner in markup.XREF.findall(f"{gloss.definition} {gloss.text}") if gloss else []:
                    for item in markup.xref_targets(inner):
                        parts = markup.split_key(item)
                        linked = lexicon.spelling.get(parts[0] if parts else item)
                        if linked:
                            found.add(linked)
        found.discard(word_id)
        return sorted(found, key=lambda other: (lexicon.words[other].spelling.casefold(), other))


def text(lexicon: Lexicon, spellings: List[str], related: bool = False) -> str:
    """The markup file of the words, each under its version stamp and context comments."""
    context = Context(lexicon)
    words: List[str] = []
    for spelling in spellings:
        word_id = lexicon.spelling.get(spelling)
        if word_id is None:
            raise CiteError(f"'{spelling}' is not a word of the lexicon; see: python3 -m assist cite lookup {spelling}")
        for found in [word_id] + (context.related(word_id) if related else []):
            if found not in words:
                words.append(found)
    blocks: List[str] = []
    for word_id in words:
        lines = render.word_lines(lexicon, word_id)
        stamp = importer.stamp_line(lexicon.words[word_id].spelling, render.version(lines))
        blocks.append("\n".join([stamp] + context.comments(word_id) + lines))
    return "\n\n".join(blocks) + "\n"
