# Plan: writing pieces, and moving and sorting notes

Written 2026-09-11. Nothing here is built yet. It's written down first so any part of it can be
changed before it becomes code.

## Why

Not everyone who writes in the life web knows HTML or Markdown, and even for those who do, the note
box surprised people:

- Tags typed in the note box turn into visible text.
- A single line break (Shift+Enter) is merged away, so lines run together.
- `###` makes a level-4 heading, because every # counts one level below the page title.
- Tags typed in the whole-page editor are saved as typed. A heading typed inside a paragraph then
  breaks the page's shape.

## Done, 2026-09-11

These went in first, as their own small change, before the rest of the plan:

- HTML typed in the note box is real HTML. Scripts, styles, frames, event attributes and script
  links still stay as visible text.
- `###` is level 3, up to `######`. A single `#` is level 2.
- A line break you type stays a line break.
- A heading typed mid-paragraph is lifted out of the paragraph.

## Agreed so far

**Say what a piece is before typing it.** Next to the note box is a choice of paragraph, heading,
list, or quote. Pick one, type the words, save. No marks to remember and nothing to select. For a
list, each line typed becomes one item. It's a visible control, following "simple is gold".

**Line breaks stay where they were typed.** A blank line still starts a new paragraph. A single line
break becomes a real line break, the way WordPress does it.

**Heading marks mean what Markdown says.** `##` is level 2, `###` is level 3, up to `######`. A
single `#` still stops at level 2, so the page title stays the only level 1.

**Anyone who knows HTML or Markdown can still type it** and it works. Nobody has to.

**Notes move as whole units.** A saved note keeps its time stamp and everything under it. Each note
gets a "move this to" list: the top of the page, the bottom of the page, or after a named note. Pick
one and press Move once. The note list is a plain dropdown and a plain button, so no JavaScript and no
pressing Move Up twenty times.

**A sort button** puts every note in order by its time stamp, newest first or oldest first. It
rearranges the file itself, so the file stays the record, just tidier.

## Still to decide

- Whether tags typed in the note box become real HTML. The suggestion is yes, with scripts,
  styles, event attributes and `javascript:` links still blocked.
- A heading picked from the choice: which level? One option is "heading" and "smaller heading".
  Another is taking the level below the heading before it.
- Whether pieces outside notes, meaning things typed straight into a page, need a way to move too.
  Notes first.
- Whether a numbered list is its own choice or a tick box beside "list".

## Rules this has to keep

No JavaScript. No browser storage. No database. The file is the record. Every capability is a
control you can see and press. Never block the writer. No `autofocus`. Real `<label for>` on every
control.

## How it gets checked

Every change gets tests in the existing `test_*.py` files. The built program then runs against a
throwaway folder, never the live pages. The reading order of each changed screen gets dumped with an
HTML parser, so it can be checked the way NVDA would move through it.
