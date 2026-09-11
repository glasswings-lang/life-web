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

Then saying what a piece is before typing it:

- The Add page asks "What is it?" before the note box. The choices are Paragraph, Heading level 1 to
  6, Bulleted list, Numbered list and Quote, in one box.
- Paragraph is first, and is the note box as it always was, marks and tags included.
- A heading is the words typed, on one line. A list is one item per line typed. A numbered list gets
  its numbers from the page, and one number typed at the start of a line is taken off. A quote can
  hold paragraphs.
- It works for adding at the end of a page and for adding after a chosen piece.

## Agreed so far

**Line breaks stay where they were typed.** A blank line still starts a new paragraph. A single line
break becomes a real line break, the way WordPress does it.

**Heading marks mean what Markdown says.** `##` is level 2, `###` is level 3, up to `######`. A
single `#` still stops at level 2, so the page title stays the only level 1.

**Anyone who knows HTML or Markdown can still type it** and it works. Nobody has to.

**Everything that can be written can be moved**, not only notes. Writing put straight onto a page
moves too.

**A chosen heading can be any level from 1 to 6.** The choice lists them all by number. HTML has no
level beyond 6.

**Bulleted list and numbered list are two options in the same box**, not a tick box. For a numbered
list the page adds the numbers, so they are not typed.

## Still to decide

- Whether tags typed in the note box become real HTML. The suggestion is yes, with scripts,
  styles, event attributes and `javascript:` links still blocked.

## Rules this has to keep

No JavaScript. No browser storage. No database. The file is the record. Every capability is a
control you can see and press. Never block the writer. No `autofocus`. Real `<label for>` on every
control.

## How it gets checked

Every change gets tests in the existing `test_*.py` files. The built program then runs against a
throwaway folder, never the live pages. The reading order of each changed screen gets dumped with an
HTML parser, so it can be checked the way NVDA would move through it.
