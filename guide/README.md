# Guide data

Answers the Lai Siangtho guide can download: one topic per file, one folder
per language.

```
guide/<language>/<any folders>/<topic>.json
guide/en/help/bookmarks.json
guide/en/books/43-john.json
```

Every file here that is not Markdown is data. There is no index to keep up to
date: the app asks GitHub for this repository's file list and takes the files
under `guide/<language>/` for the reader's language and English. A topic that
has no file in the reader's language is shown from English, marked as such.

## The format

Each file is a [schema.org FAQPage](https://schema.org/FAQPage) in JSON-LD —
the format websites use to publish questions and answers — so any schema.org
or JSON-LD tool reads it.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "name": "Bookmarks",
  "inLanguage": "en",
  "dateModified": "2026-09-30",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "How do I bookmark a verse?",
      "alternateName": ["mark a verse", "save a verse"],
      "acceptedAnswer": { "@type": "Answer", "text": "Press the verse number and choose the bookmark…" },
      "potentialAction": { "@type": "Action", "target": "laisiangtho:pane/marks" }
    }
  ]
}
```

| Field | Required | Meaning |
|---|---|---|
| `name` (page) | yes | The topic, as a person would call it |
| `inLanguage` | no | Must agree with the folder when given |
| `dateModified` | no | When the file was last changed |
| `mainEntity` | yes | The questions |
| `name` (question) | yes | The question, as a reader would ask it |
| `alternateName` | no | Other ways of asking; they help the guide match |
| `acceptedAnswer.text` | yes | The answer, plain text |
| `potentialAction.target` | no | The button the answer offers (below) |

### Buttons

| Target | Does |
|---|---|
| `laisiangtho:command/<id>` | runs a command, e.g. `search.open` |
| `laisiangtho:doc/<id>` | opens a page, e.g. `library`, `settings`, `memory` |
| `laisiangtho:pane/<id>` | shows a sidebar pane, e.g. `marks`, `plan`, `tags` |
| `laisiangtho:palette/<text>` | opens the palette with the text typed, e.g. `compare` |
| `laisiangtho:passage/<book>/<chapter>[/<verse>]` | goes to a passage; books are numbered 1–66 |

A target this version of the app does not know is shown without a button.

## Adding a language

Copy `en/` to the language's two- or three-letter code (`nb/`, `my/`,
`ctd/`), translate the `name`, `alternateName` and `text` fields, and set
`inLanguage`. Leave the targets as they are. A topic not yet translated keeps
being shown in English.

## Checking a change

From a checkout of the app (laisiangtho/lab):

```sh
node scripts/guide-check.mjs ../bible/guide
```

It reads every file the way the app does and names each problem with its
file and question. The app refuses a file that fails, and says which.

## Writing answers

- Short: a sentence or three. The button does the rest.
- Say what to press, not where it is: "Press the verse number and choose…".
- For the books of the Bible, keep to what is widely agreed, and say so
  plainly where authorship or dates are disputed.
