# The life web — how it is built

Design notes for anyone changing this program, including its author
later. The rules below are settled: they were arrived at by using the
thing, and re-deciding them costs more than keeping them.

Paths, personal context and session handoffs are deliberately not here.

## What the program is

**One job: HTML cannot save anything.** A form only sends what was
typed to an address; something has to be listening. `Life_Web.exe` is that
something. It writes what a form sent into an HTML file.

Run it by pressing Enter on the exe. It serves the folder it sits in,
on 127.0.0.1 only. `Life_Web.log` next to it records start, stop, crashes
and request errors — added because a crash and a clean stop looked
identical from a browser.


## How it works

**Everything is insert-at-a-marker.** `<!-- here -->`, `<!-- fields -->`,
`<!-- entries -->`, `<!-- kinds -->`, `<!-- questions -->`,
`<!-- pointing here -->`. One mechanism, many uses. `insert(...,
before=True)` appends in order; the default puts newest first.

**Kinds are folders.** There is no list of kinds in the code and there
must never be one. A kind is `<slug>/_kind.html` (the shape its pages
take) plus `<slug>/index.html` (its listing and controls). Adding a
question inserts into `_kind.html`.

**Some things are filled when a page is served, never stored:** combo
boxes of another kind's entries, checkbox groups of the same, the list
of all kinds, the list of a kind's questions, and "what points here".
Read off disk each request, so nothing goes stale and there is no
rebuild step. This is the ONE place a served page differs from the file,
and it is safe because a form does nothing without the program running
anyway.

**Links are real.** A "points at another kind" answer stores
`<a href="../places/x.html">X</a>` in the file, not an id into a table.
Open any page with nothing running and it still works.

**Eleven answer types** (`kinds.TYPES`): short text, long text, number,
date, time, yes/no, one-of-a-list (radio), one-of-a-list (dropdown),
several-of-a-list (checkboxes), one of another kind, several of another
kind. The list-based ones take words typed one per line; the kind-based
ones point at pages.

**Kind index pages carry a version marker** (`kinds.INDEX_VERSION`).
Anything older is rebuilt at startup so improvements reach kinds that
already exist. **Bump it whenever `KIND_INDEX` changes shape.**


## Settled decisions — do not relitigate these

- **Simple is gold.** A new capability must be a control you can see and
  press, never a convention to remember. The operator rejected a `[[bracket]]`
  link syntax in favour of a combo box for exactly this reason.
- **The person using this writes HTML and wants to.** Do not build things that own the operator's
  markup. An earlier version generated pages from fragments and was thrown out.
- **No database, ever.** The reasons: you can't read it, can't fix it by hand, and it
  needs software to exist at all.
- **No browser storage.** Fragile, per-device, wiped with site data.
- **No JavaScript.** Plain forms are what works best with NVDA, and JS
  widgets are what break it.
- **The file is the record.** Nothing holds a second copy that can drift.
- **F5, not a refresh button.** That was the right call.
- **Never block the writer.** Every "pick a thing" has an "or a new one
  called" beside it. Realising something doesn't exist yet must never
  make you abandon what you were doing.
- **Follow ordinary form convention.** Fields in defined order, values
  in the boxes, one Save. The first version read backwards and was caught.
- **Don't pad anything with credit.** Acting on a decision is the
  acknowledgement. That was asked for explicitly.
- **No names of anyone in any file** — including plausible-sounding
  place or event names in examples. Use "First Place", "Second Event".


## Accessibility

It is built for NVDA running all the time, and checked with NVDA only. It has not been tested with JAWS or any other screen reader. What matters here and is done:
`<html lang="en">`, real `<label for>` on every control, a unique
`<title>` per page, failures explained in text on the page,
`<fieldset>`/`<legend>` for radio and checkbox groups.

**Never use `autofocus`.** It teleports a screen reader into a form and
skips everything above it — checked, not assumed.

Verify by dumping reading order with an HTML parser (headings, labels,
buttons, links in sequence) rather than describing intent. Skip
`<template>` contents when you do — they are not rendered and not in the
accessibility tree.


## Known gaps

- Removing a question changes the kind's shape for pages made afterwards.
  Existing pages keep the fields they were made with. Deliberate, but
  there is no migration.
- Search reads every page each time it is asked, so nothing is indexed
  and nothing goes stale. There are no filters.
- Flag-and-come-back is built: `[[words]]` mid-sentence marks a spot to
  link later, and the flagged list turns one into a real link
  afterwards. It exists because selection does not survive tabbing
  away, so nothing should have to be chosen while writing.
- Kind pages have exactly one navigation link, *Back to the top*. Getting
  between two kinds is up and back down.
- No page history. The pages folder is ordinary files: whatever backs up
  or versions the folder is what you have.


## Traps hit this session

- **Heredocs mangle escapes.** Writing Python via a bash heredoc turned
  `\b` and `\2` into literal control characters and broke the file
  twice. Use the Write/Edit tools for anything containing backslashes.
- **A comment that mentions the thing it describes gets found instead of
  the thing.** Bit twice: a comment containing `<template>` was matched
  as the template, and a comment listing `{{blanks}}` was filled in.
  Comments are stripped before searching now.
- **Broken checks.** Several of mine passed while testing nothing, or
  failed on the wrong thing: a test that searched `write.py` for
  `<article`; a character-count that reported 1,891 missing characters
  when nothing was missing; a "is this page current" check that matched
  `"Add a "` against *"Add a question"*. **Break a check on purpose and
  confirm it screams before believing it.**
- **A test fixture that copied the operator's live `index.html`** started failing
  the moment the operator used the app. Fixtures must be self-contained.
- **The exe locks while running.** Copying over it fails with "device or
  resource busy". Ask whoever is using it to close the window.


## Building and testing

```
cd C:\git-src\life-web
python test_forms.py
python -m PyInstaller --onefile --name Life_Web --console --clean --noconfirm --exclude-module tkinter forms.py
```

Then move `dist\Life_Web.exe` next to the operator's pages. `--exclude-module email`
breaks it (`http.server` needs it) — only exclude `tkinter`.

Test with `--folder` pointing at a throwaway copy. Never test against
`life-web` directly.
