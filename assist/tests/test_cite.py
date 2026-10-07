"""Tests of the cite tooling.

The fixture holds rows of the repository data. Rows added inside a test are
artificial and state nothing about the language.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import List

from assist.cite import check, cli, config as configuration, credits, importer, lexicon, markup, pull, query, render, tables
from assist.cite.config import CiteError

ROWS = """
amau = (t:pron) (w:they/them) (d:Third person plural pronoun.)
amaute = (t:pron) (f:everyday) (w:they) (d:Third person plural pronoun, <amau> with the plural <te>.) (b:amau)
te = (t:part) (w:plural marker)
amaute.1 = ~ in mawtaw khat nei uh hi | they have a car (r:pk:67)
khut = (t:n) (w:hand) (d:the hand of a person)
khut.1 = Na ~ sil den in | always wash your hands (r:zd:23727)
khut.1 = ka ~ tawh kong gelh hi | I write to you with my own hand (r:46.16.21)
Be-ersheba = (t:name) (c:land) (w:Beersheba) (r:1.26.33)
ersheba = (t:see) <Be-ersheba>
""".strip().split("\n")


class Fixture(unittest.TestCase):
    """A cite directory of its own, filled by importing ``ROWS``."""

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        (root / "cite").mkdir()
        (root / "json").mkdir()
        shutil.copy(configuration.CONFIG_PATH, root / "cite" / "configuration.json")
        self.config = configuration.load(root / "cite" / "configuration.json")
        bible = self.config.raw["bible"]
        for identify in bible["source"] + bible["reference"]:
            text = json.dumps({"info": {"name": identify}, "book": {}})
            self.config.bible_path(identify).write_text(text, encoding="utf-8")
        for name, table in self.config.tables.items():
            if table.sharded and not table.per_language:
                (self.config.directory / table.path).mkdir()
        tables.write_all(self.config, {"note/open": [], "sequence": [("word", "0"), ("sense", "0"), ("example", "0")]})
        tables.write_text(credits.path(self.config), credits.build(self.config))
        self.apply(ROWS)

    def plan(self, lines: List[str]):
        model = check.load(self.config)
        return model, importer.plan(self.config, model, lines)

    def apply(self, lines: List[str]) -> importer.Plan:
        model, result = self.plan(lines)
        self.assertEqual(result.errors, [])
        self.assertEqual([f.describe(self.config) for f in check.run(self.config, model.tables())], [])
        tables.write_all(self.config, model.tables())
        return result

    def errors(self, lines: List[str]) -> List[str]:
        return self.plan(lines)[1].errors

    def verbs(self, lines: List[str]) -> List[str]:
        return [action.verb for action in self.apply(lines).actions]

    def model(self) -> lexicon.Lexicon:
        return check.load(self.config)


class MarkupTest(unittest.TestCase):
    def test_parse_sense_row(self) -> None:
        row = markup.parse("khut = (t:n) (w:hand/ arm)  the  text", 3)
        self.assertEqual((row.keyword, row.text, row.remove, row.is_example), ("khut", "the text", False, False))
        self.assertEqual(row.values(), {"t": "n", "w": "hand/ arm"})
        self.assertEqual(markup.split_list(row.values()["w"]), ["hand", "arm"])

    def test_parse_remove_and_example(self) -> None:
        row = markup.parse("- khut.1 = ka ~ | my hand (e:e7)")
        self.assertTrue(row.remove and row.is_example)
        self.assertEqual(markup.split_example(row.text), ("ka ~", "my hand", 1))
        self.assertFalse(markup.parse("khut").described)

    def test_fill_and_blank(self) -> None:
        text, starts, length = markup.fill("ka ~ tawh kong gelh hi", "khut")
        self.assertEqual((text, starts, length), ("ka khut tawh kong gelh hi", [2], 1))
        self.assertEqual(markup.blank(text, "khut", starts, length), "ka ~ tawh kong gelh hi")
        text, starts, length = markup.fill("pau ~-~ hi", "pau")
        self.assertEqual((starts, markup.blank(text, "pau", starts, length)), ([2, 2], "pau ~-~ hi"))
        with self.assertRaises(CiteError):
            markup.blank("ka khut", "khut", [1], 1)

    def test_segments(self) -> None:
        kinds = [(s.kind, s.text) for s in markup.segments("see <a/b.1> and {c d}")]
        self.assertEqual(
            kinds, [("text", "see "), ("link", "a"), ("text", "/"), ("link", "b.1"), ("text", " and "), ("mention", "c d")]
        )


class TableTest(Fixture):
    def test_shard_and_round_trip(self) -> None:
        rows = [("w5000", "b", "1"), ("w2", "a", "1"), ("w10", "c", "1")]
        files = tables.render(self.config, "word", rows)
        self.assertEqual([path.name for path in files], ["0000.tsv", "0001.tsv"])
        self.assertEqual(files[self.config.directory / "word" / "0000.tsv"], "id\tspelling\tstatus\nw2\ta\t1\nw10\tc\t1\n")

    def test_write_only_what_differs(self) -> None:
        model = self.model()
        self.assertEqual(tables.changes(self.config, model.tables()), ({}, []))
        model.words[model.spelling["khut"]].status = "3"
        write, remove = tables.changes(self.config, model.tables())
        self.assertEqual(([path.name for path in write], remove), (["0000.tsv"], []))

    def test_rejects_bad_values(self) -> None:
        with self.assertRaises(CiteError):
            tables.render(self.config, "word", [("w1", "a\tb", "1")])
        with self.assertRaises(CiteError):
            tables.render(self.config, "word", [("w1", "a", "1"), ("w1", "a", "1")])
        with self.assertRaises(CiteError):
            tables.render(self.config, "word", [("w1", "a")])

    def test_read_defects(self) -> None:
        path = self.config.directory / "word" / "0000.tsv"
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        path.write_text("\n".join([lines[0], lines[2], lines[1]] + lines[3:]), encoding="utf-8")
        problems: List[str] = []
        tables.read_all(self.config, problems)
        self.assertEqual(len(problems), 1)
        self.assertEqual([f.rule for f in check.structure(self.config, tables.read_all(self.config), problems)], ["E01"])
        path.write_text(text.replace("id\tspelling", "id\tword"), encoding="utf-8")
        with self.assertRaises(CiteError):
            tables.read_all(self.config)
        path.write_text(text, encoding="utf-8")
        path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        with self.assertRaises(CiteError):
            tables.read_all(self.config)
        path.write_text(text, encoding="utf-8")
        (self.config.directory / "word" / "0001.tsv").write_text("id\tspelling\tstatus\nw1\tx\t1\n", encoding="utf-8")
        with self.assertRaises(CiteError):
            tables.read_all(self.config)

    def test_unknown_language_folder(self) -> None:
        (self.config.directory / "gloss" / "xxx").mkdir()
        with self.assertRaises(CiteError):
            tables.read_all(self.config)


class ImportTest(Fixture):
    def test_fixture(self) -> None:
        model = self.model()
        self.assertEqual(model.last, {"word": 6, "sense": 5, "example": 3})
        self.assertEqual(model.key(model.sense_by_key("amaute.1")), "amaute.1")
        self.assertEqual(model.relation_items(model.sense_by_key("amaute.1"), "b"), ["amau"])
        self.assertEqual(model.relation_items(model.spelling["ersheba"], "see"), ["Be-ersheba"])
        sets = {model.key(s.id): s.set for s in model.senses.values()}
        self.assertEqual((sets["khut.1"], sets["Be-ersheba.1"]), ("core", "bible"))
        self.assertTrue(all(sense.status == "2" for sense in model.senses.values()))

    def test_new_sense_gets_the_next_number(self) -> None:
        result = self.apply(["khut = (t:v) (w:handle) (q:low, one sentence only)"])
        self.assertEqual([(a.verb, a.subject) for a in result.actions], [("inserted", "s6 khut.2")])
        sense = self.model().senses["s6"]
        self.assertEqual((sense.number, sense.status, sense.note), ("2", "1", "one sentence only"))

    def test_duplicate_is_blocked_and_can_be_forced(self) -> None:
        errors = self.errors(["khut = (t:n) (w:palm/Hand)"])
        self.assertEqual(len(errors), 1)
        self.assertIn("write (i:1) to replace it or (i:+)", errors[0])
        self.assertEqual(self.verbs(["khut = (i:+) (t:n) (w:palm/hand)"]), ["inserted"])

    def test_replace_is_whole(self) -> None:
        self.assertEqual(self.verbs(["amaute = (i:1) (t:pron) (w:they/those people) (q:confirmed)"]), ["replaced"])
        model = self.model()
        sense_id = model.sense_by_key("amaute.1")
        self.assertEqual(render.sense_line(model, sense_id), "amaute = (i:1) (t:pron) (w:they/those people) (q:confirmed)")
        self.assertEqual(model.relations.get(sense_id), None)
        self.assertEqual(len(model.shown_by[sense_id]), 1)

    def test_replace_by_id_and_unchanged(self) -> None:
        line = render.sense_line(self.model(), "s2")
        self.assertEqual(self.verbs([line]), ["unchanged"])
        self.assertEqual(self.verbs([line.replace("(i:1)", "(i:s2)")]), ["unchanged"])
        self.assertIn("already given on line 1", self.errors([line, line.replace("(i:1)", "(i:s2)")])[0])
        self.assertIn("not a sense of 'khut'", self.errors(["khut = (i:s2) (t:n) (w:x)"])[0])
        self.assertIn("has no sense 7", self.errors(["khut = (i:7) (t:n) (w:x)"])[0])

    def test_row_errors(self) -> None:
        for line, part in (
            ("khut = (t:zz) (w:x)", "not a type"),
            ("khut = (w:x)", "(t:) is missing"),
            ("khut = (t:n) (x:1) (w:y)", "not an attribute"),
            ("khut = (t:n) (w:y) (w:z)", "written twice"),
            ("khut = (t:n) (w:y) (lost", "parenthesis"),
            ("khut = (t:n) (w:y) (q:sure)", "not a status"),
            ("khut = (t:n) (w:y) (q:draft, low confidence)", "(q:low)"),
            ("khut = (t:n) (w:y) (s:nowhere)", "names no word"),
            ("khu.t = (t:n) (w:y)", "not written as a keyword"),
            ("kh_ut = (t:n) (w:y)", "not written as a keyword"),
            ("khut = (t:n) (w:y/)", "empty item"),
            ("khut.1 = ka khut | my hand", "written ~"),
            ("khut.1 = ka ~", "translation"),
            ("khut.9 = ka ~ | my hand", "not a sense"),
            ("- khut = (t:n)", "removed by its number"),
            ("- khut", "still has the senses khut.1"),
            ("khut = (i:) (t:n) (w:y)", "(i:) is empty"),
            ("khut.1 = ka ~ | my hand (e:)", "(e:) is empty"),
            ("khut.1 = ka ~ | my hand (e:s5)", "not an example"),
            ("- khut.1 = (e:e1)", "not an example of khut.1"),
            ("# pulled khut version 12", "stamp is damaged"),
        ):
            with self.subTest(line=line):
                errors = self.errors([line])
                self.assertEqual(len(errors), 1)
                self.assertIn(part, errors[0])

    def test_nothing_is_written_when_the_check_fails(self) -> None:
        model, result = self.plan(["khut = (i:1) (t:n) (w:hand) (d:see <nowhere>)"])
        self.assertEqual(result.errors, [])
        self.assertEqual([f.rule for f in check.run(self.config, model.tables())], ["E10"])

    def test_relations_variants_and_sense_keys(self) -> None:
        self.apply(["khutme = (t:n) (w:thumb) (s:khut.1/amau) (j:khut/te) (v:khut-me)"])
        model = self.model()
        sense_id = model.sense_by_key("khutme.1")
        targets = {(r.kind, r.to, r.order) for r in model.relations[sense_id]}
        self.assertEqual(targets, {
            ("s", model.sense_by_key("khut.1"), 1), ("s", model.spelling["amau"], 2),
            ("j", model.spelling["khut"], 1), ("j", model.spelling["te"], 2), ("v", model.spelling["khut-me"], 1),
        })
        self.assertEqual(model.words[model.spelling["khut-me"]].status, "2")
        self.assertIn("(s:khut.1/amau) (j:khut/te) (v:khut-me)", render.sense_line(model, sense_id))

    def test_redirect(self) -> None:
        self.assertEqual(self.verbs(["ersheba = (t:see) <Be-ersheba>"]), ["unchanged"])
        self.assertEqual(self.verbs(["ersheba = (t:see) <khut>"]), ["replaced"])
        self.assertEqual(self.verbs(["- ersheba = (t:see) <khut>"]), ["removed"])
        self.assertIn("names no word", self.errors(["ersheba = (t:see) <nowhere>"])[0])

    def test_bare_word_and_retire(self) -> None:
        result = self.apply(["sil"])
        self.assertEqual((result.actions[0].verb, result.words), ("inserted", ["w7 sil"]))
        self.assertEqual(self.verbs(["sil", "- sil"]), ["unchanged", "removed"])
        self.assertEqual(self.verbs(["- khut = (i:1)"]), ["removed"])
        model = self.model()
        self.assertFalse(model.active(model.sense_by_key("khut.1")))
        self.assertEqual(self.verbs(["khut = (t:n) (w:hand)", "sil = (t:v) (w:wash)"]), ["inserted", "inserted"])
        model = self.model()
        self.assertEqual((model.senses["s6"].number, model.words[model.spelling["sil"]].status), ("2", "1"))

    def test_example_is_stored_once(self) -> None:
        self.apply(["amaute = (i:+) (t:pron) (w:them)"])
        lines = ["amaute.2 = ~ in mawtaw khat nei uh hi | they have a car (r:pk:67)"]
        self.assertEqual(self.apply(lines).actions[0].subject, "e1 amaute.2")
        model = self.model()
        self.assertEqual(sorted(model.usages["e1"]), ["s2", "s6"])
        self.assertEqual(self.verbs(lines), ["unchanged"])
        self.assertEqual(self.verbs(["- " + lines[0]]), ["removed"])
        self.assertEqual(sorted(self.model().usages["e1"]), ["s2"])

    def test_example_with_another_translation(self) -> None:
        line = "khut.1 = Na ~ sil den in | wash your hands always (r:zd:23727)"
        self.assertIn("write (e:e2) to replace it or (e:+) to keep both", self.errors([line])[0])
        self.assertEqual(self.verbs([line + " (e:+)"]), ["inserted"])
        self.assertEqual(self.model().last["example"], 4)
        self.assertEqual(self.verbs([line.replace("always", "every day") + " (e:e2)"]), ["replaced"])
        self.assertEqual(self.model().translations["eng"]["e2"], "wash your hands every day")

    def test_removing_the_last_usage_removes_the_example(self) -> None:
        self.assertEqual(self.verbs(["- khut.1 = Na ~ sil den in | always wash your hands (e:e2)"]), ["removed"])
        model = self.model()
        self.assertNotIn("e2", model.examples)
        self.assertNotIn("e2", model.translations["eng"])
        self.assertEqual(model.last["example"], 3)
        self.assertEqual(self.apply(["khut.1 = Na ~ sil den in | always wash your hands"]).actions[0].subject, "e4 khut.1")

    def test_example_of_a_sense_typed_in_the_same_file(self) -> None:
        result = self.apply(["khut = (t:v) (w:handle)", "khut.2 = ka ~ tawh kong gelh hi | I write to you with my own hand (r:46.16.21)"])
        self.assertEqual([a.subject for a in result.actions], ["s6 khut.2", "e3 khut.2"])

    def test_rows_of_a_shared_example_agree(self) -> None:
        self.apply(["khut.1 = amaute in ~ nei uh hi | they have hands", "amaute.1 = ~ in khut nei uh hi | they have hands"])
        first = "khut.1 = amaute in ~ nei uh hi | they have hands (e:e4)"
        second = "amaute.1 = ~ in khut nei uh hi | they do have hands (e:e4)"
        for lines in ([first, second], [second, first]):
            model, result = self.plan(lines)
            self.assertEqual(result.errors, [])
            self.assertEqual(model.translations["eng"]["e4"], "they do have hands")
            self.assertEqual(sorted(action.verb for action in result.actions), ["replaced", "unchanged"])
        errors = self.errors([first.replace("have hands", "own hands"), second])
        self.assertIn("another text, source or translation on line 1", errors[0])

    def test_removal_by_example_id_alone(self) -> None:
        self.assertEqual(self.verbs(["- khut.1 = (e:e2)"]), ["removed"])
        self.assertNotIn("e2", self.model().examples)

    def test_sense_without_number_is_named_by_id(self) -> None:
        self.apply(["zz = (t:todo) (r:1.1.1) (q:draft, not clear from the verse)"])
        model = self.model()
        self.assertEqual(render.sense_line(model, "s6"), "zz = (i:s6) (t:todo) (r:1.1.1) (q:draft, not clear from the verse)")
        self.assertEqual(self.verbs(pull.text(model, ["zz"]).split("\n")), ["unchanged"])

    def test_retired_rows_are_not_named(self) -> None:
        model, result = self.plan(["- amau = (i:1)", "- amau"])
        self.assertEqual(result.errors, [])
        found = check.run(self.config, model.tables())
        self.assertEqual(sorted(f.rule for f in found), ["E10", "E12"])
        self.apply(["- khut = (i:1)", "- khut"])
        self.assertEqual(self.model().words["w4"].status, "0")
        self.assertEqual(self.verbs(["khut = (i:1) (t:n) (w:hand)"]), ["replaced"])
        self.assertEqual(self.model().words["w4"].status, "1")
        self.apply(["- khut = (i:1)", "- khut"])
        self.assertEqual(self.verbs(["khut"]), ["replaced"])
        self.assertEqual(self.model().words["w4"].status, "1")

    def test_done_rows_are_not_imported_again(self) -> None:
        lines = ["# note", "khut = (t:v) (w:handle)", "", "sil"]
        result = self.apply(lines)
        marked = importer.mark_done(lines, result)
        self.assertEqual(marked, ["# note", "# done s6 khut.2 inserted: khut = (t:v) (w:handle)", "", "# done w7 sil inserted: sil"])
        self.assertEqual(self.errors(marked), ["the file holds no row to import"])


class PullTest(Fixture):
    def test_pulled_file_imports_unchanged(self) -> None:
        text = pull.text(self.model(), ["amaute", "khut", "ersheba"])
        lines = text.split("\n")
        self.assertIn("# amaute.1 is s2, set core", lines)
        self.assertIn("ersheba = (t:see) <Be-ersheba>", lines)
        result = self.apply(lines)
        self.assertEqual({action.verb for action in result.actions}, {"unchanged"})
        self.assertEqual(tables.changes(self.config, self.model().tables()), ({}, []))
        marked = importer.mark_done(lines, result)
        self.assertFalse(any(markup.is_row(line) or importer.STAMP.match(line) for line in marked))

    def test_stale_file_is_refused(self) -> None:
        lines = pull.text(self.model(), ["khut"]).split("\n")
        self.apply(["khut = (i:1) (t:n) (w:hand/arm)"])
        errors = self.errors(lines)
        self.assertEqual(len(errors), 1)
        self.assertIn("pull the word again", errors[0])
        self.assertIn("pull the word again", self.errors([lines[0] + " "] + lines[1:])[0])

    def test_context_and_related(self) -> None:
        text = pull.text(self.model(), ["amau"], related=True)
        self.assertIn("# amau is named by: (b) of amaute.1", text)
        self.assertIn("# <amau> is linked in the prose of: amaute.1", text)
        self.assertIn("# pulled amaute version", text)
        with self.assertRaises(CiteError):
            pull.text(self.model(), ["nowhere"])


class CheckTest(Fixture):
    def rules(self, change) -> List[str]:
        data = self.model().tables()
        change(data)
        return sorted({finding.rule for finding in check.run(self.config, data)})

    def test_sound(self) -> None:
        self.assertEqual(self.rules(lambda data: None), [])

    def test_structure(self) -> None:
        self.assertEqual(self.rules(lambda data: data["usage"].append(("e9", "s1", "1", "1"))), ["E04"])
        self.assertEqual(self.rules(lambda data: data["word"].append(("w9", "x", "1"))), ["E03"])
        self.assertEqual(self.rules(lambda data: data["word"].append(("x9", "x", "1"))), ["E02"])
        self.assertEqual(self.rules(lambda data: data["word"].append(("w6", "x", "9"))), ["E02", "E05"])
        self.assertEqual(self.rules(lambda data: data["relation"].append(("s1", "zz", "w1", "1"))), ["E05"])

    def test_content(self) -> None:
        def usage(data) -> None:
            data["usage"] = [(e, s, "1", n) if e == "e3" else (e, s, a, n) for e, s, a, n in data["usage"]]

        self.assertEqual(self.rules(usage), ["E15"])
        self.assertEqual(self.rules(lambda data: data["word"].append(("w6", "khut", "1"))), ["E02"])
        self.assertEqual(self.rules(lambda data: data["gloss/eng"].append(("s3", "plural (marker)", "", ""))), ["E02"])

        def paren(data) -> None:
            data["gloss/eng"] = [(s, t.replace("hand", "hand (limb)"), d, x) for s, t, d, x in data["gloss/eng"]]

        self.assertEqual(self.rules(paren), ["E09"])

        def lower(data) -> None:
            data["word"] = [(i, s.lower(), t) for i, s, t in data["word"]]

        self.assertEqual(self.rules(lower), ["E18"])

    def test_credits(self) -> None:
        credits.path(self.config).write_text("old", encoding="utf-8")
        self.assertEqual(self.rules(lambda data: None), ["E21"])


class QueryTest(Fixture):
    def test_lookup(self) -> None:
        model = self.model()
        self.assertEqual(query.words_for(model, "beersheba"), [model.spelling["Be-ersheba"]])
        self.assertEqual(query.words_for(model, "KHUT"), [model.spelling["khut"]])
        self.assertEqual(query.words_for(model, "nowhere"), [])
        self.assertEqual(query.senses_for_term(model, "Hand", "eng"), [model.sense_by_key("khut.1")])
        self.assertEqual(query.senses_for_term(model, "marker", "eng"), [model.sense_by_key("te.1")])
        self.assertIn("see          Be-ersheba", query.describe_word(model, model.spelling["ersheba"]))
        self.assertIn("ka ~ tawh kong gelh hi | I write to you with my own hand  [46.16.21]", query.describe_word(model, model.spelling["khut"]))

    def test_record_and_find(self) -> None:
        model = self.model()
        data = query.record(model, model.sense_by_key("amaute.1"))
        self.assertEqual(data["relation"], {"b": ["amau"]})
        self.assertEqual(data["example"][0]["start"], [1])
        found = query.find(model, "WASH")
        self.assertEqual((found["word"], len(found["example"])), ([], 1))


class CommandTest(unittest.TestCase):
    def test_inbox_path(self) -> None:
        config = configuration.load()
        self.assertEqual(cli._markup_file(config, "new"), config.directory / "inbox" / "new.cite")
        self.assertEqual(cli._markup_file(config, "new.txt"), config.directory / "inbox" / "new.txt")
        self.assertEqual(cli._markup_file(config, "./new.cite"), Path("new.cite"))
        self.assertEqual(cli._markup_file(config, "notes/new.cite"), Path("notes/new.cite"))


class RepositoryTest(unittest.TestCase):
    """The data of the repository itself."""

    def test_format_document_lists_every_rule(self) -> None:
        text = (self.config.directory / "Format.md").read_text(encoding="utf-8")
        for rule in self.config.rules.values():
            self.assertIn(f"| `{rule['id']}` | {rule['name']} | {rule['description']} |", text)

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = configuration.load()
        cls.problems: List[str] = []
        cls.data = tables.read_all(cls.config, cls.problems)

    def test_check_passes(self) -> None:
        found = check.run(self.config, self.data, self.problems)
        self.assertEqual([finding.describe(self.config) for finding in found[:20]], [])

    def test_model_stores_what_it_read(self) -> None:
        model = lexicon.build(self.config, self.data)
        self.assertEqual(tables.changes(self.config, model.tables()), ({}, []))

    def test_pulled_words_import_unchanged(self) -> None:
        model = lexicon.build(self.config, self.data)
        lines = pull.text(model, ["khut", "amaute", "ersheba", "adah"], related=True).split("\n")
        result = importer.plan(self.config, model, lines)
        self.assertEqual(result.errors, [])
        self.assertEqual({action.verb for action in result.actions}, {"unchanged"})
        self.assertEqual(tables.changes(self.config, model.tables()), ({}, []))


if __name__ == "__main__":
    unittest.main()
