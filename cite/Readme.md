# Cite

Source of the Zolai–English dictionary. One row describes one sense of one Zolai keyword.

| Path | Content |
| --- | --- |
| `Markup.md` | The row format, version 2. |
| `configuration.json` | Every closed list the format refers to: files, attributes, types, categories, fields, sources, translation languages, rules. Read by the tooling and by readers. |
| `ctd-*.cite` | The data files listed under `file` in `configuration.json`. |
| `ctd-core.cite` | The core lexicon: general vocabulary of everyday life and of modern subjects. |
| `ctd-draft.cite` | The Bible lexicon: vocabulary and names drawn from the Bible text, sorted by keyword. |
| `ctd-*.example.cite` | The examples of each data file, one row per example, keyed by sense. |
| `ext/ctd-*.cite` | Terms and definitions in a further language, keyed by sense. Optional. |
| `index/` | Generated keyword index and English term index. Never edited by hand. |
| `ctd-core-notes.txt` | English concepts of the core lexicon that still lack a Zolai keyword. |
| `ctd-draft-notes.txt` | Notes for the editor left while rows were drafted and enriched: senses left out, doubtful types, suspected misprints in the Bible text. |

## Commands

Python 3.9 or newer, standard library only. Every command runs from the repository root and reads `cite/configuration.json`. A command that writes files is a dry run unless `--apply` is given.

```shell
python3 -m assist cite check                  # every broken rule, with file and line
python3 -m assist cite check --summary        # counts per rule
python3 -m assist cite format --apply         # canonical spacing and attribute order
python3 -m assist cite convert --apply        # sense numbers for new rows; rows of an earlier markup version
python3 -m assist cite index --apply          # regenerate index/*.txt
python3 -m assist cite rename OLD NEW --apply # respell a keyword everywhere
python3 -m assist cite words --apply          # regenerate word/*.json
python3 -m assist cite lookup vantung         # rows of a Zolai keyword
python3 -m assist cite lookup beersheba       # hyphens, spaces and capitals are ignored: finds Be-ersheba
python3 -m assist cite lookup --english heaven
python3 -m assist cite lookup --english mom   # no sense has the term: shows the closest senses of ext/eng-ctd.cite
python3 -m assist cite search kipat cil       # verses with the word, and parallel verses
python3 -m assist cite todo --limit 100       # most frequent words without a row
python3 -m assist cite examples               # rows whose examples do not yet show every English term
python3 -m assist cite credits --apply         # regenerate CREDITS.md from the source list
python3 -m assist cite parse > cite.json      # every row as JSON, only when the check passes
python3 -m unittest discover -s assist/tests -t .
```

Exit status: `0` success, `1` findings or nothing found, `2` a condition that stops the command.

## Adding rows

1. `todo` lists the most frequent words of the Tedim Bible text that have no row.
2. `search` shows a word in its verses, next to the same verses in the reference translations.
3. The row is written in the fitting data file, following `Markup.md`. A general sense goes to `ctd-core.cite`, a sense specific to the Bible text to `ctd-draft.cite`; a sense is never written in both.
4. `convert --apply` gives the new row its sense number, and its examples are written in the example file under that sense key.
5. `index --apply` regenerates the indexes.
6. `check` passes before the change is committed.

## Confirmed and unconfirmed rows

Each data file is sorted by keyword.

- A row without `q` is confirmed by a speaker of the language.
- A row with `(q:draft)` was drafted from the Bible text and is not yet confirmed; `(q:draft, low confidence)` marks thin evidence. A row is confirmed by correcting it where needed and removing `q`.
- `r` names where a sense or an example is attested: a Bible verse or a listed source. An example taken from the Bible text is an exact fragment of the verse in its `r`.
- An example row is written Zolai first, then ` | `, then its English translation. Every English term of `w` is meant to be shown by three examples whose translation uses that term; `examples` lists the rows that fall short. A word that is rare in the Bible text stays short until a speaker adds examples.
- A core row drafted from dictionary data names its source in `r`, as in `(r:zai:money)`, and carries `(q:draft)` until a speaker confirms it.
- `ext/eng-ctd.cite` links common English words that are not a term of any sense to the closest senses, found through the Moby Thesaurus and judged one by one. Every link carries `q` until a speaker confirms it. `ctd-core-notes.txt` lists the common words for which no sense is close enough.
- A core row drafted from the news articles of Zomi Daily and Tongsan names the articles in `r`, as in `(r:zd:20522)`, and its examples are exact fragments of sentences of those articles. Its meaning was worked out from the sentences and from dictionary data without a parallel English text, so every such row carries `(q:draft)` or `(q:draft, low confidence)`. The articles themselves are not part of this repository.
- A core row drawn from the grammar book Paunam Khenna leh Kampau Luanzia names the page in `r`, as in `(r:pk:165)`. The book states many meanings, opposites and equivalents itself; such rows still carry `(q:draft)` until confirmed, and `(q:draft, low confidence)` where the meaning is inferred. The book itself is not part of this repository.
- A row of type `todo` marks a word whose meaning could not be told from the verses; its `q` says why.
- A row of type `see` redirects a form that occurs only as one part of a hyphenated word to the full word, as `ersheba` to `Be-ersheba`. A redirect carries no `q`.
- Draft rows for words that occur 5 times or more were read a second time against the verses. Draft rows for words that occur 1 to 4 times were read once.

## Word lists

`word/{language}-ord-{model}.json` holds every distinct written form of one model, most frequent first. Each word carries the number of occurrences `n` and the first verse `r` as book.chapter.verse.

```json
{
  "language": "ctd",
  "model": "plain",
  "identify": ["3561", "tedim1932"],
  "count": 22192,
  "word": [
    {"w": "a", "n": 146508, "r": "1.1.1"}
  ]
}
```

| Model | Content |
| --- | --- |
| `plain` | Runs of letters. A hyphen or apostrophe ends a word. |
| `dash` | Whole written forms that contain a hyphen. |
| `apostrophe` | Whole written forms that contain or end with an apostrophe. |
| `exclamation` | Written forms directly followed by an exclamation mark. |
| `question` | Written forms directly followed by a question mark. |
| `number` | Runs of digits. |

A form that starts a sentence is counted under its lowercase spelling when, inside sentences, the lowercase spelling is the more frequent one. Names keep their capital.

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
