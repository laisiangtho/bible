# Cite

Data of the Zolai–English dictionary, format 3. A word is stored once, each of its meanings is a sense, and every example sentence is stored once and linked to the senses it shows. Rows are linked by ids.

| Path | Content |
| --- | --- |
| `Format.md` | The tables, the ids, the markup in which entries are typed, and the rules. |
| `configuration.json` | Every table, column and closed list the format refers to: status codes, relation kinds, sets, types, categories, fields, sources, rules. Read by the tooling and by readers. |
| `word/` | Every written form. |
| `sense/` | Every meaning of a word: type, category, field, set, status, origin, source. |
| `gloss/eng/` | Terms and definition of a sense in English. A further language is a further folder. |
| `relation/` | Synonyms, antonyms, bases, joined forms, variants and redirects. |
| `example/` | Every example sentence or fragment, once. |
| `usage/` | Which sense an example shows and where the keyword stands in it. |
| `translation/eng/` | English translation of each example. |
| `link/eng.tsv` | Common English words that are not a term of any sense, each sent to the closest senses. |
| `note/open.tsv` | Open points: concepts without a keyword, words whose meaning is not settled, notes for the editor. |
| `sequence.tsv` | The highest id given out for words, senses and examples. |
| `CREDITS.md` | Generated credits: sources and Bible texts. |
| `inbox/` | Markup files being typed or pulled. Not part of the repository. |

A table file is tab-separated text with a header line. A large table is split into files of a few hundred kilobytes, named by the block of ids they hold. No index or export is stored: every command reads the tables directly.

## Commands

Python 3.9 or newer, standard library only. Every command runs from the repository root and reads `cite/configuration.json`. A command that writes files is a dry run unless `--apply` is given.

```shell
python3 -m assist cite check                  # every broken rule
python3 -m assist cite check --summary        # counts per rule
python3 -m assist cite lookup vantung         # senses of a Zolai word, with examples
python3 -m assist cite lookup beersheba       # hyphens, spaces and capitals are ignored: finds Be-ersheba
python3 -m assist cite lookup --term heaven   # senses that have an English term
python3 -m assist cite lookup --term mom      # no sense has the term: shows the closest senses of link/eng.tsv
python3 -m assist cite lookup khut --json     # the same as data
python3 -m assist cite find "wash"            # a text anywhere: spellings, glosses, examples, translations
python3 -m assist cite show s19435 e12061     # the rows behind ids or sense keys, as markup
python3 -m assist cite pull khut --apply      # write inbox/khut.cite: the rows of the word, ready to edit
python3 -m assist cite pull khut --related    # with the words one relation or link away
python3 -m assist cite import khut            # dry run of inbox/khut.cite: what each row would do
python3 -m assist cite import khut --apply    # change the tables, mark the rows of the file as done
python3 -m assist cite import ./notes/new.cite
python3 -m assist cite set core khut.2 --apply # move senses to another set
python3 -m assist cite search kipat cil       # Bible verses with the word, and parallel verses
python3 -m assist cite todo --limit 100       # most frequent words of the Bible text that the lexicon lacks
python3 -m assist cite examples               # senses whose examples do not yet show every English term
python3 -m assist cite credits --apply        # regenerate CREDITS.md from the source list
python3 -m unittest discover -s assist/tests -t .
```

Exit status: `0` success, `1` findings or nothing found, `2` a condition that stops the command.

## Adding and changing entries

Entries are typed as markup, one row per sense or example, and imported. The tables are not edited by hand: one new sense with an example touches up to eight files and needs new ids.

1. `todo` lists the most frequent words of the Tedim Bible text that the lexicon lacks; `search` shows a word in its verses, next to the same verses in the reference translations.
2. New rows are typed into a file in `inbox/`, following `Format.md`. To change what is stored, `pull WORD --apply` writes the rows of the word into `inbox/WORD.cite` with their ids and with comments that say what else names the word.
3. `import FILE` reports what each row would do: `inserted`, `replaced`, `unchanged` or `removed`, with the ids. A row that cannot be imported is reported with its line, and nothing is written.
4. `import FILE --apply` writes the tables and turns every imported row of the file into a comment starting `# done`, so a second run does nothing.
5. `check` passes before the change is committed. The import already runs the full check on the result and refuses a change that breaks a rule.

An import is done on top of the latest `master`, one branch at a time: ids are given in order, and two branches that import separately would give the same ids to different rows.

```text
# a sense and an example; no i, so a new sense, and a new word when the word is not yet stored
khut = (t:n) (w:hand) (d:the hand of a person) (r:46.16.21)
khut.1 = ka ~ tawh kong gelh hi | I write to you with my own hand (r:46.16.21)

# replace the whole sense khut.1; a pulled row already carries (i:1)
khut = (i:1) (t:n) (w:hand) (d:the hand of a person) (r:46.16.21) (q:reviewed)

# retire a sense, remove an example from a sense
- adah = (i:2)
- khut.1 = Na ~ sil den in | always wash your hands (e:e12061)
```

## State of the data

- Every sense is a draft until it is reviewed: status `draft`, or `low` where the evidence is thin. The conversion from format 2 kept `low` and made every other sense `draft`, including those that had no remark. The status codes are listed under `status` in `configuration.json`; a sense becomes `confirmed` only when a speaker of the language confirms it.
- A sense belongs to one set: `core` for general vocabulary, `bible` for vocabulary drawn from the Bible text, `name` for the lists of months, days, clans, places, persons and books.
- `source` names where a sense or an example is attested: a Bible verse or a listed source. An example taken from the Bible text is an exact fragment of the verse it names.
- Every English term of a sense is meant to be shown by three examples whose translation uses that term; `examples` lists the senses that fall short. A word that is rare in the texts stays short until a speaker adds examples.
- A sense drafted from dictionary data names its source, as in `zai:money`.
- `link/eng.tsv` links common English words that are not a term of any sense to the closest senses, found through the Moby Thesaurus and judged one by one. `note/open.tsv` lists the common words for which no sense is close enough.
- A sense drafted from the news articles of Zomi Daily and Tongsan names the articles, as in `zd:20522`, and its examples are exact fragments of sentences of those articles. Its meaning was worked out from the sentences and from dictionary data without a parallel English text. The articles themselves are not part of this repository.
- A sense drawn from the grammar book Paunam Khenna leh Kampau Luanzia names the page, as in `pk:165`. The book states many meanings, opposites and equivalents itself; where the meaning is inferred the status is `low`. The book itself is not part of this repository.
- A sense of type `todo` marks a word whose meaning could not be told from the verses; its note says why.
- A redirect sends a form that occurs only as one part of a hyphenated word to the full word, as `ersheba` to `Be-ersheba`.

## Working notes

### Affixes to describe

`ki`, `na`, `mah`, `ah`, `in`, `ding` and similar particles, postpositional markers and determiners that attach as prefix or suffix need rows of their own. A form built with one of them names its base in the attribute `b`.

- [ ] ending in `in`, `ah`, `a`, `pa`, `nu`, `mi`, `ni`, `pi`, `te`, `teng`
  - `pa`: `mipa/hihpa/huapa`
  - `nu`: `minu/hihnu/huanu`
  - `mi`: `tuami/hihmi/gammi`
  - `ni`: `tuni/tuani/nipini`
  - `pi`: `golpi/haupi/hoihpi`
  - `te`: `nate/mite/lote/gamte/pasiante`
  - `teng`: `miteng/loteng/vanteng`
- [ ] ending in `sak`, `pen`
  - `sak`: `hisak, beisak, hoihsak`
- [ ] `ki`~`sak`, where an adjective or verb is enclosed by `ki` and `sak`
- [ ] technology
- [ ] daily

### Candidate categories

Zolai labels considered for the category list. A label becomes usable in a row once it is added under `category` in `configuration.json`.

muhtheih, lawntheih, hihtheih, zaktheih, simtheih,
uptheih, zuihtheih, zontheih,
lametna, upna, phawkna, lunggulhna, lungdamna,
phatna, selphona,
thu, la, numbet, symbol, phrase,
lai, pau, kammal,
tangthu, gentehna, paunak,
thusim, thupiang, thuthak,
thuhoih, thusia, thupha,
hoih, sia, pha, manpha,
mi, ganhing, singkung, lopa, nahteh,
ulian, kumcing, naupang, naunget,
mual, gun, tui, bual, suang, tuipi,
pasal, numei, nupa, panu, min, beh
gam, khua, khuapi, khuaneu,
sak, nip,
sang, niam,
lim, aw,
bawl, sem, lak, pia, ngen, thum,
nektheih, dawntheih,
zopna (lai-zom), khupna,
kamsang, pasian thugen,
gentehna, ciaptehna, mualsuang,
lungdam, dah, khasia,
kampha, kamsia,

Example: gen -> zaktheih

### Word division

The same sentence is written with different word division. The keyword of a row follows the division used in the Bible text.

```text
1. an ne khin ta maw? an ne khin maw? an ne ta maw?
2. annne khinta maw?
3. an ne khinta maw?
4. an nekhinta maw?

1. koi ah pai ding?
2. koi ah paiding
3. koi ahpai ding
4. koiah pai ding
5. koiah paiding

1. lei tang pen pa sian bawl sa a hi hi
2. leitang pen pasian bawlsa ahihi.
3. leitang

1. ui san - uisan
```

### Bitexts

A bitext is a merged document composed of both source- and target-language versions of a given text. A corpus is a collection of written texts, especially the entire works of a particular author or a body of writing on a particular subject.

Bitexts can markedly increase student reading and comprehension in a second language. Because the raw volume of text they read jumps so dramatically, students are exposed to a much wider vocabulary. Moreover, when text is easier to read, students can begin to understand large-scale features of style and grammar.

Bitexts have long been a mainstay of second-language education for European languages, and are equally valuable for students of English and Southeast Asian languages.

Bitext in kammal/laimal dangte simna leh teihna dingin hong kangto sak hi. Tua ahihmanin laigual a simnate hang tampitak khangtosak hi, sangnaupangte pen khangto mahmah uh a, laimalte a sim uh ciangin, amaute laimal leh grammer gualdang pen theihna leh muhna kihong khia hi.
