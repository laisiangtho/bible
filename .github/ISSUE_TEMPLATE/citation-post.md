---
name: Citation post
about: Propose new or corrected dictionary rows
title: "[CITE]"
labels: cite
assignees: ''

---

Rows follow markup version 1. The full rules are in `cite/Markup.md`; the allowed types and categories are in `cite/configuration.json`.

### Rows

One row per line, one sense per row.

```text
keyword = (t:type) (c:category) (w:term/term) (d:definition) (e:example with ~) description
```

```text
kipat = (t:v) (w:begin/start/open/first) (e:a ~ cil)
in = (t:ppm) (d:postpositional marker indicating place or time) (e:a kipat cil ~)
Eden = (t:name) (c:land) (w:Eden) (e:~ huan)
vantungte = (t:n) (w:heavens) (b:vantung)
```

### Source

Verse or other source for each row, as book.chapter.verse where it applies.

### Checklist

- [ ] The keyword is spelled as in the Bible text and contains no parentheses.
- [ ] Each row has `t` and at least one of `w` and `d`.
- [ ] Parentheses are used only for attributes.
- [ ] Each example contains `~` in place of the keyword.
- [ ] A row that is not confirmed by a speaker carries `(q:...)`.
