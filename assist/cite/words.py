"""Word lists generated from the Bible translations.

Each list holds every distinct written form of one model with its number of
occurrences and the first verse where it occurs, most frequent first.

A form that starts a sentence is counted under its lowercase spelling when,
inside sentences, the lowercase spelling is more frequent than the spelling
as written; otherwise it is counted as written. Names therefore keep their
capital and ordinary words lose the capital that only marks the start of a
sentence.

A right single quotation mark directly after a letter is read as an
apostrophe and written as a straight one; after punctuation it is a closing
quotation mark.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Dict, Iterator, List, Tuple

from assist.cite import bible
from assist.cite.config import CiteError, Config

WRITTEN = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*'?|\d+")
LETTERS = re.compile(r"[^\W\d_]+")
CURLY_APOSTROPHE = re.compile(r"(?<=[^\W\d_])\u2019")
SENTENCE_END = set(".!?:;“‘\"(")
FOLDED_MODELS = ("plain", "dash", "apostrophe")

Token = Tuple[str, str, bool]


def tokens(text: str) -> Iterator[Token]:
    """Yield (model, form, starts_sentence) for every form in a verse text."""
    text = CURLY_APOSTROPHE.sub("'", text)
    previous_end = 0
    first = True
    for match in WRITTEN.finditer(text):
        form = match.group()
        gap = text[previous_end:match.start()]
        initial = first or any(character in SENTENCE_END for character in gap)
        first = False
        previous_end = match.end()
        following = text[match.end():match.end() + 1]
        if form.isdigit():
            yield "number", form, False
            continue
        for index, part in enumerate(LETTERS.findall(form)):
            yield "plain", part, initial and index == 0
        if "-" in form:
            yield "dash", form, initial
        if "'" in form:
            yield "apostrophe", form, initial
        if following == "!":
            yield "exclamation", form + "!", False
        if following == "?":
            yield "question", form + "?", False


def build(config: Config, language: str) -> Dict[str, Dict]:
    """Word lists of one language, keyed by model."""
    settings = config.raw["word"]
    if language not in settings["language"]:
        raise CiteError(
            f"no word list is configured for '{language}'; "
            f"configured: {', '.join(settings['language'])}"
        )
    identifies: List[str] = settings["language"][language]
    models = list(settings["model"])
    inside: Dict[str, Counter] = {model: Counter() for model in models}
    starting: Dict[str, Counter] = {model: Counter() for model in models}
    first_seen: Dict[Tuple[str, str], str] = {}
    for identify in identifies:
        data = bible.load(config, identify)
        found = bible.language(data)
        if found != language:
            raise CiteError(
                f"translation '{identify}' is in '{found}', but is listed under '{language}'"
            )
        for book, chapter, verse, text in bible.verses(data, identify):
            for model, form, initial in tokens(text):
                if model not in inside:
                    continue
                (starting if initial else inside)[model][form] += 1
                first_seen.setdefault((model, form), f"{book}.{chapter}.{verse}")

    result: Dict[str, Dict] = {}
    for model in models:
        counts = Counter(inside[model])
        first: Dict[str, str] = {form: first_seen[(model, form)] for form in counts}
        for form, number in starting[model].items():
            lowered = form[0].lower() + form[1:]
            fold = model in FOLDED_MODELS and inside[model][lowered] > inside[model][form]
            target = lowered if fold else form
            counts[target] += number
            reference = first_seen[(model, form)]
            if target not in first or _order(reference) < _order(first[target]):
                first[target] = reference
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        result[model] = {
            "language": language,
            "model": model,
            "identify": identifies,
            "count": len(ordered),
            "word": [{"w": form, "n": number, "r": first[form]} for form, number in ordered],
        }
    return result


def _order(reference: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in reference.split("."))


def to_json(document: Dict) -> str:
    """JSON with one word per line, so a change shows as a small diff."""
    head = {key: value for key, value in document.items() if key != "word"}
    lines = json.dumps(head, ensure_ascii=False, indent=2).rstrip("}").rstrip()
    words = ",\n".join("    " + json.dumps(entry, ensure_ascii=False) for entry in document["word"])
    body = f'\n  "word": [\n{words}\n  ]\n' if words else '\n  "word": []\n'
    return f"{lines},{body}}}\n"


def read(config: Config, language: str, model: str) -> Dict:
    """A generated word list. A missing or old-format file raises CiteError."""
    path = config.word_path(language, model)
    hint = "run: python3 -m assist cite words --apply"
    if not path.is_file():
        raise CiteError(f"word list not found: {path}; {hint}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CiteError(f"word list {path.name} is not valid JSON: {error}") from error
    words = document.get("word") if isinstance(document, dict) else None
    if not isinstance(words, list) or (words and not isinstance(words[0], dict)):
        raise CiteError(f"word list {path.name} is in the old format; {hint}")
    return document
