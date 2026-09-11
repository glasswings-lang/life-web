#!/usr/bin/env python3
"""Checks for links.py. Every fixture is built here, from nothing.

A fixture that copies a real page starts failing the moment that page
is used, which is a check reporting on the wrong thing.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import links

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


def page(title, body):
    return ('<!doctype html>\n<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n<title>' + title + '</title>\n'
            '<link rel="stylesheet" href="{css}">\n</head>\n<body>\n'
            + "<h1>" + title + "</h1>\n"
            + body + "\n</body>\n</html>\n")


def build():
    """A folder with two sections and a page in each, linked both ways."""
    root = Path(tempfile.mkdtemp(prefix="linkcheck-"))
    (root / "one").mkdir()
    (root / "two").mkdir()
    (root / "style.css").write_text("body { }", encoding="utf-8")

    (root / "index.html").write_text(
        page("Top", '<p>Start at <a href="one/first.html">First</a>.</p>')
        .replace("{css}", "style.css"), encoding="utf-8")

    (root / "one" / "first.html").write_text(
        page("First",
             '<p>It began at <a href="../two/second.html">Second Place</a>'
             ' during the fair.</p>\n'
             '<form method="post" action="/save">\n'
             '<input type="hidden" name="_to" value="one/first.html">\n'
             "</form>\n<!-- here -->")
        .replace("{css}", "../style.css"), encoding="utf-8")

    (root / "two" / "second.html").write_text(
        page("Second Place",
             '<p>Which is near <a href="../one/first.html">First</a>.</p>\n'
             '<input type="hidden" name="_to" value="two/second.html">')
        .replace("{css}", "../style.css"), encoding="utf-8")
    return root


def read(path):
    return links._read(path)


def write(path, text):
    try:
        Path(path).write_text(text, encoding="utf-8", newline="\n")
        return True
    except OSError:
        return False


def text_of(root, rel):
    return (root / rel).read_text(encoding="utf-8")


# --- what a link points at -------------------------------------------

check("a link up and over resolves",
      links.target_of("one/first.html", "../two/second.html"),
      "two/second.html")
check("a link in the same folder resolves",
      links.target_of("one/first.html", "other.html"), "one/other.html")
check("a website is not ours", links.target_of("index.html",
                                               "https://example.org/x"), None)
check("an anchor is not ours", links.target_of("index.html", "#top"), None)
check("a program address is not ours",
      links.target_of("one/first.html", "/save"), None)
check("a link out of the folder is refused",
      links.target_of("index.html", "../../elsewhere.html"), None)
check("an anchor on a real page still resolves",
      links.target_of("one/first.html", "../two/second.html#notes"),
      "two/second.html")

check("address from the top down", links.address_from("index.html",
                                                      "one/first.html"),
      "one/first.html")
check("address up and over", links.address_from("one/first.html",
                                                "two/second.html"),
      "../two/second.html")
check("address from a page to the top",
      links.address_from("one/first.html", "index.html"), "../index.html")


# --- moving a page ----------------------------------------------------

root = build()
trouble = links.move(root, "one/first.html", "two/first.html", read, write)
check("the move reported no trouble", trouble, "")
check("the old file is gone", (root / "one" / "first.html").exists(), False)
check("the new file is there", (root / "two" / "first.html").exists(), True)

moved = text_of(root, "two/first.html")
check("a link that stayed put is re-addressed",
      'href="second.html"' in moved, True)
check("the old address is gone from the moved page",
      "../two/second.html" in moved, False)
check("the stylesheet still resolves from the new depth",
      'href="../style.css"' in moved, True)
check("the hidden _to follows the file",
      'name="_to" value="two/first.html"' in moved, True)

top = text_of(root, "index.html")
check("a link from the top follows the move",
      'href="two/first.html"' in top, True)
second = text_of(root, "two/second.html")
check("a link from a sibling follows the move",
      'href="first.html"' in second, True)
check("the sibling's old address is gone",
      "../one/first.html" in second, False)
check("nothing is left pointing at nothing", links.loose_ends(root), [])
shutil.rmtree(root, ignore_errors=True)


# --- moving is refused when it should be ------------------------------

root = build()
check("moving onto something that exists is refused",
      links.move(root, "one/first.html", "two/second.html", read, write)
      != "", True)
check("the page that was in the way is untouched",
      "Which is near" in text_of(root, "two/second.html"), True)
check("moving a page that is not there is refused",
      links.move(root, "one/nope.html", "two/nope.html", read, write) != "",
      True)
check("moving somewhere new makes the folder",
      links.move(root, "one/first.html", "three/first.html", read, write), "")
check("the new folder is there", (root / "three" / "first.html").is_file(),
      True)
shutil.rmtree(root, ignore_errors=True)


# --- loose ends -------------------------------------------------------

root = build()
shutil.move(str(root / "two" / "second.html"), str(root / "second.html"))
ends = links.loose_ends(root)
check("a file moved behind the program's back leaves one loose end",
      len(ends), 1)
if ends:
    page_rel, addr, words, sentence = ends[0]
    check("the loose end names the page it is in", page_rel, "one/first.html")
    check("the loose end keeps the words", words, "Second Place")
    check("the loose end carries the sentence it came from",
          sentence, "It began at Second Place during the fair.")

    trouble = links.repoint(root, page_rel, addr, "second.html", read, write)
    check("repointing reported no trouble", trouble, "")
    fixed = text_of(root, "one/first.html")
    check("the link now points at the real page",
          'href="../second.html"' in fixed, True)
    check("the words are still the writer's",
          ">Second Place</a>" in fixed, True)
    check("nothing is loose any more", links.loose_ends(root), [])
shutil.rmtree(root, ignore_errors=True)


# --- a form told to save into a file that is not there ----------------

root = build()
(root / "one" / "first.html").unlink()
check("an orphan form is noticed",
      [p for p, _ in links.orphan_forms(root)], [])
root2 = build()
shutil.move(str(root2 / "one" / "first.html"), str(root2 / "first.html"))
check("a moved page's own form is noticed as orphaned",
      ("first.html", "one/first.html") in links.orphan_forms(root2), True)
shutil.rmtree(root, ignore_errors=True)
shutil.rmtree(root2, ignore_errors=True)


# --- the templates rule -----------------------------------------------

root = build()
(root / "one" / "_kind.html").write_text(
    page("{name}", "<p>shape</p>").replace("{css}", "../style.css"),
    encoding="utf-8")
check("a kind's shape is not listed as a page",
      "one/_kind.html" in links.pages(root), False)
check("a kind's shape is visited when rewriting",
      "one/_kind.html" in links.pages(root, templates=True), True)
check("moving a kind's shape is refused",
      links.move(root, "one/_kind.html", "two/_kind.html", read, write) != "",
      True)
shutil.rmtree(root, ignore_errors=True)




# --- what points at a page, across the whole folder --------------------

root = build()
(root / "two" / "second.html").write_text(
    page("Second Place",
         '<p>Which is near <a href="../one/first.html">First</a>, and '
         'again <a href="../one/first.html">the first one</a>.</p>')
    .replace("{css}", "../style.css"), encoding="utf-8", newline="\n")

back = links.points_at(root, "one/first.html")
check("every link pointing at it is found, from every page", len(back), 3)
check("it says which pages they are on",
      sorted({p for p, _t, _w, _s in back}),
      ["index.html", "two/second.html"])
check("it uses each page's title, not its filename",
      sorted({t for _p, t, _w, _s in back}), ["Second Place", "Top"])
check("the writer's words come with it",
      sorted(w for _p, _t, w, _s in back),
      ["First", "First", "the first one"])
check("a page does not count as pointing at itself",
      links.points_at(root, "index.html"), [])
check("a page with one thing pointing at it says so",
      [w for _p, _t, w, _s in links.points_at(root, "two/second.html")],
      ["Second Place"])
check("a page nothing points at comes back empty",
      links.points_at(root, "style.css"), [])
selfy = root / "one" / "first.html"
selfy.write_text(selfy.read_text(encoding="utf-8").replace(
    "<!-- here -->", '<p>see <a href="first.html">itself</a></p>'),
    encoding="utf-8", newline="\n")
check("a page linking to itself is not counted as pointing at it",
      [w for _p, _t, w, _s in links.points_at(root, "one/first.html")
       if w == "itself"], [])
check("a kind is not needed for any of this",
      any((root / d / "_kind.html").exists() for d in ("one", "two")), False)


# --- the links a page has, and changing one that is not broken ---------

on = links.links_on(root, "two/second.html")
check("every link on the page is listed", len(on), 2)
check("where each one lands is worked out",
      sorted({t for _a, _w, t, _s in on}), ["one/first.html"])

trouble = links.repoint_any(root, "two/second.html", "../one/first.html",
                            "the first one", "index.html", read, write)
check("repointing a working link reported no trouble", trouble, "")
now = text_of(root, "two/second.html")
check("that one now points somewhere else",
      '<a href="../index.html">the first one</a>' in now, True)
check("the OTHER link on the same words is untouched",
      '<a href="../one/first.html">First</a>' in now, True)
check("nothing was left pointing at nothing", links.loose_ends(root), [])

check("taking a link off keeps the words",
      links.unlink(root, "two/second.html", "../index.html",
                   "the first one", read, write) == ""
      and "the first one" in text_of(root, "two/second.html")
      and 'href="../index.html"' not in text_of(root, "two/second.html"),
      True)
check("repointing something that is gone is refused",
      links.repoint_any(root, "two/second.html", "../index.html",
                        "the first one", "index.html", read, write) != "",
      True)
shutil.rmtree(root, ignore_errors=True)


# --- renaming makes the page say its new name --------------------------

root = build()
check("renaming reported no trouble",
      links.move(root, "one/first.html", "one/the-first-place.html",
                 read, write, called="The First Place"), "")
renamed = text_of(root, "one/the-first-place.html")
check("the title says the new name",
      "<title>The First Place</title>" in renamed, True)
check("the heading says the new name too",
      "<h1>The First Place</h1>" in renamed, True)
check("the old name is gone from both", ">First<" in renamed, False)
check("links to it still work", links.loose_ends(root), [])
check("moving without renaming leaves the name alone",
      "<title>Second Place</title>" in text_of(root, "two/second.html"), True)
shutil.rmtree(root, ignore_errors=True)


# --- putting a page away, and getting it back --------------------------

root = build()
check("removing reported no trouble",
      links.remove(root, "two/second.html", read, write), "")
check("the page is gone from where it was",
      (root / "two" / "second.html").exists(), False)
check("but it is kept, not destroyed",
      (root / "_deleted" / "two" / "second.html").is_file(), True)
check("what it said is all still there",
      "Which is near" in (root / "_deleted" / "two"
                          / "second.html").read_text(encoding="utf-8"), True)
check("what was put away is not a page any more",
      any(p.startswith("_deleted") for p in links.pages(root)), False)
check("and the links that pointed at it now show as loose",
      [w for _p, _a, w, _s in links.loose_ends(root)], ["Second Place"])
check("removing a page that is not there is refused",
      links.remove(root, "nope.html", read, write) != "", True)
shutil.rmtree(root, ignore_errors=True)

# ---- Repairs offers a way out for a page that is gone ON PURPOSE ----
# "Point it at" has no right answer when the page it named was deleted
# deliberately. Before this, a loose end like that could only be fixed
# by opening the file in a text editor, which is the thing this program
# exists so nobody has to do.
root2 = Path(tempfile.mkdtemp()) / "web2"
root2.mkdir(parents=True)
write(root2 / "index.html",
      '<h1>Everything</h1><ul><li><a href="gone/index.html">'
      'First List</a> - 12 entries.</li></ul>')

ends = links.loose_ends(root2)
check("a link to a page that is not there is a loose end", len(ends), 1)

shown = links.repairs_page(root2)
check("Repairs offers to take the link off",
      "Take the link off and keep the words" in shown, True)
check("...and carries the words that button needs",
      'name="words"' in shown, True)

took = links.unlink(root2, ends[0][0], ends[0][1], ends[0][2], read, write)
left = text_of(root2, "index.html")
check("taking it off reports no trouble", took, "")
check("the loose end is gone", links.loose_ends(root2), [])
check("the words are still there", "First List" in left, True)
check("the sentence around them survived", "12 entries" in left, True)
check("and nothing links anywhere now", "<a href" not in left, True)

shutil.rmtree(root2.parent, ignore_errors=True)



print("\n".join("  ok   " + n for n in PASS))
if FAIL:
    print("\n".join("  FAIL " + n for n in FAIL))
print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
