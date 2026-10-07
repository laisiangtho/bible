"""Tests of the format 3 tables. Run from the repository root:

    python3 -m unittest discover -s assist/tests -t .
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from assist.cite import config as configuration
from assist.cite import store
from assist.cite.config import CiteError
from assist.cite3 import convert, legacy, render, roundtrip, schema, tables

CONFIG = configuration.load()

LEXICON = """
ale
amaute = (i:1) (t:pron) (w:they) (j:amau/te) (q:draft)
amau = (i:1) (t:pron) (f:everyday) (w:they/them) (d:the third person plural; see <amaute>)
khut = (i:1) (t:n) (f:body) (w:hand) (a:khe) (r:pk:38) (q:draft, low confidence, one sentence) used of people
khut = (i:2) (t:v) (w:hold) (q:?)
khe = (i:1) (t:n) (w:foot/leg) (s:khut)
te = (i:1) (t:part) (d:plural marker)
Abde = (t:see) <khe>
anath = (t:todo) (q:draft, lowercase only)
"""
EXAMPLES = """
khut.1 = Ka ~ a na hi | my hand hurts (r:pk:38)
khe.1 = ka khut leh ka ~ | my hand and my foot (r:19.22.16)
khut.1 = ka ~ leh ka khe | my hand and my foot (r:19.22.16)
amaute.1 = ~ in a gen uh hi | they said it
te.1 = pau ~-~ hi | plural twice
"""
LINKS = """
arm = khut.1/khe.1 (r:moby:limb) (q:draft)
"""
NOTES = [
    ("concept", "# heading", "good morning", "", "no row"),
    ("book", "# heading", "siallei", "pk:176", "bare word list"),
]


def data_of(lexicon: str = LEXICON, examples: str = EXAMPLES, links: str = LINKS) -> store.Data:
    def file(key: str, kind: str, text: str) -> store.DataFile:
        return store.DataFile(key, f"{key}.{kind}", CONFIG.directory / f"{key}.{kind}", kind, text.strip("\n").split("\n"))

    return store.Data(
        [file("core", "lexicon", lexicon)], [file("core", "example", examples)], [], [file("link", "link", links)]
    )


class LegacyTest(unittest.TestCase):
    def test_status_and_remark_of_q(self) -> None:
        self.assertEqual(legacy.read_q(""), (2, ""))
        self.assertEqual(legacy.read_q("draft"), (2, ""))
        self.assertEqual(legacy.read_q("draft, low confidence"), (1, ""))
        self.assertEqual(legacy.read_q("draft, low confidence, one sentence"), (1, "one sentence"))
        self.assertEqual(legacy.read_q("draft, seen once"), (2, "seen once"))
        self.assertEqual(legacy.read_q("?"), (2, "?"))
        self.assertEqual(legacy.write_q(1, "one sentence"), "draft, low confidence, one sentence")

    def test_a_status_without_format_2_form_is_an_error(self) -> None:
        with self.assertRaises(CiteError):
            legacy.write_q(4, "")

    def test_placeholder_becomes_word_positions_and_back(self) -> None:
        for zolai, keyword in (
            ("Ka ~ a na hi", "khut"), ("~-in a pai hi", "amau te"), ("pau ~-~ hi", "te"), ("a ~, a ~ leh", "gam"),
        ):
            text, starts, length = legacy.fill(zolai, keyword)
            self.assertNotIn("~", text)
            self.assertEqual(legacy.blank(text, keyword, starts, length), zolai)
        self.assertEqual(legacy.fill("~-in a pai hi", "amau te"), ("amau te-in a pai hi", [1], 2))

    def test_a_position_that_does_not_hold_the_keyword_is_an_error(self) -> None:
        with self.assertRaises(CiteError):
            legacy.blank("Ka khut a na hi", "khut", [1], 1)


class TableFileTest(unittest.TestCase):
    def test_rows_are_sorted_sharded_and_read_back(self) -> None:
        rows = [("w5000", "b", "1"), ("w2", "a", "1"), ("w10", "c", "2")]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            written = tables.write(root, "word", rows)
            self.assertEqual([path.name for path in written], ["0000.tsv", "0001.tsv"])
            self.assertEqual((root / "word" / "0000.tsv").read_text(), "id\tspelling\tstatus\nw2\ta\t1\nw10\tc\t2\n")
            self.assertEqual(tables.read(root, "word"), [("w2", "a", "1"), ("w10", "c", "2"), ("w5000", "b", "1")])

    def test_defects_stop_writing(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for rows in ([("w1", "a\tb", "1")], [("w1", "a")], [("w1", "a", "1"), ("w1", "a", "1")], [("x1", "a", "1")]):
                with self.assertRaises(CiteError):
                    tables.write(root, "word", rows)

    def test_defects_stop_reading(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(CiteError):
                tables.read(root, "word")
            tables.write(root, "word", [("w1", "a", "1")])
            path = root / "word" / "0000.tsv"
            for text in ("id\tspelling\nw1\ta\n", "id\tspelling\tstatus\nw1\ta\n", "id\tspelling\tstatus\nw5000\ta\t1\n"):
                path.write_text(text)
                with self.assertRaises(CiteError):
                    tables.read(root, "word")

    def test_shard_of_an_id(self) -> None:
        self.assertEqual(schema.shard_of("w4999"), 0)
        self.assertEqual(schema.shard_of("s4000"), 2)
        with self.assertRaises(CiteError):
            schema.shard_of("s01")


class ConvertTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = data_of()
        self.tables = convert.convert(CONFIG, self.data, NOTES)

    def test_words_senses_and_relations(self) -> None:
        words = {spelling: word for word, spelling, _ in self.tables["word"]}
        self.assertEqual(set(words), {"ale", "amaute", "amau", "khut", "khe", "te", "Abde", "anath"})
        senses = {(row[1], row[2]): row for row in self.tables["sense"]}
        khut = senses[words["khut"], "1"]
        self.assertEqual(khut[3:], ("n", "", "body", "core", "1", "", "pk:38", "one sentence"))
        self.assertEqual(senses[words["khut"], "2"][7], "2")
        self.assertEqual(senses[words["khut"], "2"][10], "?")
        self.assertEqual(senses[words["amau"], "1"][7], "2")
        self.assertIn((khut[0], "hand", "", "used of people"), self.tables["gloss/eng"])
        self.assertIn((khut[0], "a", words["khe"], "1"), self.tables["relation"])
        self.assertIn((senses[words["amaute"], "1"][0], "j", words["te"], "2"), self.tables["relation"])
        self.assertIn((words["Abde"], "see", words["khe"], "1"), self.tables["relation"])
        self.assertEqual(senses[words["anath"], ""][3], "todo")

    def test_one_sentence_is_stored_once(self) -> None:
        texts = [row[2] for row in self.tables["example"]]
        self.assertEqual(texts.count("ka khut leh ka khe"), 1)
        example = next(row[0] for row in self.tables["example"] if row[2] == "ka khut leh ka khe")
        positions = sorted(row[2] for row in self.tables["usage"] if row[0] == example)
        self.assertEqual(positions, ["2", "5"])
        self.assertIn("2/2", [row[2] for row in self.tables["usage"]])

    def test_sequence_holds_the_last_ids(self) -> None:
        self.assertEqual(dict(self.tables["sequence"]), {"word": "8", "sense": "7", "example": "4"})

    def test_the_tables_return_the_rows(self) -> None:
        report = roundtrip.compare(CONFIG, self.data, self.tables, NOTES)
        self.assertTrue(report.equal, roundtrip.text(report))
        self.assertEqual(report.expected["rows without q, now draft"], 3)
        self.assertEqual(report.expected["q that did not start with draft, now a remark of a draft"], 1)

    def test_a_lost_row_is_reported(self) -> None:
        self.tables["usage"].pop()
        report = roundtrip.compare(CONFIG, self.data, self.tables, NOTES)
        self.assertFalse(report.equal)
        self.assertEqual(len(report.parts[1].missing), 1)

    def test_defects_of_the_files_stop_the_conversion(self) -> None:
        for lexicon, examples in (
            ("khut = (i:1) (t:n) (w:hand) (s:khe)", "khut.1 = ~ | hand"),
            ("khut = (t:n) (w:hand)", "khut.1 = ~ | hand"),
            ("khut = (i:1) (t:n) (w:hand)", "khut.2 = ~ | hand"),
            ("khut = (i:1) (t:n) (w:hand)\nkhe = (t:see) <khut> extra", "khut.1 = ~ | hand"),
        ):
            with self.assertRaises(CiteError):
                convert.convert(CONFIG, data_of(lexicon, examples, "arm = khut.1"), NOTES)

    def test_a_table_that_names_a_missing_row_stops_rendering(self) -> None:
        self.tables["word"] = [row for row in self.tables["word"] if row[1] != "khe"]
        with self.assertRaises(CiteError):
            render.lexicon_lines(CONFIG, self.tables)


class RepositoryTest(unittest.TestCase):
    def test_the_data_survives_the_conversion(self) -> None:
        data = store.load(CONFIG)
        converted = convert.convert(CONFIG, data)
        with tempfile.TemporaryDirectory() as folder:
            tables.write_all(Path(folder), converted)
            stored = tables.read_all(Path(folder))
        report = roundtrip.compare(CONFIG, data, stored)
        self.assertTrue(report.equal, roundtrip.text(report))


if __name__ == "__main__":
    unittest.main()
