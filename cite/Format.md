# Cite Format

Version 3. The tables of the Zolai–English dictionary data in this directory, the ids that link them, and the markup in which entries are typed and shown.

Every closed list named in this document is stored in `configuration.json`: tables and columns, status codes, relation kinds, sets, note kinds, attributes, types, categories, fields, sources and rules. When the two differ, `configuration.json` is authoritative.

## Model

- A **word** is one written form. Case is significant: `Pasian` and `pasian` are different words.
- A **sense** is one meaning of a word. It carries what does not depend on a language: type, category, field, set, status, origin and source.
- A **gloss** gives the terms and the definition of a sense in one language.
- A **relation** links a sense to another word or sense: synonym, antonym, base, join, variant. A redirect links a word to a word.
- An **example** is a sentence or fragment in Zolai, stored once. A **usage** says which sense the example shows and where the keyword stands in it; one example may show several senses. A **translation** gives the example in one language.
- A **link** sends a word of another language that is not a term of any sense to the closest senses.
- A **note** is an open point for an editor.

## Files

```text
cite/
  configuration.json
  word/0000.tsv              one file per block of 5000 word ids
  sense/0000.tsv             one file per block of 2000 sense ids
  gloss/eng/0000.tsv         by the sense id; one folder per language
  relation/0000.tsv          by the id the relation starts from
  example/0000.tsv           one file per block of 5000 example ids
  usage/0000.tsv             by the example id
  translation/eng/0000.tsv   by the example id; one folder per language
  link/eng.tsv               one file per language
  note/open.tsv
  sequence.tsv
  CREDITS.md                 generated
  inbox/                     markup files, not part of the repository
```

- A table file is UTF-8 text without a byte order mark. Lines end with a single line feed, and the file ends with exactly one.
- The first line names the columns, separated by tabs. Every further line is one row with the same number of values.
- A value never holds a tab or a line break. An absent value is empty.
- A list inside one value is separated by `/`.
- The rows of a file are sorted by their columns from left to right, an id by its number, and no row occurs twice.
- A sharded table keeps a row in the file named by the block of the id in its first column: the number divided by the block size, written with four digits. `s4100` is in `sense/0002.tsv`.
- Nothing generated is stored except `CREDITS.md`. Indexes are built in memory by the command that needs them.

## Ids

An id is a letter and a number: `w` for a word, `s` for a sense, `e` for an example. A number is given once, in order, and never reused; `sequence.tsv` holds the highest number given for each kind. A removed row leaves its number unused.

A sense also has a number within its word. Word and number form the **sense key**, `khut.1`, which is how a sense is named in markup and in prose. The number is never reused within a word.

## Tables

### word

| Column | Content |
| --- | --- |
| `id` | Word id. |
| `spelling` | The word as written. Unique. |
| `status` | `0` retired, `1` standard, `2` variant, `3` nonstandard. |

A word is written with the letters A to Z and a to z, the digits, and between its parts one space, one hyphen or one apostrophe; a final apostrophe is allowed. A word written with a hyphen in the Bible text keeps the hyphen. A word without a sense is a form that only points at other words: a variant, or a redirect.

### sense

| Column | Content |
| --- | --- |
| `id` | Sense id. |
| `word` | Word id. |
| `number` | Number of the sense within its word. May be empty for a sense of type `todo`. |
| `type` | Code of the type list: the word class. |
| `category` | Codes of the category list: what kind of thing the word names. |
| `field` | Codes of the field list: the subject area. |
| `set` | `core`, `bible` or `name`. |
| `status` | `0` retired, `1` low, `2` draft, `3` reviewed, `4` confirmed, `5` disputed. |
| `origin` | Language the word comes from, optionally followed by a comma and the source word. |
| `source` | Where the sense is attested: Bible verses and listed sources. |
| `note` | Remark that belongs to the status. |

| Status | Meaning |
| --- | --- |
| retired | No longer part of the lexicon. The row stays so that its id and number are not reused. |
| low | Drafted on thin evidence; likely to need correction. |
| draft | Drafted and not yet reviewed. |
| reviewed | Read by a reviewer who found no fault, or confirmed by a second and independent source; not yet confirmed by the maintainer. |
| confirmed | Confirmed by a speaker of the language. |
| disputed | Reviewers disagree, or a fault was reported and is not yet resolved. |

### gloss/{language}

| Column | Content |
| --- | --- |
| `sense` | Sense id. One row per sense. |
| `terms` | Words of the language with the meaning of the sense, the best first. Interchangeable; a different meaning is a different sense. |
| `definition` | Explanation of the meaning, used when no term fits or in addition to one. |
| `text` | Remark on usage or grammar that is not the meaning itself. |

A sense of a type that carries a meaning has a term or a definition in at least one language, unless it joins exactly one target and so carries the meaning of that target.

### relation

| Column | Content |
| --- | --- |
| `from` | Sense id; for the kind `see`, a word id. |
| `kind` | `s` synonym, `a` antonym, `b` base, `j` join, `v` variant, `see` redirect. |
| `to` | Word id, or a sense id when one meaning of the target is meant. |
| `order` | Position among the targets of the same kind, from 1. |

- `b`: the keyword is a plural, suffixed or prefixed form of the target.
- `j` with several targets: separate words written as one, in their order, as `aom` joins `a` and `om`. With one target: the same word in another spelling.
- `v`: the target is another spelling of the keyword. It is a word with the status variant and has no sense of its own.
- `see`: the word occurs only as one part of the target, as `ersheba` in `Be-ersheba`.

### example, usage, translation/{language}

| Table | Column | Content |
| --- | --- | --- |
| example | `id` | Example id. |
| example | `source` | A Bible verse or a listed source. May be empty. |
| example | `text` | The text in Zolai, in full. |
| usage | `example` | Example id. |
| usage | `sense` | Sense id. One row per example and sense. |
| usage | `start` | Positions of the word of the text at which the keyword starts, counted from 1 and separated by `/`. A position is repeated when the keyword stands more than once inside that word. |
| usage | `length` | Number of words the keyword covers. |
| translation | `example` | Example id. One row per example. |
| translation | `text` | The translation. |

Two examples may share text and source when their translations differ. An example that no sense uses is removed.

### link/{language}, note/open, sequence

| Table | Column | Content |
| --- | --- | --- |
| link | `term` | A word of the language, in lowercase, that is not a term of any sense. |
| link | `senses` | Sense ids, the closest first. |
| link | `source` | How the link was found. |
| link | `status`, `note` | As for a sense. |
| note | `kind` | Code of the note list. |
| note | `subject` | The concept or word. |
| note | `source` | Where it was met. |
| note | `text` | What was found. |
| sequence | `table` | `word`, `sense` or `example`. |
| sequence | `last` | Highest number given out. |

## Sources

A source is written as a Bible verse, `book.chapter.verse` with book numbers 1 to 66 and a hyphen for a range of verses, or as a code of the source list, optionally followed by a colon and a locator inside that source: `1.2.4-6`, `zai:market`, `zd:20522`, `pk:165`.

## Zolai inside prose

Prose is the definition and text of a gloss and the note of a sense. Zolai that occurs in it is marked, so that a tool can tell the languages apart. The marks are stored as written; they are not replaced by ids.

- A word of the lexicon is a link, `<ahih>`. The key of one sense, `<khat.2>`, links to that sense.
- Several words are written `<a> <b>` or `<a/b>`; the two forms mean the same, two links.
- Any other Zolai is a mention in braces and is not a link: a phrase, `{a nu leh a pa}`; an ending or prefix, `{-pa}`; a form that is not a word of the lexicon; and the keyword of the sense itself.
- A name in its English spelling is English and carries no mark.
- Parentheses, `~` and `|` do not occur in any stored text: the markup reserves them.

## Markup

Entries are typed and shown as markup. A markup file is plain text with any name; the commands `import` and `pull` turn markup into table changes and tables into markup.

| Line | Form | Meaning |
| --- | --- | --- |
| blank | empty | No meaning. |
| comment | first character is `#` | Text for the editor. A line starting `# done` is a row already imported. |
| sense row | `keyword = (key:value) ... text` | One sense of the keyword. |
| example row | `keyword.number = zolai \| translation (r:source) (e:id)` | One example of that sense. The keyword is written `~` in the Zolai text. |
| word row | `keyword` | The word alone. |
| removal | any row after `- ` | Removes what the row names. |

- The first `=` on a line separates the keyword from the rest. A keyword never holds a dot, so a key with a dot and a number is a sense key and makes the row an example row.
- An attribute is written `(key:value)`. Parentheses are reserved for attributes; prose that would use them uses commas.
- A list value separates its items with `/`.
- The text of a sense row, outside every attribute, is the remark on usage: the `text` of the gloss.
- The markup carries the first gloss language, English. Glosses and translations of a further language are not typed in this markup.

### Attributes of a sense row

| Key | Name | List | Meaning | Example |
| --- | --- | --- | --- | --- |
| `i` | sense | no | Which sense the row is. Absent: a new sense. A number or a sense id: that sense is replaced by the row. `+`: a new sense although a similar one exists. | `(i:2)` |
| `t` | type | no | Word class. Required. | `(t:v)` |
| `c` | category | yes | What kind of thing the keyword names. | `(c:land)` |
| `f` | field | yes | Subject area. | `(f:health)` |
| `w` | term | yes | English words with the meaning of this sense. | `(w:begin/start)` |
| `d` | definition | no | English explanation of the meaning. | `(d:marker of place or time)` |
| `s` | synonym | yes | Keywords with the same meaning; a sense key when one meaning is meant. | `(s:leh)` |
| `a` | antonym | yes | Keywords with the opposite meaning; a sense key when one meaning is meant. | `(a:lian)` |
| `b` | base | no | The keyword this form is built from. | `(b:vantung)` |
| `j` | joins | yes | The keywords this written form joins or respells. | `(j:a/om)` |
| `v` | variant | yes | Other spellings of the keyword. A word with the status variant is made for each. | `(v:Shoute)` |
| `o` | origin | no | Language the keyword comes from, optionally a comma and the source word. | `(o:Hebrew, kerub)` |
| `r` | source | yes | Where the sense is attested. | `(r:1.1.1/zai:market)` |
| `q` | status | no | Name of the status, optionally a comma and a remark. Absent: draft. | `(q:low, inferred from one sentence)` |

A redirect is typed as `(t:see)` followed by exactly one link and is stored as a relation, not as a sense:

```text
ersheba = (t:see) <Be-ersheba>
```

### What a sense row does

- **No `i`**: a new sense. The word is added when it is not yet stored. The sense gets the next number of its word and the next sense id. Its set is `bible` when every source is a Bible verse and `core` otherwise; `set` moves it.
- **A duplicate is refused.** A row without `i` whose word already has an active sense of the same type that shares a term, or has the same definition when there is no term, is not imported. The message names that sense: `(i:1)` replaces it, `(i:+)` adds a further sense.
- **`(i:2)` or `(i:s19435)`**: the row replaces that sense as a whole. Type, category, field, origin, source, status, note, the English gloss and the relations `s`, `a`, `b`, `j` and `v` become what the row says; an attribute that is left out is removed. The id, the number, the set and the examples stay.
- **No `q` is a draft**, also on a replacing row. A pulled row carries its `q`, so a status other than draft survives an edit unless it is changed.
- A keyword or sense key named in `s`, `a`, `b` or `j` is a word or sense of the lexicon or of the same file.
- **`- khut = (i:2)`** retires the sense: status retired. The row, its number and its examples stay. A sense that an active sense still names in a relation or links in its prose is not retired until those are changed.
- A sense is given once in a file. A sense without a number, of type `todo`, is named by its id: `(i:s2764)`.
- **`- ersheba = (t:see) <Be-ersheba>`** removes the redirect.

### What an example row does

```text
khut.1 = ka ~ tawh kong gelh hi | I write to you with my own hand (r:46.16.21)
```

- The sense key names a sense of the lexicon or one added earlier in the same file; a new sense gets the next number of its word.
- The full text is stored with the keyword in place of every `~`, and the usage records the word positions.
- **No `e`**: when an example with the same text, source and translation exists, the row adds a usage to it and no second copy is stored. When one exists with another translation, the row is refused and the message names it: `(e:e88120)` replaces that example, `(e:+)` keeps both.
- **`(e:e88120)`**: the text, source and English translation of that example become what the row says, and the sense uses it. Every other sense that uses the example is checked against the new text. When several rows of a file name one example, as the rows of a pulled example that two senses share do, the rows that differ from what is stored agree with each other; a row left as pulled changes nothing.
- **`- khut.1 = (e:e88120)`** removes the usage; the text may follow as pulled and is not read. An example that no sense uses any more is removed with its translations. Without `e` the row is written in full and the example is found by its text.

### What a word row does

`sil` alone adds the word without a sense, so that other rows may name it; a retired word becomes standard again. `- sil` retires a word that has no active sense. A word that gets an active sense becomes standard.

## Import

`python3 -m assist cite import FILE` reads a markup file. A bare file name is looked up in the inbox folder named under `format.inbox` in `configuration.json`, with the extension `.cite` when none is given; a path with a folder is used as given.

- The import is a dry run unless `--apply` is given. It reports for every row what it does: `inserted`, `replaced`, `unchanged` or `removed`, with the id and the sense key.
- A file is imported as a whole or not at all. A row that cannot be imported is reported with its line number and what to change.
- The changed data is checked in full against the rules before anything is written. A change that breaks a rule is refused.
- With `--apply` only the table files that differ are written. Every imported row of the markup file becomes a comment, `# done s51193 khut.2 inserted: ...`, so a second run of the same file does nothing.
- Ids are given in order at import. Imports are done on top of the latest `master`, one branch at a time.

## Pull

`python3 -m assist cite pull WORD... --apply` writes the rows of the words into `inbox/WORD.cite`, ready to edit and import. Without `--apply` the file is printed.

```text
# pulled amaute version 7cf8bc45fd8d
# word w2459 'amaute', standard; senses 2, examples 18
# amaute is named by: (b) of Amaute.1, (s) of amau.1, (s) of maute.1
# <amaute> is linked in the prose of: maute.1, mi thumna.1, zomah.1
# amaute.1 is s2557, set core
amaute = (i:1) (t:pron) (f:everyday) (w:they) (d:Third person plural pronoun, <amau> with the plural <te>; as the subject it is usually followed by <in>.) (b:amau)
amaute.1 = ~ in mawtaw khat nei uh hi | they have a car (r:pk:67) (e:e4270)
```

- Every sense row carries its `i` and every example row its `e`, so an edited row replaces what is stored.
- The comments say what else names the word: relations that lead to it, prose that links it, linked words of another language. They are not imported.
- The first line is a version stamp of the rows as pulled. When the rows of the word change in the tables afterwards, the import refuses the file and asks for a new pull, so an old file never overwrites a newer state.
- `--related` adds the words one relation or one link away, each under its own stamp.
- A file in the inbox that still holds rows that are not imported is never overwritten.

## Rules

`python3 -m assist cite check` reports every broken rule with the table and the row. The ids and descriptions are listed under `rule` in `configuration.json`.

| Id | Name | Rule |
| --- | --- | --- |
| `E01` | file order | The rows of a table file are sorted by their columns and no row occurs twice. |
| `E02` | id | An id is the letter of its kind and a number; an id, and a key that is one per row, occurs once. |
| `E03` | sequence | The sequence table holds one row per kind of id, and no id is above the last number given. |
| `E04` | reference | An id written in a column names an existing row of the table it points at. |
| `E05` | code | A code is listed in the configuration: status, type, category, field, set, relation kind, note kind. A code is named once. |
| `E06` | spelling | A word is written as the keyword pattern allows, and a spelling occurs once. |
| `E07` | sense number | A sense of a type that carries a meaning has a positive whole number that no other sense of the word has. |
| `E08` | meaning | A sense of a type that carries a meaning has a term or a definition, or joins exactly one target. |
| `E09` | text | A value holds nothing that the markup cannot hold: parentheses, the placeholder, the translation separator, double spaces; terms hold no empty or repeated term and no link or mention. |
| `E10` | link mark | A link in prose is written <keyword> or <keyword.number> and names an existing word or sense; prose of an active sense names nothing retired. |
| `E11` | mention | A mention in prose is written {text}; braces are balanced and not empty, hold no link, and do not name a standard word of the lexicon other than the keyword. |
| `E12` | relation | A redirect leads from a word to one other word; every other kind leads from a sense. The targets of one kind are ordered from 1. A variant is a word with the status variant and no sense. A join does not name its own keyword. An active sense or word does not lead to a retired one, and a retired word is not redirected. |
| `E13` | source | A source is a Bible verse written book.chapter.verse or the code of a listed source with an optional locator. |
| `E14` | example | An example has a text that the markup can hold, is used by at least one sense, and does not repeat the text, source and translation of another example. |
| `E15` | usage | A usage gives the positions and the length in words at which the keyword of the sense stands in the example. |
| `E16` | translation | An example has a translation in at least one language; a translation is a text that the markup can hold. |
| `E17` | link | A linked word is lowercase, is not a term of a sense in that language, and names each of its senses once. |
| `E18` | name | A keyword with a sense of the type name begins with a capital letter or a digit. |
| `E19` | duplicate sense | Two senses of one word do not share type, category, terms and definition. |
| `E20` | note | A note has a subject. |
| `E21` | credits | CREDITS.md is generated from the source list and the Bible texts and is up to date. |

## Conversion from format 2

Format 2 kept one row per sense in `ctd-*.cite` files and one row per example and sense in `ctd-*.example.cite` files. The conversion to format 3 was verified by rebuilding every format 2 row from the tables and comparing: the lexicon rows, the example rows, the link rows and the notes were equal. Two differences were intended:

- Every sense is a draft. A row without `q` in format 2 counted as confirmed; such rows are now status draft. `(q:draft, low confidence)` became status low, and any other remark became the note of a draft.
- A sentence that several senses used was stored once per sense and is now stored once.

The data files of format 2 became sets: `core`, `draft` and `digit-number` became `core`, `bible` and `bible`, and the `noun-*` files became `name`.
