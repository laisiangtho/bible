"""Tests of the cite tooling. Run from the repository root:

    python3 -m unittest discover -s assist/tests -t .
"""

from __future__ import annotations

import json
import re
import unittest

from assist.cite import config as configuration
from assist.cite import convert, credits, examples, index, markup, query, rules, store, upgrade, words

CONFIG = configuration.load()
MAIN = CONFIG.data_name("draft")
BEH = CONFIG.data_name("noun-beh")


def rows_of(text: str, file: str = MAIN):
    lines = text.strip("\n").split("\n")
    return [markup.parse(line, file, n) for n, line in enumerate(lines, 1) if markup.is_row(line)]


def numbered(text: str) -> str:
    """The rows with a sense number added where a described row has none."""
    counts = {}
    lines = []
    for line in text.strip("\n").split("\n"):
        if "=" in line and "(i:" not in line and "(t:see)" not in line and "(t:todo)" not in line:
            keyword = line.split("=")[0].strip()
            counts[keyword] = counts.get(keyword, 0) + 1
            head, rest = line.split("=", 1)
            gap = rest[: len(rest) - len(rest.lstrip())]
            line = f"{head}={gap}(i:{counts[keyword]}) {rest.lstrip()}" if rest.strip() else line
        lines.append(line)
    return "\n".join(lines)


def rule_ids(text: str, file: str = MAIN):
    return sorted({finding.rule for finding in rules.check_rows(CONFIG, rows_of(numbered(text), file))})


def example_rows(text: str, file: str = "examples"):
    return rows_of(text, file)


def example_rule_ids(rows: str, examples_text: str):
    found = rules.check_rows(CONFIG, rows_of(rows), example_rows(examples_text))
    return sorted({finding.rule for finding in found})


class ConfigurationTest(unittest.TestCase):
    def test_attributes_are_in_configured_order(self):
        orders = [attribute.order for attribute in CONFIG.attributes.values()]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(list(CONFIG.attributes)[:2], ["i", "t"])

    def test_alias_and_file_requirements_use_listed_codes(self):
        for target in CONFIG.alias.values():
            self.assertIn(target["t"], CONFIG.types)
            if "c" in target:
                self.assertIn(target["c"], CONFIG.categories)
        for entry in CONFIG.files.values():
            for key, value in entry.get("require", {}).items():
                self.assertIn(value, CONFIG.types if key == "t" else CONFIG.categories)

    def test_file_templates_name_distinct_files(self):
        self.assertEqual(CONFIG.data_name("core"), "ctd-core.cite")
        self.assertEqual(CONFIG.example_name("core"), "ctd-core.example.cite")
        self.assertEqual(CONFIG.translation_name("mya"), "ext/ctd-mya.cite")

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
        row = markup.parse("kipat=(s:kipan / kisin)  early stage (w: begin / start) (t:v)(i:1)")
        self.assertTrue(row.text_before_attribute)
        self.assertEqual(
            markup.canonical(CONFIG, row),
            "kipat = (i:1) (t:v) (w:begin/start) (s:kipan/kisin) early stage",
        )

    def test_canonical_example_row(self):
        row = markup.parse("khat.1=ni ~|one day  (r: 1.1.5)")
        self.assertEqual(markup.canonical_example(row), "khat.1 = ni ~ | one day (r:1.1.5)")
        self.assertIsNone(markup.canonical_example(markup.parse("khat.1 = ni ~")))

    def test_sense_key(self):
        self.assertEqual(markup.split_key("ahih hangin.12"), ("ahih hangin", "12"))
        self.assertIsNone(markup.split_key("khat"))
        self.assertIsNone(markup.split_key("khat.0"))
        self.assertEqual(markup.row_key(markup.parse("khat = (i:2) (t:num) (w:first)")), "khat.2")
        self.assertEqual(markup.row_key(markup.parse("khat")), "")

    def test_row_with_structural_error_is_not_rewritten(self):
        for line in ("x = (t:n) (w:a) (note)", "x = (t:n) (w:a) (w:b)", "x = (t:n) (z:a)", "x ="):
            self.assertIsNone(markup.canonical(CONFIG, markup.parse(line)), line)

    def test_record(self):
        row = markup.parse("khat = (i:1) (t:num) (w:one/first)", MAIN, 7)
        shown = [markup.example(markup.parse("khat.1 = ni ~ | one day (r:1.1.5)"))]
        self.assertEqual(
            markup.record(CONFIG, row, shown),
            {
                "keyword": "khat", "file": MAIN, "line": 7, "key": "khat.1", "i": 1, "t": "num",
                "w": ["one", "first"],
                "example": [{"text": "ni ~", "translation": "one day", "r": ["1.1.5"]}],
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
        "E11": "khat = (t:num) (w:one) ni ~",
        "E12": "hiah = (t:adv) (w:<here>)",
        "E13": "leh = (t:conj) (w:and) (s:ale)",
        "E14": "Sote = (t:name) (w:Sote) (v:Sho_ute)",
        "E15": "Eden = (t:name) (w:Eden) (r:Genesis 2)",
        "E17": "eden = (t:name) (w:Eden)",
        "E18": "khawlei = (t:see) (w:bear)",
        "E22": "sum = (t:n) (f:finance) (w:money)",
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
        self.assertIn("E11", rule_ids("khat = (t:num) (w:one) (d:one | first)"))

    def test_sense_number(self):
        self.assertEqual(rule_ids("khat = (t:num) (w:one)\nkhat = (t:num) (w:first)"), [])
        text = "khat = (i:1) (t:num) (w:one)\nkhat = (i:1) (t:num) (w:first)"
        self.assertEqual(sorted({f.rule for f in rules.check_rows(CONFIG, rows_of(text))}), ["E21"])
        for line in ("khat = (t:num) (w:one)", "khat = (i:0) (t:num) (w:one)", "khat = (i:x) (t:num) (w:one)"):
            self.assertEqual([f.rule for f in rules.check_rows(CONFIG, rows_of(line))], ["E21"], line)
        self.assertEqual(rules.check_rows(CONFIG, rows_of("khat = (t:todo) (q:unclear)")), [])

    def test_reference_forms(self):
        for value in ("1.1.1", "66.22.21", "1.2.4-6", "zai", "zai:market", "zai:a number of"):
            self.assertEqual(rule_ids(f"sum = (t:n) (w:money) (r:{value})"), [], value)
        for value in ("67.1.1", "Genesis 2", "book:12", "zai:", "zai:a/b"):
            self.assertIn("E15", rule_ids(f"sum = (t:n) (w:money) (r:{value})"), value)

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


class ExampleRuleTest(unittest.TestCase):
    ROWS = "khat = (i:1) (t:num) (w:one)\nkhat = (i:2) (t:num) (w:first)"

    def test_valid_example(self):
        self.assertEqual(example_rule_ids(self.ROWS, "khat.1 = ni ~ | one day (r:1.1.5)\nkhat.2 = ni ~ ni | the first day"), [])

    def test_each_rule_is_reported(self):
        cases = {
            "E03": "khat.1",
            "E04": "khat.1 = ni ~ (one) | one day",
            "E05": "khat.1 = ni ~ | one day (q:sure)",
            "E11": "khat.1 = ni khat | one day",
            "E12": "khat.1 = ni ~ | one <ni>",
            "E15": "khat.1 = ni ~ | one day (r:Genesis 1)",
            "E16": "khat.1 = ni ~ | one day\nkhat.1 = Ni ~ | a day",
            "E20": "khat.1 = ni ~",
            "E23": "khat.3 = ni ~ | one day",
            "F02": "khat.1 = ni ~|one day",
        }
        for rule, text in cases.items():
            self.assertEqual(example_rule_ids(self.ROWS, text), [rule], text)
        self.assertEqual(example_rule_ids(self.ROWS, "khat = ni ~ | one day"), ["E23"])
        self.assertEqual(example_rule_ids(self.ROWS, "khat.1 = ni ~ | a | b"), ["E11"])

    def test_translation_rows(self):
        def ids(text):
            found = rules.check_rows(CONFIG, rows_of(self.ROWS), (), rows_of(text, "ext/ctd-mya.cite"))
            return sorted({finding.rule for finding in found})

        self.assertEqual(ids("khat.1 = (w:တစ်)\nkhat.2 = (w:ပထမ) (d:x)"), [])
        self.assertEqual(ids("khat.9 = (w:တစ်)"), ["E23"])
        self.assertEqual(ids("khat.1 = (t:num) (w:တစ်)"), ["E05"])
        self.assertEqual(ids("khat.1 = (w:တစ်)\nkhat.1 = (w:တစ်)"), ["E16"])
        self.assertEqual(ids("khat.1 = တစ်"), ["E04", "E10"])


class UpgradeTest(unittest.TestCase):
    def data(self, lexicon: str, side: str = ""):
        file = store.DataFile("draft", MAIN, CONFIG.data_path("draft"), "lexicon", lexicon.split("\n"))
        files = [file]
        sides = []
        if side:
            sides.append(store.DataFile(
                "draft", CONFIG.example_name("draft"), CONFIG.example_path("draft"), "example", side.split("\n")
            ))
        return store.Data(files, sides, [])

    def locate(self, keyword, zolai, references):
        return "1.1.5" if zolai.strip() == "ni ~" and "1.1.5" in references else None

    def lines(self, changes):
        return {file.name: lines for file, lines in changes.items()}

    def test_numbers_and_examples(self):
        data = self.data(
            "# head\nkhat = (t:num) (w:one) (e:ni ~ | one day/mi ~ | one man) (r:1.1.5/1.2.1)\n"
            "khat = (i:4) (t:num) (w:first)\nkhat = (t:num) (w:single)\nkipan\nx = (t:see) <khat>"
        )
        changed = self.lines(upgrade.upgrade(CONFIG, data, self.locate))
        self.assertEqual(changed[MAIN], [
            "# head",
            "khat = (i:5) (t:num) (w:one) (r:1.2.1)",
            "khat = (i:4) (t:num) (w:first)",
            "khat = (i:6) (t:num) (w:single)",
            "kipan",
            "x = (t:see) <khat>",
        ])
        self.assertEqual(changed[CONFIG.example_name("draft")], [
            "khat.5 = ni ~ | one day (r:1.1.5)",
            "khat.5 = mi ~ | one man",
        ])

    def test_upgrade_is_idempotent_and_keeps_order(self):
        data = self.data(
            "khat = (i:1) (t:num) (w:one)\nnih = (i:1) (t:num) (w:two)",
            "# examples\nnih.1 = ni ~ | two days\nkhat.1 = ni ~ | one day",
        )
        changed = self.lines(upgrade.upgrade(CONFIG, data, self.locate))
        self.assertEqual(changed, {CONFIG.example_name("draft"): [
            "# examples", "khat.1 = ni ~ | one day", "nih.1 = ni ~ | two days",
        ]})
        data.examples[0].lines = changed[CONFIG.example_name("draft")]
        self.assertEqual(upgrade.upgrade(CONFIG, data, self.locate), {})

    def test_example_without_translation_stops_the_upgrade(self):
        with self.assertRaises(configuration.CiteError):
            upgrade.upgrade(CONFIG, self.data("khat = (t:num) (w:one) (e:ni ~)"), self.locate)

    def test_rename(self):
        data = self.data(
            "khat = (i:1) (t:num) (w:one) (s:pumkhat)\npumkhat = (i:1) (t:num) (w:one) (s:khat) see <khat>\n"
            "khatna = (i:1) (t:num) (w:first) (b:khat)\nkhat ni",
            "khat.1 = ni ~ | one day\nkhatna.1 = a ~ | the first",
        )
        changed = self.lines(upgrade.rename(CONFIG, data, "khat", "khaat"))
        self.assertEqual(changed[MAIN], [
            "khaat = (i:1) (t:num) (w:one) (s:pumkhat)",
            "pumkhat = (i:1) (t:num) (w:one) (s:khaat) see <khaat>",
            "khatna = (i:1) (t:num) (w:first) (b:khaat)",
            "khat ni",
        ])
        self.assertEqual(changed[CONFIG.example_name("draft")], [
            "khaat.1 = ni ~ | one day", "khatna.1 = a ~ | the first",
        ])
        with self.assertRaises(configuration.CiteError):
            upgrade.rename(CONFIG, data, "khat", "pumkhat")
        with self.assertRaises(configuration.CiteError):
            upgrade.rename(CONFIG, data, "missing", "khaat")


class MoveTest(unittest.TestCase):
    def data(self):
        def file(key, kind, text):
            name = CONFIG.data_name(key) if kind == "lexicon" else CONFIG.example_name(key)
            path = CONFIG.data_path(key) if kind == "lexicon" else CONFIG.example_path(key)
            return store.DataFile(key, name, path, kind, text.split("\n"))

        return store.Data(
            [
                file("core", "lexicon", "# core\nan = (i:1) (t:n) (w:food)\nnu = (i:2) (t:n) (w:aunt)"),
                file("draft", "lexicon", "inn = (i:1) (t:n) (w:house)\nnu = (i:1) (t:n) (w:mother)\nzu = (i:1) (t:n) (w:wine)"),
            ],
            [file("draft", "example", "inn.1 = ~ sungah | in the house\nnu.1 = ka ~ | my mother\nzu.1 = ~ dawn | drink wine")],
            [],
        )

    def test_senses_move_with_their_examples(self):
        data = self.data()
        changed = {file.name: lines for file, lines in upgrade.move(CONFIG, data, ["nu.1", "inn.1"], "core").items()}
        self.assertEqual(changed[CONFIG.data_name("core")], [
            "# core", "an = (i:1) (t:n) (w:food)", "inn = (i:1) (t:n) (w:house)",
            "nu = (i:2) (t:n) (w:aunt)", "nu = (i:1) (t:n) (w:mother)",
        ])
        self.assertEqual(changed[CONFIG.data_name("draft")], ["zu = (i:1) (t:n) (w:wine)"])
        self.assertEqual(changed[CONFIG.example_name("draft")], ["zu.1 = ~ dawn | drink wine"])
        self.assertEqual(changed[CONFIG.example_name("core")], ["inn.1 = ~ sungah | in the house", "nu.1 = ka ~ | my mother"])

    def test_unknown_key_and_no_change(self):
        with self.assertRaises(configuration.CiteError):
            upgrade.move(CONFIG, self.data(), ["nu.9"], "core")
        self.assertEqual(upgrade.move(CONFIG, self.data(), ["an.1"], "core"), {})


class IndexTest(unittest.TestCase):
    ROWS = rows_of(
        "Pasian = (i:1) (t:n) (w:God)\npasian = (i:1) (t:n) (w:god/idol)\n"
        "ze-et = (i:1) (t:v) (w:test) (v:zeet/ze et)\nkipan\nkipan = (i:1) (t:v) (w:begin)\nkisin"
    )

    def body(self, text):
        return [line for line in text.split("\n") if line and not line.startswith("#")]

    def test_keyword_index(self):
        self.assertEqual(self.body(index.keyword_index(CONFIG, self.ROWS)), [
            "kipan\tkipan.1", "kisin\tkisin", "pasian\tPasian.1\tpasian.1", "zeet\tze-et.1",
        ])

    def test_term_index(self):
        self.assertEqual(self.body(index.term_index(CONFIG, self.ROWS)), [
            "begin\tkipan.1", "god\tPasian.1\tpasian.1", "idol\tpasian.1", "test\tze-et.1",
        ])


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
        "tungah = (t:prep) (w:above/on top of)\n"
        "ze-et = (t:v) (w:test/tempt)\n"
        "Be-ersheba = (t:name) (c:city) (w:Beersheba)"
    )

    def test_exact_keyword_is_preferred(self):
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "vantung")], [1, 2])
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "pasian")], [4])

    def test_keyword_ignoring_case_and_variant(self):
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "VANTUNG")], [1, 2])
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "Shoute")], [5])

    def test_hyphen_space_and_apostrophe_are_ignored(self):
        for text in ("zeet", "ze et", "Ze-Et", "ze'et"):
            self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, text)], [7], text)
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "beersheba")], [8])
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "ze-et")], [7])

    def test_english_term(self):
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "God", english=True)], [3])
        self.assertEqual([row.number for row in query.lookup(CONFIG, self.ROWS, "top", english=True)], [6])
        self.assertEqual(query.lookup(CONFIG, self.ROWS, "hell", english=True), [])


class ExamplesTest(unittest.TestCase):
    def measure(self, line, text):
        shown = [markup.example(row) for row in rows_of(text)]
        return examples.measure(CONFIG, markup.parse(line), shown)

    def test_inflected_forms_count_for_a_term(self):
        self.assertTrue(examples.uses("ask", "he asked them"))
        self.assertTrue(examples.uses("go", "they went up"))
        self.assertTrue(examples.uses("gush out", "water gushed out"))
        self.assertFalse(examples.uses("ask", "he inquired of them"))

    def test_examples_are_counted_per_term(self):
        measured = self.measure(
            "dong = (i:1) (t:v) (w:ask/inquire)", "dong.1 = a ~ hi | he asked\ndong.1 = ka ~ hi | I asked"
        )
        self.assertEqual(measured.terms, (("ask", 2), ("inquire", 0)))
        self.assertEqual(measured.short, [("ask", 2), ("inquire", 0)])
        self.assertFalse(measured.complete)

    def test_three_examples_per_term_complete_a_row(self):
        measured = self.measure(
            "khat = (i:1) (t:num) (w:one)",
            "khat.1 = ni ~ | one day\nkhat.1 = mi ~ | one man\nkhat.1 = inn ~ | one house",
        )
        self.assertTrue(measured.complete)

    def test_names_are_not_measured(self):
        self.assertFalse(examples.measurable(CONFIG, markup.parse("Eden = (i:1) (t:name) (w:Eden)")))


class JoinTest(unittest.TestCase):
    ROWS = "a = (i:1) (t:part) (d:marks the third person)\nom = (i:1) (t:v) (w:be/exist)\n"

    def found(self, line):
        return {finding.rule for finding in rules.check_rows(CONFIG, rows_of(self.ROWS + line))}

    def test_joined_form_with_its_own_meaning(self):
        self.assertEqual(self.found("aom = (i:1) (t:v) (w:there is) (j:a/om)"), set())

    def test_respelling_may_leave_out_the_meaning(self):
        self.assertEqual(self.found("oom = (i:1) (t:v) (j:om)"), set())
        self.assertEqual(self.found("aom = (i:1) (t:v) (j:a/om)"), {"E10"})

    def test_parts_exist_and_differ_from_the_keyword(self):
        self.assertEqual(self.found("aom = (i:1) (t:v) (w:there is) (j:a/um)"), {"E13"})
        self.assertEqual(self.found("aom = (i:1) (t:v) (w:there is) (j:aom/om)"), {"E26"})

    def test_join_index(self):
        rows = rows_of(self.ROWS + "aom = (i:1) (t:v) (w:there is) (j:a/om)\noom = (i:1) (t:v) (j:om)")
        body = [line for line in index.join_index(CONFIG, rows).split("\n") if line and not line.startswith("#")]
        self.assertEqual(body, ["a\taom.1", "om\taom.1\toom.1"])


class MarkTest(unittest.TestCase):
    ROWS = "nu = (i:1) (t:n) (w:mother)\npa = (i:1) (t:n) (w:father)\npa = (i:2) (t:part) (d:marks a man)\n"

    def found(self, line):
        return {finding.rule for finding in rules.check_rows(CONFIG, rows_of(self.ROWS + line))}

    def test_links_and_mentions_pass(self):
        self.assertEqual(self.found("x = (i:1) (t:n) (w:parents) (d:<nu> with <pa>; {a nu leh a pa} is his parents)"), set())
        self.assertEqual(self.found("x = (i:1) (t:n) (w:parents) (d:<nu/pa> joined, see <pa.2> and {-pa})"), set())
        self.assertEqual(self.found("x = (i:1) (t:n) (w:parents) (q:draft, {x} beside <nu>) from {x}"), set())

    def test_link_to_a_missing_keyword_or_sense(self):
        self.assertEqual(self.found("x = (i:1) (t:n) (w:parents) (d:<nu/te>)"), {"E13"})
        self.assertEqual(self.found("x = (i:1) (t:n) (w:parents) (d:<pa.3>)"), {"E13"})

    def test_mention_of_a_keyword_with_a_row_is_a_link(self):
        self.assertEqual(self.found("x = (i:1) (t:n) (w:parents) (d:{nu} and more)"), {"E25"})

    def test_braces_are_balanced_and_only_in_prose(self):
        self.assertEqual(self.found("x = (i:1) (t:n) (w:parents) (d:{a nu)"), {"E25"})
        self.assertEqual(self.found("x = (i:1) (t:n) (w:{parents})"), {"E25"})
        self.assertEqual(self.found("x = (i:1) (t:n) (w:parents) (d:{} here)"), {"E25"})

    def test_segments_for_display(self):
        shown = [(part.kind, part.text) for part in markup.segments("<nu/pa>, as in {a nu leh a pa}.")]
        self.assertEqual(shown, [
            ("link", "nu"), ("text", "/"), ("link", "pa"), ("text", ", as in "),
            ("mention", "a nu leh a pa"), ("text", "."),
        ])

    def test_rename_follows_every_form_of_link(self):
        self.assertEqual(markup.relink("<nu/pa> and <pa.2> but {pa te}", "pa", "paa"), "<nu/paa> and <paa.2> but {pa te}")


class CreditsTest(unittest.TestCase):
    def test_every_source_is_credited(self):
        text = credits.build(CONFIG)
        for code, entry in CONFIG.sources.items():
            self.assertIn(f"### `{code}`: {entry['name']}", text)
        for identify in CONFIG.raw["bible"]["source"]:
            self.assertIn(f"| `{identify}` |", text)

    def test_the_file_matches_the_source_list(self):
        self.assertFalse(credits.stale(CONFIG))


class LinkTest(unittest.TestCase):
    ROWS = "nu = (i:1) (t:n) (w:mother)\npa = (i:1) (t:n) (w:father)"

    def found(self, line):
        links = [markup.parse(line, "ext/eng-ctd.cite", 1)]
        return {finding.rule for finding in rules.check_rows(CONFIG, rows_of(self.ROWS), links=links)}

    def test_valid_link(self):
        self.assertEqual(self.found("mom = nu.1 (r:moby:mother) (q:draft)"), set())
        self.assertEqual(self.found("parent = nu.1/pa.1"), set())

    def test_word_that_is_a_term_is_not_linked(self):
        self.assertEqual(self.found("mother = nu.1"), {"E24"})

    def test_unknown_or_repeated_sense_key(self):
        self.assertEqual(self.found("mom = nu.2"), {"E24"})
        self.assertEqual(self.found("mom = nu.1/nu.1"), {"E24"})

    def test_only_reference_and_query_are_allowed(self):
        self.assertIn("E05", self.found("mom = nu.1 (w:mother)"))
        self.assertIn("E15", self.found("mom = nu.1 (r:unknown:mother)"))

    def test_word_is_lowercase(self):
        self.assertIn("E02", self.found("Mom = nu.1"))

    def test_canonical_form(self):
        row = markup.parse("mom=nu.1 / pa.1 (q:draft)(r:moby:mother)")
        self.assertEqual(markup.canonical_link(CONFIG, row), "mom = nu.1/pa.1 (r:moby:mother) (q:draft)")

    def test_lookup_falls_back_to_the_link(self):
        rows = rows_of(self.ROWS)
        link, senses = query.linked(CONFIG, rows, [markup.parse("mom = nu.1")], "Mom")
        self.assertEqual([row.keyword for row in senses], ["nu"])
        self.assertIsNone(query.linked(CONFIG, rows, [], "mom"))

    def test_rename_follows_into_the_link_file(self):
        data = store.load(CONFIG)
        if not data.links:
            self.skipTest("no link file")
        key = markup.link_keys(data.link_rows()[0])[0]
        old = markup.split_key(key)[0]
        changes = upgrade.rename(CONFIG, data, old, old + "x")
        self.assertIn(data.links[0], changes)


class DocumentTest(unittest.TestCase):
    """Markup.md repeats the configuration; the two are kept identical."""

    @classmethod
    def setUpClass(cls):
        cls.text = (CONFIG.directory / "Markup.md").read_text(encoding="utf-8")

    def cell(self, text: str) -> str:
        return text.replace("|", "\\|")

    def test_every_code_and_description_is_documented(self):
        raw = CONFIG.raw
        for table in ("attribute", "type", "category", "field", "source", "translation"):
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

    def blocks(self):
        parts = self.text.split("Valid rows:")[1].split("```text\n")
        return parts[1].split("```")[0], parts[2].split("```")[0]

    def cases(self, title):
        table = self.text.split(title)[1].split("\n\n")[1]
        found = re.findall(r"^\| `(.+?)` \| ([EF]\d\d) \|", table, re.M)
        return [(line.replace("\\|", "|"), rule) for line, rule in found]

    def test_valid_examples_pass(self):
        block, side = self.blocks()
        self.assertEqual(rules.check_rows(CONFIG, rows_of(block), example_rows(side)), [])
        self.assertGreaterEqual(len(example_rows(side)), 5)

    def test_invalid_examples_break_the_stated_rule(self):
        block, _ = self.blocks()
        cases = self.cases("Invalid rows:")
        self.assertGreaterEqual(len(cases), 10)
        for line, rule in cases:
            keyword = line.split("=")[0].strip().lower()
            context = [row for row in rows_of(block) if row.keyword.lower() != keyword]
            found = rules.check_rows(CONFIG, context + [markup.parse(line, MAIN, 999)])
            self.assertEqual(sorted({finding.rule for finding in found}), [rule], line)

    def test_invalid_example_rows_break_the_stated_rule(self):
        block, side = self.blocks()
        cases = self.cases("Invalid example rows:")
        self.assertGreaterEqual(len(cases), 5)
        for line, rule in cases:
            given = example_rows(side) if rule == "E16" else []
            found = rules.check_rows(CONFIG, rows_of(block), given + [markup.parse(line, "examples", 999)])
            self.assertEqual(sorted({finding.rule for finding in found}), [rule], line)

    def test_data_passes_the_check_and_the_index_is_current(self):
        data = store.load(CONFIG)
        found = [finding for file in data.every_file() for finding in file.findings]
        found += rules.check_rows(CONFIG, data.rows(), data.example_rows(), data.translation_rows())
        self.assertEqual(found, [])
        self.assertEqual(index.stale(CONFIG, data.rows()), [])


if __name__ == "__main__":
    unittest.main()
