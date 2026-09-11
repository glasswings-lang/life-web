#!/usr/bin/env python3
"""Checks for wiki.py - pages, flags, and finding. Fixtures built here."""

import shutil
import sys
import tempfile
from pathlib import Path

import links
import wiki

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


def slug(text, fallback=""):
    out = "".join(c.lower() if c.isalnum() else "-" for c in text)
    return "-".join(p for p in out.split("-") if p) or fallback


def write(path, text):
    try:
        Path(path).write_text(text, encoding="utf-8", newline="\n")
        return True
    except OSError:
        return False


def read(path):
    return wiki.links._read(path)


def fresh():
    root = Path(tempfile.mkdtemp(prefix="wikicheck-"))
    (root / "style.css").write_text("body { }", encoding="utf-8")
    return root


# --- a new page is prose and nothing else ------------------------------

root = fresh()
rel, trouble = wiki.make_page(root, "Second Place", "places", slug, write)
check("making a page reported no trouble", trouble, "")
check("the page is where it was asked for", rel, "places/second-place.html")
made = (root / rel).read_text(encoding="utf-8")
check("the page has the name as its title",
      "<title>Second Place</title>" in made, True)
check("the page has a spot to add things", "<!-- here -->" in made, True)
check("a new page carries no boxes at all - it is just the page",
      "<form" in made, False)
check("but it has a spot for writing to land in",
      "<!-- here -->" in made, True)
check("and a shape for what lands there",
      "<template>" in made, True)
check("the stylesheet is reached from the right depth",
      'href="../style.css"' in made, True)
check("a new page asks no questions", "_kind" in made, False)
check("a new page arrives with no flags on it", wiki.flags(root), [])
check("naming nothing is refused",
      wiki.make_page(root, "   ", "", slug, write)[1] != "", True)
check("a name with no letters is refused",
      wiki.make_page(root, "!!!", "", slug, write)[1] != "", True)
check("making the same page twice is refused",
      wiki.make_page(root, "Second Place", "places", slug, write)[1] != "",
      True)
check("a folder trying to escape is refused",
      wiki.make_page(root, "Away", "../out", slug, write)[1] != "", True)
shutil.rmtree(root, ignore_errors=True)


# --- flags -------------------------------------------------------------

root = fresh()
rel, _ = wiki.make_page(root, "Second Place", "places", slug, write)
page = root / rel
page.write_text(page.read_text(encoding="utf-8").replace(
    "<!-- here -->",
    "<!-- here -->\n<p>We went up with [[Second Event]] going on below, "
    "and [[a third thing]] after.</p>"), encoding="utf-8", newline="\n")

loose = wiki.flags(root)
check("both flags are found", [w for _p, w, _s in loose],
      ["Second Event", "a third thing"])
check("the flag carries the sentence it was written in",
      loose[0][2],
      "We went up with [[Second Event]] going on below, and "
      "[[a third thing]] after.")

check("a flag inside a comment is not a flag",
      wiki.flags_in("<!-- like [[this]] -->"), [])
check("a flag inside a template is not a flag",
      wiki.flags_in("<template><p>[[this]]</p></template>"), [])
check("a flag inside a tag is not a flag",
      wiki.flags_in('<a href="[[x]]">hi</a>'), [])
check("a flag in plain prose is a flag",
      [w for w, _s, _e in wiki.flags_in("<p>go to [[the second]] now</p>")],
      ["the second"])

other, _ = wiki.make_page(root, "Second Event", "places", slug, write)
trouble = wiki.resolve(root, rel, "Second Event", other, read, write)
check("resolving reported no trouble", trouble, "")
after = page.read_text(encoding="utf-8")
check("the flag became a real link",
      '<a href="second-event.html">Second Event</a>' in after, True)
check("the brackets are gone", "[[Second Event]]" not in after, True)
check("the writer's words are unchanged", ">Second Event</a>" in after, True)
check("the other flag is untouched", "[[a third thing]]" in after, True)
check("only one flag is left now",
      [w for _p, w, _s in wiki.flags(root)], ["a third thing"])
check("resolving a flag that is gone is refused",
      wiki.resolve(root, rel, "Second Event", other, read, write) != "", True)
check("pointing a flag at a page that is not there is refused",
      wiki.resolve(root, rel, "a third thing", "places/nope.html",
                   read, write) != "", True)
shutil.rmtree(root, ignore_errors=True)


# --- a flag whose link has to climb out of a folder --------------------

root = fresh()
deep, _ = wiki.make_page(root, "Deep One", "a/b", slug, write)
top, _ = wiki.make_page(root, "Top One", "", slug, write)
p = root / deep
p.write_text(p.read_text(encoding="utf-8").replace(
    "<!-- here -->", "<!-- here -->\n<p>see [[Top One]]</p>"),
    encoding="utf-8", newline="\n")
wiki.resolve(root, deep, "Top One", top, read, write)
check("a link out of two folders climbs correctly",
      '<a href="../../top-one.html">Top One</a>'
      in (root / deep).read_text(encoding="utf-8"), True)
shutil.rmtree(root, ignore_errors=True)


# --- finding things ----------------------------------------------------

root = fresh()
one, _ = wiki.make_page(root, "First Place", "", slug, write)
two, _ = wiki.make_page(root, "Second Place", "", slug, write)
for rel_, words in ((one, "Held every autumn, and the weather turned."),
                    (two, "A quiet spring, nothing much happened.")):
    p = root / rel_
    p.write_text(p.read_text(encoding="utf-8").replace(
        "<!-- here -->", "<!-- here -->\n<p>" + words + "</p>"),
        encoding="utf-8", newline="\n")

found = wiki.hits(root, "autumn")
check("one page has that word", [r for r, _t, _l in found], [one])
check("the snippet is the prose around it",
      "Held every autumn" in found[0][2][0], True)
check("the page's own nav is not searched", wiki.hits(root, "Back to the top"),
      [])
check("the page's own save box is not searched",
      wiki.hits(root, "What do you want to say"), [])
check("the bracket instruction is not searched",
      wiki.hits(root, "double brackets"), [])
check("a shouted search finds quiet words",
      [r for r, _t, _l in wiki.hits(root, "AUTUMN")], [one])
# The one that matters: the word is capitalised in the PAGE and typed
# in lower case. Searching only for lower-case words on the page misses
# every sentence that starts with the word you are looking for.
check("a quiet search finds a capitalised word",
      [r for r, _t, _l in wiki.hits(root, "held")], [one])
check("nothing found is nothing returned", wiki.hits(root, "zzznope"), [])
check("an empty search lists every page",
      sorted(r for r, _t, _l in wiki.hits(root, "")), sorted([one, two]))
check("the title comes back with the hit", found[0][1], "First Place")
shutil.rmtree(root, ignore_errors=True)


# --- a flag typed into a field must not be counted twice --------------

root = fresh()
rel, _ = wiki.make_page(root, "First Entry", "", slug, write)
p = root / rel
p.write_text(p.read_text(encoding="utf-8").replace(
    "<!-- here -->",
    '<!-- here -->\n<p id="origin">From writing about [[First Place]].</p>\n'
    '<form method="post" action="/save">\n'
    '<textarea id="origin-box" name="value" rows="3">'
    'From writing about [[First Place]].</textarea>\n</form>'),
    encoding="utf-8", newline="\n")

check("a flag in a field is counted once, not once per copy",
      [w for _p, w, _s in wiki.flags(root)], ["First Place"])

other, _ = wiki.make_page(root, "First Place", "", slug, write)
check("resolving it reports no trouble",
      wiki.resolve(root, rel, "First Place", other, read, write), "")
done = p.read_text(encoding="utf-8")
check("the shown copy became a link",
      '<a href="first-place.html">First Place</a>' in done, True)
check("the edit box lost the brackets",
      ">From writing about First Place.</textarea>" in done, True)
check("no markup was pushed into the edit box",
      "<a href" in done.split("<textarea")[1].split("</textarea>")[0], False)
check("nothing is flagged any more", wiki.flags(root), [])
shutil.rmtree(root, ignore_errors=True)



# --- tool links go on when served, never into the file ----------------

PLAIN = ('<!doctype html><html lang="en"><body>\n<h1>A Site</h1>\n'
         '<p>words</p>\n</body></html>')
WITHNAV = ('<html lang="en"><body>\n<h1>A Site</h1>\n<nav>\n'
           '<a href="index.html">Back</a>\n</nav>\n<p>words</p></body></html>')

fitted = wiki.with_tools(PLAIN)
check("a page with no nav gets one", "<nav>" in fitted, True)
check("they go after the title, not before it",
      fitted.index("<h1>A Site</h1>") < fitted.index('href="/search"'), True)
check("in an existing nav, the page's own links are read first",
      wiki.with_tools(WITHNAV).index('href="index.html"')
      < wiki.with_tools(WITHNAV).index('href="/search"'), True)
check("a page that has a nav gets them put inside it",
      wiki.with_tools(WITHNAV).count("<nav>"), 1)
check("both links are added once",
      wiki.with_tools(WITHNAV).count('href="/flags"'), 1)
check("serving twice does not add them twice",
      wiki.with_tools(wiki.with_tools(PLAIN)).count('href="/search"'), 1)
check("a page with neither nav nor h1 still gets them",
      'href="/search"' in wiki.with_tools("<html><body><p>x</p></body></html>"),
      True)
check("nothing at all is left alone", wiki.with_tools(""), "")
check("a new page no longer carries them in the file",
      "/search" in wiki.PAGE, False)


# --- editing a page that already exists -------------------------------

root = fresh()
rel, _ = wiki.make_page(root, "Second Entry", "", slug, write)
page = root / rel
page.write_text(page.read_text(encoding="utf-8").replace(
    "<!-- here -->", "<!-- here -->\n<p>Between one year and the next.</p>"),
    encoding="utf-8", newline="\n")

shown = wiki.edit_page(root, rel)
check("the box holds the file itself, escaped",
      "&lt;p&gt;Between one year and the next.&lt;/p&gt;" in shown, True)
check("a page's own textarea cannot break the box",
      shown.count("</textarea>"), 1)
check("it says which file it is", rel in shown, True)
check("nothing to undo yet, so no undo offered",
      "previous version" in shown.split("Save the page")[1], False)

fixed = page.read_text(encoding="utf-8").replace("Between one year and the next.",
                                                 "Twelve or thirteen.")
check("saving reported no trouble",
      wiki.save_edit(root, rel, fixed, read, write), "")
check("the change is in the file",
      "Twelve or thirteen." in page.read_text(encoding="utf-8"), True)
check("the previous version was kept",
      "Between one year and the next." in (root / (rel + ".bak")).read_text(
          encoding="utf-8"), True)
check("a kept version is not itself a page",
      rel + ".bak" in links.pages(root), False)
check("undo is offered once there is something to undo",
      "previous version" in wiki.edit_page(root, rel), True)

check("undo reported no trouble", wiki.undo_edit(root, rel, read, write), "")
check("the page is back as it was",
      "Between one year and the next." in page.read_text(encoding="utf-8"), True)
check("undoing again swaps it round",
      wiki.undo_edit(root, rel, read, write) == ""
      and "Twelve or thirteen." in page.read_text(encoding="utf-8"), True)

check("emptying a page completely is refused",
      wiki.save_edit(root, rel, "   ", read, write) != "", True)
check("the page survived being refused",
      "Twelve or thirteen." in page.read_text(encoding="utf-8"), True)
check("editing a page that is not there is refused",
      wiki.save_edit(root, "nope.html", "x", read, write) != "", True)
check("undoing with nothing kept is refused",
      wiki.undo_edit(root, "nope.html", read, write) != "", True)
check("what you typed is what the file becomes",
      wiki.save_edit(root, rel, "<html><body><p>mine</p></body></html>",
                     read, write) == ""
      and page.read_text(encoding="utf-8")
      == "<html><body><p>mine</p></body></html>", True)
shutil.rmtree(root, ignore_errors=True)


FIXTURE = """<form method="post" action="/save">
<p id="f-said">Held together by [[Second Event]] underneath.</p>
<label for="f-said-box">Said</label>
<textarea id="f-said-box" name="set-f-said" rows="6">Held together by [[Second Event]] underneath.</textarea>
<button type="submit">Save details</button>
</form>"""

# --- a written answer has somewhere to BE, not only to be typed -------
# Its words used to live only inside the box, where searching does not
# look (forms were dropped whole, or every page matches on the words in
# its own Save button) and flags are not hunted (a box cannot hold a
# link). So a term could be found by its name and never by a word of
# what it said, which in a dictionary is the point going missing.

import kinds

made = kinds.field_block("f-defined-as", "Defined as", "long")
check("a written answer is given somewhere to show",
      '<p id="f-defined-as"></p>' in made, True)
check("...before the label, not after the box",
      made.index('<p id="f-defined-as"') < made.index("<label"), True)
check("...and it still has its box", 'id="f-defined-as-box"' in made, True)
check("a date answer is left alone",
      "<p id=" in kinds.field_block("f-when", "When", "date"), False)

root = fresh()
rel, _ = wiki.make_page(root, "First Place", "", slug, write)
page = root / rel
page.write_text(
    page.read_text(encoding="utf-8").replace("<!-- here -->", FIXTURE),
    encoding="utf-8", newline="")

check("the words of an answer can be searched for",
      [r for r, _t, _l in wiki.hits(root, "held together")], [rel])
check("a Save button is still not searchable",
      wiki.hits(root, "Save details"), [])
check("a label is still not searchable", wiki.hits(root, "Said"), [])
check("a flag in an answer is found, once",
      [w for _p, w, _s in wiki.flags(root)], ["Second Event"])

other, _ = wiki.make_page(root, "Second Event", "", slug, write)
check("and it can be turned into a real link",
      wiki.resolve(root, rel, "Second Event", other, read, write), "")
now = read(root / rel)
check("the link landed in the shown words",
      "<a href=" in now.split("<textarea")[0], True)
check("and the box kept the words without the brackets",
      "[[Second Event]]" not in now.split("<textarea")[1]
      and "Second Event" in now.split("<textarea")[1], True)

shutil.rmtree(root, ignore_errors=True)


# --- the front page says what is waiting ------------------------------
# Repairs, the flagged list and Find were reachable only by typing their
# addresses; nothing on disk linked to any of them. So a flag could sit
# waiting forever and the page you actually look at would never say so.

root = fresh()
MARKER = '<h2>Waiting</h2>' + chr(10) + '<ul id="tidy"></ul>'

quiet = wiki.fill_tidy(MARKER, root)
check("with nothing wrong, Repairs is not mentioned",
      "/repairs" in quiet, False)
check("...nor is the flagged list", "/flags" in quiet, False)
check("...but you can always go and find something",
      "/search" in quiet, True)

# A made page carries a "Back to the top" link, so the fixture needs a
# top for it to land on - otherwise the count is of the nav, not of
# the dead link this is about.
write(root / "index.html", "<h1>Everything</h1>")
one_page, _ = wiki.make_page(root, "First Place", "", slug, write)
page = root / one_page
page.write_text(page.read_text(encoding="utf-8").replace(
    "<!-- here -->",
    '<!-- here --><p>To <a href="nowhere.html">nothing</a>, '
    'about [[Second Event]].</p>'),
    encoding="utf-8", newline="")

busy = wiki.fill_tidy(MARKER, root)
check("a dead link is reported, with a count",
      "1 link goes nowhere" in busy, True)
check("a waiting flag is reported too",
      "1 thing waiting" in busy, True)
check("both are links you can press",
      '<a href="/repairs">' in busy and '<a href="/flags">' in busy, True)

check("a page with no marker is left exactly alone",
      wiki.fill_tidy("<h1>Nothing here</h1>", root), "<h1>Nothing here</h1>")

shutil.rmtree(root, ignore_errors=True)


# --- a dead end offers a way through ----------------------------------
# Not found used to be the end of the road. That is fine for someone who
# writes HTML and will go and make a page; it is a wall for everyone
# else, and an empty folder was the worst of it - the program started,
# said Not found, and there was nothing anywhere to press.

root = fresh()

check("an empty folder can be given a front page",
      wiki.make_page_at(root, "index.html", "", write), "")
front = read(root / "index.html")
check("...which is a working page, not a blank one",
      "Make a new page" in front and 'id="tidy"' in front, True)
check("...and the stylesheet every page asks for is there too",
      (root / "style.css").is_file(), True)

check("a page is made at the address that was asked for",
      wiki.make_page_at(root, "notes/deep/first-thought.html",
                        "First Thought", write), "")
check("...at exactly that address, not one worked out from the name",
      (root / "notes" / "deep" / "first-thought.html").is_file(), True)
made = read(root / "notes" / "deep" / "first-thought.html")
check("...titled from what it was called", "<h1>First Thought</h1>" in made, True)
check("...with somewhere to write on it", "<!-- here -->" in made, True)

check("it will not write over a page that is there",
      wiki.make_page_at(root, "index.html", "", write) != "", True)
check("it will not make one outside the folder",
      wiki.make_page_at(root, "../escape.html", "Escape", write) != "", True)
check("it will not touch the program's own storage",
      wiki.make_page_at(root, "_kind.html", "Shape", write) != "", True)
check("it only makes pages",
      wiki.make_page_at(root, "notes/thing.txt", "Thing", write) != "", True)

check("a made front page reports nothing waiting, because nothing is",
      "/repairs" in wiki.fill_tidy(front, root), False)

shutil.rmtree(root, ignore_errors=True)

print("\n".join("  ok   " + n for n in PASS))
if FAIL:
    print("\n".join("  FAIL " + n for n in FAIL))
print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
