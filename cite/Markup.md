# Cite Markup

Version 1. Row format of the Zolai–English dictionary source files in this directory.

A data file is plain text. Each row describes one sense of one Zolai keyword. Every closed list named in this document (attributes, types, categories, rules, files) is stored in `configuration.json`; the tables below are copies of it. When the two differ, `configuration.json` is authoritative.

## Files

- A data file is listed under `file` in `configuration.json` and named `ctd-{file}.cite`, for example `ctd-draft.cite`. A listed file that does not exist is an error, and so is a `.cite` file in this directory that is not listed.
- A file may require attribute values. Every described row of `ctd-noun-beh.cite`, for example, carries `(t:name)` and `(c:beh)`.
- Encoding is UTF-8 without a byte order mark. Lines end with a single line feed. The file ends with exactly one line feed.
- Tabs are not allowed.

## Lines

Each line is one of three kinds.

| Kind | Form | Meaning |
| --- | --- | --- |
| blank | empty | Separates groups of rows. No meaning. |
| comment | first character is `#` | Text for editors. Not data. |
| row | anything else | One sense of one keyword. |

## Row

```text
row         = keyword [ " = " body ]
body        = attribute { " " attribute } [ " " description ]
attribute   = "(" key ":" value ")"
value       = item { "/" item }      for a list attribute
            | item                   for any other attribute
item        = text without "(" and ")"
description = text without "(" and ")"
```

- The first `=` on the line separates the keyword from the body.
- A row without `=` is a keyword-only row: the word is known but not yet described. It may be the target of a synonym, antonym, base or cross-reference.
- A row with `=` starts its body with the attribute `t`.
- Parentheses are reserved for attributes. Prose that would use parentheses uses commas instead.
- Each attribute key occurs at most once in a row.

## Keyword

The keyword is the Zolai headword, spelled as it is written in running text.

- Pattern: `^[A-Za-z0-9]+(?:[ '-][A-Za-z0-9]+)*'?$`
- Allowed characters are the letters A to Z and a to z, the digits, and between words one space, one hyphen or one apostrophe. A final apostrophe is allowed.
- Case is significant. `Pasian` and `pasian` are different keywords.
- A keyword of type `name` starts with an uppercase letter or a digit.
- Another spelling of the same word is not written into the keyword; it goes into the attribute `v`.
- A word written with a hyphen in the Bible text keeps the hyphen in its keyword, so the row shows how the word is written. Lookup ignores hyphens, spaces, apostrophes and capitals: `ze-et` is found as `zeet` and as `ze et`.
- A form that occurs only as one part of a hyphenated word has a redirect row to the full word.

## Attributes

| Key | Name | Value | List | Meaning | Example |
| --- | --- | --- | --- | --- | --- |
| `t` | type (required) | code | no | Word class of the keyword. Exactly one code from the type list. | `(t:v)` |
| `c` | category | code | yes | What kind of thing the keyword names. One or more codes from the category list. | `(c:land)` |
| `w` | term | English | yes | English word or words with the same meaning as this sense of the keyword. Items of one row are interchangeable; a different meaning goes on its own row. | `(w:begin/start)` |
| `d` | definition | English | no | English explanation of the meaning, used when no English term fits or in addition to one. May contain cross-references. | `(d:postpositional marker indicating place or time)` |
| `e` | example | Zolai and English | yes | Zolai phrase or sentence that uses the keyword, followed by its English translation. Each item is written Zolai first, then \|, then English. The keyword is written as ~ in the Zolai. | `(e:a kipat cil ~ \| in the beginning)` |
| `s` | synonym | Zolai keyword | yes | Keywords with the same meaning. Every item is a keyword that exists in the data. | `(s:leh)` |
| `a` | antonym | Zolai keyword | yes | Keywords with the opposite meaning. Every item is a keyword that exists in the data. | `(a:lian)` |
| `b` | base | Zolai keyword | no | The keyword this form is built from, for plural, suffixed and prefixed forms. One keyword that exists in the data. | `(b:vantung)` |
| `v` | variant | Zolai keyword | yes | Other spellings of the same keyword. An item is never the keyword of another row. | `(v:Shoute)` |
| `o` | origin | English | no | Language the keyword comes from, optionally followed by a comma and the source word. | `(o:Hebrew, kerub)` |
| `r` | reference | verse | yes | Bible verses where this sense occurs, written book.chapter.verse with book numbers 1 to 66. A verse range uses a hyphen. | `(r:1.1.1/1.2.4-6)` |
| `q` | query | English | no | Open question about the row. Its presence marks the row as not verified. | `(q:meaning not confirmed)` |

Canonical order: `t` `c` `w` `d` `e` `s` `a` `b` `v` `o` `r` `q`.

## Description

The description is free English text after the last attribute. It holds a remark on usage or grammar that is not the meaning itself. The meaning belongs in `w` or `d`. A row of any type except `see` and `todo` has at least one of `w` and `d`.

## Symbols

| Symbol | Name | Meaning |
| --- | --- | --- |
| `=` | separator | The first = on a line ends the keyword and starts the body. A line without = is a keyword-only row. |
| `#` | comment | A line whose first character is # is a comment. A comment cannot follow a row on the same line. |
| `(` `)` | attribute | Parentheses are reserved for attributes, written (key:value). They never appear in a keyword, inside a value or in the description. |
| `/` | list separator | Separates the items of a list attribute. In a text attribute and in the description it is an ordinary character. |
| `~` | keyword placeholder | Stands for the keyword of the row. Allowed only in the attribute e. |
| `\|` | translation separator | Inside one item of the attribute e, separates the Zolai example from its English translation. Allowed only in the attribute e, at most once per item. |
| `<>` | cross-reference | Encloses exactly one keyword that exists in the data. Allowed only in the attribute d and in the description. |

## Types

The attribute `t` takes exactly one of these codes.

| Code | Name | Meaning |
| --- | --- | --- |
| `n` | noun | Common noun. |
| `name` | proper name | Name of one person, people, place, clan, book or other individual thing. The keyword starts with an uppercase letter. |
| `v` | verb | Verb. |
| `adj` | adjective | Adjective. |
| `adv` | adverb | Adverb. |
| `pron` | pronoun | Pronoun. |
| `det` | determiner | Determiner, including possessive forms. |
| `prep` | preposition | Relation word translated by an English preposition. |
| `conj` | conjunction | Conjunction. |
| `part` | particle | Particle: a prefix, suffix or sentence-final word with a grammatical function. |
| `ppm` | postpositional marker | Marker placed after a word to show case, place, time or tense. |
| `num` | number | Cardinal or ordinal number, in words or digits. |
| `intj` | interjection | Interjection or exclamation. |
| `phrase` | phrase | Fixed combination of words listed as one keyword. |
| `see` | redirect | Row that only points to another keyword. The body is the type followed by exactly one cross-reference. |
| `todo` | to do | Keyword collected but not yet described. |

## Categories

The attribute `c` takes one or more of these codes. The category says what kind of thing the keyword names; the type says how the word behaves in a sentence. A new category is added to `configuration.json` before it is used in a row.

| Code | Name | Meaning |
| --- | --- | --- |
| `male` | male person | Name of a man. |
| `female` | female person | Name of a woman. |
| `people` | people | Name of a nation, tribe or group of people. |
| `beh` | clan | Zomi clan name. |
| `land` | land | Name of a country, region or territory. |
| `place` | place | Name of a place that fits no narrower category. |
| `city` | city | Name of a city. |
| `khua` | village or town | Name of a village or town. |
| `river` | river | Name of a river. |
| `mountain` | mountain | Name of a mountain. |
| `valley` | valley | Name of a valley. |
| `well` | well | Name of a well. |
| `tower` | tower | Name of a tower. |
| `star` | star | Name of a star or constellation. |
| `kha` | month | Month of the year. Rows are of type n. |
| `ni` | day of the week | Day of the week. Rows are of type n. |
| `book` | Bible book | Name of a book of the Bible. |
| `testament` | testament | Name of a testament of the Bible. |
| `animal` | animal | Animal, bird, fish or other living creature. |
| `plant` | plant | Plant or tree. |
| `stone` | stone | Stone or mineral. |
| `direction` | direction | Compass direction. |

## Senses, forms and links

- **Sense.** One row is one sense. A keyword with several meanings has several rows, in order of importance. The items of `w` in one row are interchangeable English terms for that sense; a different meaning is a new row.
- **Homograph.** Rows with the same keyword and different types are separate words that share a spelling.
- **Form.** A plural, suffixed or prefixed form that has its own row names its base in `b`. The relation is not repeated in the description.
- **Variant.** Another spelling of the same word is listed in `v` of the main row and has no row of its own.
- **Redirect.** A row of type `see` holds only a cross-reference to the row that carries the entry.
- **Unverified.** A row with `q` is not verified. The attribute is removed when a speaker of the language confirms the row.
- **Source.** A row may name the verses that support it in `r`. Book numbers follow the order of `ctd-noun-book.cite`, 1 for Genesis to 66 for Revelation.

## Canonical form

A row in canonical form has no leading or trailing space, single spaces only, the separator written as space, `=`, space, no space inside the parentheses or around `/`, the attributes in canonical order and the description last. A row that breaks only these points is valid in content and is repaired mechanically.

## Rules

The check is run from the repository root with `python3 -m assist cite check`. It reports every broken rule with the file, the line number and the rule, and fails when anything is reported. There are no warnings and no silent repairs. Rules of level `form` are repaired by `python3 -m assist cite format --apply`.

| Rule | Level | Name | Fails when |
| --- | --- | --- | --- |
| E01 | error | file | A listed file is missing, a data file in the directory is not listed, or a file is not UTF-8, starts with a byte order mark, or contains a tab or carriage return. |
| E02 | error | keyword | The keyword is empty or does not match the keyword pattern. |
| E03 | error | empty body | Nothing follows the separator. |
| E04 | error | parenthesis | A parenthesis is not part of a well-formed attribute: unbalanced, nested, or used in the description. |
| E05 | error | unknown attribute | The attribute key is not in the attribute list. |
| E06 | error | repeated attribute | The same attribute key occurs more than once in a row. |
| E07 | error | empty value | An attribute value or a list item is empty. |
| E08 | error | type | The attribute t is missing or its value is not in the type list. |
| E09 | error | category | A value of the attribute c is not in the category list. |
| E10 | error | meaning | The row has neither w nor d, and its type is not see or todo. |
| E11 | error | placeholder | The symbol ~ or \| is used outside the attribute e, an example item has no ~, or an item has more than one \|. |
| E12 | error | cross-reference | The symbols < and > are unbalanced, used outside d and the description, or do not enclose exactly one keyword. |
| E13 | error | unresolved keyword | A keyword named in s, a, b or a cross-reference does not exist in the data. |
| E14 | error | variant | A value of the attribute v is not a valid keyword, or is the keyword of a row. |
| E15 | error | reference | A value of the attribute r does not match book.chapter.verse. |
| E16 | error | duplicate | Two rows are identical in keyword, type, category, term and definition. |
| E17 | error | name case | The keyword of a row of type name does not start with an uppercase letter or a digit. |
| E18 | error | redirect | A row of type see has anything other than exactly one cross-reference after the type. |
| E19 | error | file scope | A described row lacks an attribute value that its file requires. |
| E20 | error | translation | An example item has no English translation after the Zolai. |
| F01 | form | separator spacing | The separator is not written as one space, =, one space. |
| F02 | form | spacing | The line has leading or trailing spaces, repeated spaces, spaces inside the parentheses or around a list separator, or a translation separator not written as one space, \|, one space. |
| F03 | form | attribute order | The attributes are not in the configured order. |
| F04 | form | description position | The description is not after the last attribute. |
| F05 | form | final newline | The file does not end with exactly one newline. |

## Examples

Valid rows:

```text
# keyword-only rows: known words, not yet described
kipan
kisin

kipat = (t:v) (w:begin/start/open/first) (e:a ~ cil | in the beginning) (s:kipan/kisin)
in = (t:ppm) (d:postpositional marker indicating place or time) (e:a kipat cil ~ | in the beginning)
vantung = (t:n) (w:heaven) the promised land
vantung = (t:n) (w:sky) the upper atmosphere
vantungte = (t:n) (w:heavens) (b:vantung)
hih = (t:pron) (w:this) (e:~ mun ah ding in | stand in this place)
hihte = (t:pron) (w:these) (e:~ pen Pasian nasepna hi | these are the work of God) (b:hih)
khat = (t:num) (w:one) (e:ni ~ | one day)
bilpi = (t:n) (c:animal) (w:hare)
Eden = (t:name) (c:land) (w:Eden) (e:~ huan | the garden of Eden)
Abraham = (t:name) (c:male) (w:Abraham) (r:1.17.5)
Sote = (t:name) (c:beh) (w:Sote) (e:nang bang beh? kei ~ hi ing | what clan are you? I am Sote) (v:Shoute)
khawlei-uikai = (t:n) (w:the Bear)
khawlei = (t:see) <khawlei-uikai>
singnai = (t:n) (w:honeydew) (q:meaning not confirmed)
```

Invalid rows:

| Row | Rule | Reason |
| --- | --- | --- |
| `Sote (Shoute) = (t:name) (c:beh) (w:Sote)` | E02 | Parentheses in the keyword. |
| `vantungte = (t:n) (w:heavens) (plural form of vantung)` | E04 | Parentheses outside an attribute. |
| `tua = (t:pron) (w:that) (w:those)` | E06 | Attribute repeated; one list is written `(w:that/those)`. |
| `suakta = (t:v) (w:get away//run away)` | E07 | Empty list item. |
| `saupi = (t:adjective) (w:long)` | E08 | Type not in the list. |
| `mial = (t:adv)` | E10 | Neither `w` nor `d`. |
| `khat = (t:num) (w:one) (e:ni khat)` | E11 | Example without `~`. |
| `khat = (t:num) (w:one) (e:ni ~)` | E20 | Example without an English translation. |
| `hiah = (t:adv) (w:here) of <place>` | E13 | `place` is not a keyword in the data. |
| `eden = (t:name) (c:land) (w:Eden)` | E17 | Name keyword in lowercase. |
| `vantung=(t:n) (w:heaven)` | F01 | Separator without spaces. |
| `kipat = (w:begin) (t:v)` | F03 | Attributes out of order. |

## Rows written before version 1

Rows written before version 1 are converted in two passes.

Mechanical pass, no decision needed, run with `python3 -m assist cite convert --apply`:

1. The separator and all spacing are put in canonical form.
2. An old type tag is replaced by the type and category in the table below.
3. A description that is wholly enclosed in one pair of parentheses loses the parentheses.
4. In a row without `w`, the description becomes the attribute `d`.
5. A description that is only `??` becomes `(q:?)`.
6. The attributes are put in canonical order and the description is moved to the end.

| Old type | Version 1 |
| --- | --- |
| `(t:names)` | `(t:name)` |
| `(t:prm)` | `(t:name)` `(c:male)` |
| `(t:prf)` | `(t:name)` `(c:female)` |
| `(t:people)` | `(t:name)` `(c:people)` |
| `(t:beh)` | `(t:name)` `(c:beh)` |
| `(t:land)` | `(t:name)` `(c:land)` |
| `(t:place)` | `(t:name)` `(c:place)` |
| `(t:city)` | `(t:name)` `(c:city)` |
| `(t:khua)` | `(t:name)` `(c:khua)` |
| `(t:river)` | `(t:name)` `(c:river)` |
| `(t:mountain)` | `(t:name)` `(c:mountain)` |
| `(t:valley)` | `(t:name)` `(c:valley)` |
| `(t:well)` | `(t:name)` `(c:well)` |
| `(t:tower)` | `(t:name)` `(c:tower)` |
| `(t:star)` | `(t:name)` `(c:star)` |
| `(t:kha)` | `(t:n)` `(c:kha)` |
| `(t:ni)` | `(t:n)` `(c:ni)` |
| `(t:book)` | `(t:name)` `(c:book)` |
| `(t:testament)` | `(t:name)` `(c:testament)` |
| `(t:animal)` | `(t:n)` `(c:animal)` |
| `(t:plant)` | `(t:n)` `(c:plant)` |
| `(t:tree)` | `(t:n)` `(c:plant)` |
| `(t:stone)` | `(t:n)` `(c:stone)` |
| `(t:direction)` | `(t:n)` `(c:direction)` |
| `(t:pronoun)` | `(t:pron)` |
| `(t:determiner)` | `(t:det)` |
| `(t:preposition)` | `(t:prep)` |
| `(t:number)` | `(t:num)` |
| `(t:interjection)` | `(t:intj)` |
| `(t:exclamation)` | `(t:intj)` |
| `(t:uppercase)` | `(t:todo)` |

Editorial pass: every row that still breaks a rule after the mechanical pass is corrected by hand. Typical cases are an example written in the description, an English word enclosed in `<` and `>`, a synonym that names a word without a row, and exact duplicates.

## Use by a language model

A language model that reads or writes rows is given this document and `configuration.json` in full.

- Output is rows only, one per line, in canonical form, with no surrounding text.
- A keyword is taken from the word lists in `word/` or from a Bible text in this repository. A keyword is never invented or respelled.
- Rows are checked with `python3 -m assist cite check` before they are offered for review.
- Every generated row carries `(q:...)` stating what is uncertain, and `(r:...)` naming at least one verse where the keyword occurs with that sense.
- Types and categories are chosen from the lists. When none fits, the row is given the type `todo` and the reason is stated in the description.
- A generated row is a draft. It becomes part of the dictionary when a speaker of the language removes `q`.
