#!/usr/bin/env python3
"""Checks for editing.py - changing words without seeing tags."""

import sys

import editing

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


PAGE = """<html lang="en"><head><title>First Entry</title></head><body>
<h1>First Entry</h1>
<nav><p><a href="index.html">Back</a></p></nav>
<h2>Origin</h2>
<p id="origin">Written in the first year about a character in <a href="first-place.html">First Place</a>, then noticed in the second.</p>
<h2>Notes</h2>
<p>First Entry, an example page</p>
<div class="addition">
<p class="when">2026-08-31 11:00</p>
<p>It was <strong>never</strong> only that.</p>
</div>
<p class="todo"><em>To check: the second question.</em></p>
<p>Something <span class="odd">unusual</span> here.</p>
<form method="post" action="/save"><p>Not writing either.</p><textarea name="note">a [[flag]] here</textarea></form>
</body></html>"""


# --- what counts as a piece --------------------------------------------

found = editing.blocks(PAGE)
check("the pieces are found in reading order",
      [(t, editing.as_words(i)[:22]) for _n, t, _a, i, _s, _e in found],
      [("h2", "Origin"),
       ("p", "Written in the first y"),
       ("h2", "Notes"),
       ("p", "First Entry, an exampl"),
       ("p", "It was never only that"),
       ("p", "To check: the second q"),
       ("p", "Something unusual here")])
check("a timestamp is not a piece you edit",
      any("2026-08-31" in editing.as_words(i) for *_x, i, _s, _e in found),
      False)
check("a paragraph inside the nav is not a piece",
      any(editing.as_words(i) == "Back" for *_x, i, _s, _e in found), False)
check("a paragraph inside a form is not a piece",
      any("Not writing either" in editing.as_words(i)
          for *_x, i, _s, _e in found), False)
check("the page title is not a piece",
      any(editing.as_words(i) == "First Entry" and t == "h1"
          for _n, t, _a, i, _s, _e in found), False)


# --- which pieces plain words can carry --------------------------------

check("plain words carry a plain paragraph",
      editing.simple_enough("Just words."), True)
check("plain words carry emphasis",
      editing.simple_enough("a <strong>very</strong> thing"), True)
check("plain words carry a link, because links are put back",
      editing.simple_enough('go to <a href="x.html">X</a>'), True)
check("an unknown tag inside means the box is not offered",
      editing.simple_enough('<em>x</em> and <span class="odd">y</span>'),
      False)
check("an attribute that would vanish means it is not offered",
      editing.simple_enough('<em id="k">x</em>'), False)


# --- changing a paragraph, and the link surviving ----------------------

new, trouble = editing.rewrite(PAGE, 1, "Written in the first year about "
                               "a character in First Place, then "
                               "noticed in the third.")
check("changing a paragraph reported no trouble", trouble, "")
check("the new words are there", "noticed in the third." in new, True)
check("THE LINK MADE BY THE BUTTON SURVIVED",
      '<a href="first-place.html">First Place</a>' in new, True)
check("it was not linked twice", new.count('href="first-place.html"'), 1)
check("nothing else on the page moved",
      "First Entry, an example page" in new and "2026-08-31 11:00" in new, True)

gone, _ = editing.rewrite(PAGE, 1, "Written in the first year, and nothing else.")
check("changing the linked words drops the link",
      'href="first-place.html"' in gone, False)
check("but the words you typed are all there",
      "Written in the first year, and nothing else." in gone, True)


# --- headings stay headings --------------------------------------------

head, trouble = editing.rewrite(PAGE, 0, "Where it came from")
check("editing a heading reported no trouble", trouble, "")
check("a heading is still a heading",
      "<h2>Where it came from</h2>" in head, True)
check("it did not become a paragraph",
      "<p>Where it came from</p>" in head, False)


# --- markdown works in the box too -------------------------------------

md, _ = editing.rewrite(PAGE, 3, "First Entry, an example **page**")
check("marks work when changing a piece",
      "<strong>page</strong>" in md, True)
kept_bold, _ = editing.rewrite(PAGE, 4, "It was never only that, though.")
check("BOLD MADE EARLIER SURVIVES TOO",
      "<strong>never</strong>" in kept_bold, True)
mult, _ = editing.rewrite(PAGE, 3, "First thing.\n\nSecond thing.")
check("one piece can become two",
      "<p>First thing.</p>" in mult and "<p>Second thing.</p>" in mult, True)


# --- what must be refused ----------------------------------------------

kept, trouble = editing.rewrite(PAGE, 5, "To check: the second question.")
check("a block's own class is kept, not lost", trouble, "")
check("the class is still on it", 'class="todo"' in kept, True)
check("words left alone keep their italics",
      "<em>To check: the second question.</em>" in kept, True)
changed, _ = editing.rewrite(PAGE, 5, "To check: the second question, still.")
check("words that changed lose the italics, same as a link",
      "<em>" in changed, False)
check("but the class survives either way",
      'class="todo"' in changed, True)
odd, trouble = editing.rewrite(PAGE, 6, "Something plain here.")
check("a piece with markup that cannot survive is refused, not guessed",
      trouble != "", True)
check("and that refusal changed nothing", odd, None)
_x, trouble = editing.rewrite(PAGE, 99, "anything")
check("a piece that is not there is refused", trouble != "", True)
_x, trouble = editing.rewrite(PAGE, 3, "   ")
check("emptying a piece is refused", trouble != "", True)
check("a refusal changes nothing at all",
      editing.rewrite(PAGE, 99, "x")[0], None)


# --- typed angle brackets still cannot become tags ---------------------

danger, _ = editing.rewrite(PAGE, 3, "I typed <script>alert(1)</script>")
check("typing a tag does not make one",
      "&lt;script&gt;" in danger and "<script>alert" not in danger, True)




# --- putting something after a chosen piece ---------------------------

after, trouble = editing.insert_after(PAGE, 3, "A line that goes here.")
check("adding after a piece reported no trouble", trouble, "")
check("the new words are on the page",
      "<p>A line that goes here.</p>" in after, True)
check("it landed after the piece that was picked",
      after.index("First Entry, an example page")
      < after.index("A line that goes here."), True)
check("and before the one that followed it",
      after.index("A line that goes here.")
      < after.index("only that."), True)
check("nothing already there was changed",
      "First Entry, an example page" in after
      and '<a href="first-place.html">First Place</a>' in after, True)
marked, _ = editing.insert_after(PAGE, 3, "### A section\n\nUnder it.", top=3)
check("marks work when adding after a piece, and ### means level three",
      "<h3>A section</h3>" in marked and "<p>Under it.</p>" in marked, True)
typed, _ = editing.insert_after(PAGE, 3, "<h3>Typed</h3>\nWords under it.")
check("HTML typed when adding after a piece is real HTML",
      "<h3>Typed</h3>" in typed and "<p>Words under it.</p>" in typed, True)
check("adding after a piece that is not there is refused",
      editing.insert_after(PAGE, 99, "x")[1] != "", True)
check("adding nothing is refused",
      editing.insert_after(PAGE, 3, "   ")[1] != "", True)


print("\n".join("  ok   " + n for n in PASS))
if FAIL:
    print("\n".join("  FAIL " + n for n in FAIL))
print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
