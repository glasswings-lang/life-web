# Plan: writing pieces, moving writing, and finding it again

Written 2026-09-11. Everything below is built. Nothing agreed is waiting.

## Why

Not everyone who writes in the life web knows HTML or Markdown, and even for those who do, the note
box surprised people:

- Tags typed in the note box turned into visible text.
- A single line break (Shift+Enter) was merged away, so lines ran together.
- `###` made a level-4 heading, because every # counted one level below the page title.
- Tags typed in the whole-page editor were saved as typed. A heading typed inside a paragraph then
  broke the page's shape.

## The note box

- HTML typed in the note box is real HTML. Scripts, styles, frames, event attributes and script
  links stay as visible text.
- `##` is level 2, `###` is level 3, up to `######`. A single `#` is level 2, so the page title
  stays the only level 1 typed with marks.
- A line break you type stays a line break. A blank line starts a new paragraph.
- A heading typed mid-paragraph is lifted out of the paragraph.
- Anyone who knows HTML or Markdown can still type it and it works. Nobody has to.

## Saying what a piece is before typing it

- The Add page asks "What is it?" before the note box. The choices are Paragraph, Heading level 1 to
  6, Bulleted list, Numbered list and Quote, in one box. HTML has no heading level beyond 6.
- Paragraph is first, and is the note box as it always was, marks and tags included.
- A heading is the words typed, on one line. A list is one item per line typed. A numbered list gets
  its numbers from the page, and one number typed at the start of a line is taken off. A quote can
  hold paragraphs.
- It works for adding at the end of a page and for adding after a chosen piece.

## Moving and sorting notes

- A page with two or more notes gets a "Move or sort notes" link. It is added as the page is served,
  never written into the file.
- Each note there has a "Move this note to" list: the top, the bottom, after another named note, or
  Put it away. The note moves whole, with its date and everything under it.
- "Newest first" and "Oldest first" put every note in date order. Anything between notes stays in
  its gap. Notes from the same minute keep their order, and a note with no readable date goes last.
- The page as it was is kept beside it as a .bak file, and "Go back to the previous version" swaps
  them round.
- If the page changed after the list was shown, nothing is moved and the fresh list is shown.

## Moving any writing

- On the Edit page, each piece is one group named after it, holding its words box and Save, its
  Add link, and one "Move it to" list with a Move button. There is no separate move page.
- The list holds the top and bottom of this page, after each other piece, onto each other page, and
  Put it away, last. The top and bottom are above and below all the writing and notes, never inside
  a note.
- A heading moves on its own, because people put writing under the wrong heading and it must not be
  dragged along. A heading with writing under it has one tick box, "Take the pieces under it too":
  its section, down to the next heading at its level or above, never past a note's edge or the spot
  new notes go.
- Onto another page goes to its bottom. With nothing chosen in the list, a name typed in "or onto a
  new page called" makes that page and moves it there. Links inside are rewritten so they still work
  from there.
- Put away, it is kept in _deleted/pieces in a file of its own that says which page it came from.
- A level 1 heading chosen from the Add page is a piece like any other. The page's own title is not.
- Every piece has a "Pick this one" tick box. At the bottom of the Edit page, one list and one "Move
  the picked ones" button move every picked piece together, in the order they were on the page.
- A note with nothing left in it shows on the Edit page where it sits, with "Put this note away".

## Bringing back what was put away

- A Put away page lists everything put away, in three parts: writing, pages, and folders. The front
  page's Waiting list links to it, with a count, whenever something is there. So do Repairs, the
  Not found page, and the page that asks before putting a page away.
- Writing comes back at the bottom of the page it came from, or any page chosen, or a new page named.
  Its links are fixed for wherever it lands.
- A page comes back to the address it had, already typed in its box, or any address typed instead.
- A folder with nothing of its name left at the top is one line, with one button to bring the whole
  folder back under its own name, and a link to see its pages and bring them back one at a time.
  A page put away from a folder that is still there is listed on its own.

## Finding things

- Search finds every word typed anywhere on a page, in any order, so a half-remembered wording still
  finds it. A word counts inside a longer one. A tick box keeps the exact-phrase way. No tags.
- "Narrow it down" searches one page, one folder and the folders inside it, one kind's pages, or
  notes written between two dates. Each is left empty to not narrow by it. Once a date is given,
  only dated notes are searched.

## How the pages read

Every page follows Loose ends and Repairs. Each thing a button acts on is in a group named after it,
so a screen reader says which thing before any box in it. Just before each button, a sentence
starting "Pressing this" says plainly what will happen, and when it helps, that nothing is lost.
Words on pages are short, simple and gentle, and use page titles rather than file names.

## Rules this has to keep

No JavaScript. No browser storage. No database. The file is the record. Every capability is a
control you can see and press. Never block the writer. No `autofocus`. Real `<label for>` on every
control.

## How it gets checked

Every change gets tests in the `test_*.py` files, and the code is broken on purpose to confirm the
tests notice. The built program then runs against a throwaway folder, never the live pages. The
reading order of each changed screen is laid out with an HTML parser, in element order, the way a
screen reader moves through it.

## Not tried yet

- Hearing any of this through a screen reader.
- Pressing Enter in a text box to press its button.
