"""Tests of the cite tooling. Run from the repository root:

    python3 -m unittest discover -s assist/tests -t .
"""

from __future__ import annotations

import json
import re
import unittest

from assist.cite import config as configuration
from assist.cite import convert, markup, query, rules, words

CONFIG = configuration.load()
MAIN = CONFIG.data_name("dev-main")
BEH = CONFIG.data_name("noun-beh")


def rows_of(text: str, file: str = MAIN):
    lines = text.strip("\n").split("\n")
    return [markup.parse(line, file, n) for n, line in enumerate(lines, 1) if markup.is_row(line)]


def rule_ids(text: str, file: str = MAIN):
    return sorted({finding.rule for finding in rules.check_rows(CONFIG, rows_of(text, file))})


class ConfigurationTest(unittest.TestCase):
    def test_attributes_are_in_configured_order(self):
        orders = [attribute.order for attribute in CONFIG.attributes.values()]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(next(iter(CONFIG.attributes)), "t")

    def test_alias_and_file_requirements_use_listed_codes(self):
        for target in CONFIG.alias.values():
            self.assertIn(target["t"], CONFIG.types)
            if "c" in target:
                self.assertIn(target["c"], CONFIG.categories)
        for entry in CONFIG.files.values():
            for key, value in entry.get("require", {}).items():
                self.assertIn(value, CONFIG.types if key == "t" else CONFIG.categories)

    def test_attribute_examples_parse(self):
        for key, entry in CONFIG.raw["attribute"].items():
            match = markup.ATTRIBUTE.fullmatch(entry["example"])
            self.assertIsNotNone(match, key)
            self.assertEqual(match.group(1), key)

    def test_keyword_examples_match_the_pattern(self):
        for example in CONFIG.raw["keyword"]["example"]:
            self.assertRegex(example, CONFIG.keyword)

    def test_duplicate_key_is_rejected(self):
        with self.assertRaises(configuration.CiteError):
            json.loads('{"a": 1, "a": 2}', object_pairs_hook=configuration._reject_duplicates)


class MarkupTest(unittest.TestCase):
    def test_keyword_only_row(self):
        row = markup.parse("kipan")
        self.assertFalse(row.described)
        self.assertEqual(row.keyword, "kipan")

    def test_attributes_and_description(self):
        row = markup.parse("vantung = (t:n) (w:heaven) the promised land")
        self.assertEqual(row.keyword, "vantung")
        self.assertEqual(row.values(), {"t": "n", "w": "heaven"})
        self.assertEqual(row.text, "the promised land")
        self.assertFalse(row.text_before_attribute)

    def test_only_the_first_separator_splits(self):
        row = markup.parse("a = (t:part) (d:x = y)")
        self.assertEqual(row.keyword, "a")
        self.assertEqual(row.values()["d"], "x = y")

    def test_canonical_form(self):
        row = markup.parse("kipat=(e:a ~ cil)  early stage (w: begin / start) (t:v)")
        self.assertTrue(row.text_before_attribute)
        self.assertEqual(
            markup.canonical(CONFIG, row),
            "kipat = (t:v) (w:begin/start) (e:a ~ cil) early stage",
        )

    def test_canonical_translation_separator(self):
        row = markup.parse("khat = (t:num) (w:one) (e:ni ~|one day)")
        self.assertEqual(markup.canonical(CONFIG, row), "khat = (t:num) (w:one) (e:ni ~ | one day)")

    def test_row_with_structural_error_is_not_rewritten(self):
        for line in ("x = (t:n) (w:a) (note)", "x = (t:n) (w:a) (w:b)", "x = (t:n) (z:a)", "x ="):
            self.assertIsNone(markup.canonical(CONFIG, markup.parse(line)), line)

    def test_record(self):
        row = markup.parse("khat = (t:num) (w:one/first) (e:ni ~ | one day)", MAIN, 7)
        self.assertEqual(
            markup.record(CONFIG, row),
            {
                "keyword": "khat", "file": MAIN, "line": 7, "t": "num",
                "w": ["one", "first"], "e": [{"text": "ni ~", "translation": "one day"}],
            },
        )


class RuleTest(unittest.TestCase):
    CASES = {
        "E02": "Sote (Shoute) = (t:name) (w:Sote)",
        "E03": "vantung =",
        "E04": "vantungte = (t:n) (w:heavens) (plural form)",
        "E05": "vantung = (t:n) (w:heaven) (z:x)",
        "E06": "tua = (t:pron) (w:that) (w:those)",
        "E07": "suakta = (t:v) (w:get away//run away)",
        "E08": "saupi = (t:adjective) (w:long)",
        "E09": "Eden = (t:name) (c:garden) (w:Eden)",
        "E10": "mial = (t:adv)",
        "E11": "khat = (t:num) (w:one) (e:ni khat)",
        "E12": "hiah = (t:adv) (w:<here>)",
        "E13": "leh = (t:conj) (w:and) (s:ale)",
        "E14": "Sote = (t:name) (w:Sote) (v:Sho_ute)",
        "E15": "Eden = (t:name) (w:Eden) (r:Genesis 2)",
        "E17": "eden = (t:name) (w:Eden)",
        "E18": "khawlei = (t:see) (w:bear)",
        "F01": "vantung=(t:n) (w:heaven)",
        "F02": "vantung = (t:n)  (w:heaven)",
        "F03": "vantung = (w:heaven) (t:n)",
        "F04": "vantung = (t:n) the sky (w:heaven)",
    }

    def test_each_rule_is_reported(self):
        for rule, line in self.CASES.items():
            self.assertIn(rule, rule_ids(line), f"{rule}: {line}")

    def test_missing_type(self):
        self.assertIn("E08", rule_ids("vantung = (w:heaven)"))

    def test_placeholder_outside_example(self):
        self.assertIn("E11", rule_ids("Eden = (t:name) (w:Eden) ~ huan"))
        self.assertIn("E11", rule_ids("khat = (t:num) (w:one) (e:ni ~ | a | b)"))

    def test_duplicate(self):
        text = "gen = (t:v) (w:tell)\ngen = (t:v) (w:tell)"
        self.assertEqual(rule_ids(text), ["E16"])

    def test_variant_with_own_row(self):
        text = "Sote = (t:name) (w:Sote) (v:Shoute)\nShoute = (t:name) (w:Shoute)"
        self.assertIn("E14", rule_ids(text))

    def test_file_scope(self):
        self.assertEqual(rule_ids("Sote = (t:name) (w:Sote)", BEH), ["E19"])
        self.assertEqual(rule_ids("Sote = (t:name) (c:beh) (w:Sote)", BEH), [])
        self.assertEqual(rule_ids("Sote", BEH), [])

    def test_keyword_only_row_resolves_a_reference(self):
        self.assertEqual(rule_ids("ale\nleh = (t:conj) (w:and) (s:ale)"), [])

    def test_redirect(self):
        text = "khawlei-uikai = (t:n) (w:the Bear)\nkhawlei = (t:see) <khawlei-uikai>"
        self.assertEqual(rule_ids(text), [])

    def test_form_finding_matches_canonical_difference(self):
        for line in list(self.CASES.values()) + ["vantung = (t:n) (w:heaven)", "kipan", " kipan"]:
            row = markup.parse(line, MAIN, 1)
            canonical = markup.canonical(CONFIG, row)
            form = [f for f in rules.check_rows(CONFIG, [row]) if not f.is_error]
            self.assertEqual(bool(form), canonical is not None and canonical != line, line)

    def test_every_reported_rule_is_configured(self):
        for line in self.CASES.values():
            for finding in rules.check_rows(CONFIG, rows_of(line)):
                self.assertIn(finding.rule, CONFIG.rules)


class ConvertTest(unittest.TestCase):
    CASES = {
        "Abib=(t:names) (w:Abib)": "Abib = (t:name) (w:Abib)",
        "Aaron=(t:prm) (w:Aaron)": "Aaron = (t:name) (c:male) (w:Aaron)",
        "bilpi=(t:animal) (w:hare)": "bilpi = (t:n) (c:animal) (w:hare)",
        "tua=(t:pronoun) referring to a thing (w:that)": "tua = (t:pron) (w:that) referring to a thing",
        "vantungte=(t:n) (w:heavens) (plural form of <vantung>)":
            "vantungte = (t:n) (w:heavens) plural form of <vantung>",
        "mial=(t:adv) without being able to see": "mial = (t:adv) (d:without being able to see)",
        "singnai=(t:n) (w:honeydew) ??": "singnai = (t:n) (w:honeydew) (q:?)",
        "kipan": "kipan",
        "# comment": "# comment",
        "": "",
    }

    def test_conversion(self):
        for old, new in self.CASES.items():
            self.assertEqual(convert.convert_line(CONFIG, old), new)

    def test_conversion_is_idempotent(self):
        for new in list(self.CASES.values()) + ["khawlei = (t:see) <khawlei-uikai>"]:
            self.assertEqual(convert.convert_line(CONFIG, new), new)

    def test_row_needing_an_editor_is_kept(self):
        line = "x=(t:n) (w:a) (w:b)"
        self.assertEqual(convert.convert_line(CONFIG, line), line)

    def test_parentheses_inside_prose_are_left_for_an_editor(self):
        line = "sak=(t:ppm) marker of future action (as in will, shall) and state"
        converted = convert.convert_line(CONFIG, line)
        self.assertIn("E04", rule_ids(converted))


class WordsTest(unittest.TestCase):
    def test_models(self):
        found = list(words.tokens("A kipat cil-in Pasian’ thu, ama' 144 om hen! Bang hiam?"))
        self.assertIn(("plain", "A", True), found)
        self.assertIn(("plain", "cil", False), found)
        self.assertIn(("plain", "in", False), found)
        self.assertIn(("dash", "cil-in", False), found)
        self.assertIn(("apostrophe", "Pasian'", False), found)
        self.assertIn(("apostrophe", "ama'", False), found)
        self.assertIn(("number", "144", False), found)
        self.assertIn(("exclamation", "hen!", False), found)
        self.assertIn(("plain", "Bang", True), found)
        self.assertIn(("question", "hiam?", False), found)

    def test_closing_quotation_mark_is_not_an_apostrophe(self):
        found = list(words.tokens("‘Na ne kei ding hi,’ ci hi."))
        self.assertFalse([token for token in found if token[0] == "apostrophe"])

    def test_json_layout_round_trips(self):
        document = {
            "language": "ctd", "model": "plain", "identify": ["3561"], "count": 2,
            "word": [{"w": "a", "n": 3, "r": "1.1.1"}, {"w": "hi", "n": 1, "r": "1.1.1"}],
        }
        text = words.to_json(document)
        self.assertEqual(json.loads(text), document)
        self.assertIn('\n    {"w": "a", "n": 3, "r": "1.1.1"},\n', text)
        self.assertEqual(json.loads(words.to_json(dict(document, word=[], count=0)))["word"], [])


class QueryTest(unittest.TestCase):
    ROWS = rows_of(
        "vantung = (t:n) (w:heaven)\n"
        "vantung = (t:n) (w:sky)\n"
        "Pasian = (t:n) (w:God)\n"
        "pasian = (t:n) (w:god)\n"
        "Sote = (t:name) (c:beh) (w:Sote) (v:Shoute)\n"
        "tungah = (t:prep) (w:above/on top of)"
    )

    def test_exact_keyword_is_preferred(self):
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "vantung")], [1, 2])
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "pasian")], [4])

    def test_keyword_ignoring_case_and_variant(self):
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "VANTUNG")], [1, 2])
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "Shoute")], [5])

    def test_english_term(self):
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "God", english=True)], [3])
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "top", english=True)], [6])
        self.assertEqual(query.lookup(CONFIG, self.ROWS, "hell", english=True), [])


class DocumentTest(unittest.TestCase):
    """Markup.md repeats the configuration; the two are kept identical."""

    @classmethod
    def setUpClass(cls):
        cls.text = (CONFIG.directory / "Markup.md").read_text(encoding="utf-8")

    def cell(self, text: str) -> str:
        return text.replace("|", "\\|")

    def test_every_code_and_description_is_documented(self):
        raw = CONFIG.raw
        for table in ("attribute", "type", "category"):
            for code, entry in raw[table].items():
                self.assertIn(f"| `{code}` |", self.text, f"{table} {code}")
                self.assertIn(self.cell(entry["description"]), self.text, f"{table} {code}")
        for entry in raw["rule"]:
            self.assertIn(f"| {entry['id']} | {entry['level']} | {entry['name']} |", self.text)
            self.assertIn(self.cell(entry["description"]), self.text, entry["id"])
        for old, target in raw["alias"]["type"].items():
            new = " ".join(f"`({key}:{value})`" for key, value in target.items())
            self.assertIn(f"| `(t:{old})` | {new} |", self.text)
        self.assertIn(raw["keyword"]["pattern"], self.text)

    def test_valid_examples_pass(self):
        block = self.text.split("Valid rows:")[1].split("```text\n")[1].split("```")[0]
        self.assertEqual(rules.check_rows(CONFIG, rows_of(block)), [])

    def test_invalid_examples_break_the_stated_rule(self):
        block = self.text.split("Valid rows:")[1].split("```text\n")[1].split("```")[0]
        cases = re.findall(r"^\| `(.+?)` \| ([EF]\d\d) \|", self.text.split("Invalid rows:")[1], re.M)
        self.assertGreaterEqual(len(cases), 10)
        for line, rule in cases:
            line = line.replace("\\|", "|")
            keyword = line.split("=")[0].strip().lower()
            context = [row for row in rows_of(block) if row.keyword.lower() != keyword]
            found = rules.check_rows(CONFIG, context + [markup.parse(line, MAIN, 999)])
            self.assertEqual(sorted({finding.rule for finding in found}), [rule], line)


if __name__ == "__main__":
    unittest.main()
