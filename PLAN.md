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

Then moving and sorting notes:

- A page with two or more notes gets a "Move or sort notes" link. It is added as the page is served,
  never written into the file.
- Each note there has a "Move this note to" list: the top, the bottom, or after another named note.
  Pick one and press Move once. The note moves whole, with its date and everything under it.
- "Newest first" and "Oldest first" put every note in date order. Anything between notes stays in
  its gap. Notes from the same minute keep their order, and a note with no readable date goes last.
- The page as it was is kept beside it as a .bak file, and "Go back to the previous version" swaps
  them round.
- If the page changed after the list was shown, nothing is moved and the fresh list is shown.

## Agreed so far

**Say what a piece is before typing it.** Next to the note box is a choice of paragraph, heading,
list, or quote. Pick one, type the words, save. No marks to remember and nothing to select. For a
list, each line typed becomes one item. It's a visible control, following "simple is gold".

**Line breaks stay where they were typed.** A blank line still starts a new paragraph. A single line
break becomes a real line break, the way WordPress does it.

**Heading marks mean what Markdown says.** `##` is level 2, `###` is level 3, up to `######`. A
single `#` still stops at level 2, so the page title stays the only level 1.

**Anyone who knows HTML or Markdown can still type it** and it works. Nobody has to.

**A chosen heading can be any level from 1 to 6.** The choice lists them all by number. HTML has no
level beyond 6.

## Still to decide

- Whether tags typed in the note box become real HTML. The suggestion is yes, with scripts,
  styles, event attributes and `javascript:` links still blocked.
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
