#!/usr/bin/env python3
"""Checks for notes.py - moving notes and putting them in date order.

The last part starts the real program on a throwaway folder and presses
the buttons through it, so the pages and the saving are checked as well
as the pieces underneath.
"""

import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path

import notes
import wiki

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>First Page</title>
</head>
<body>

<h1>First Page</h1>

<nav>
<a href="index.html">Back to the top</a>
</nav>

<p>Words written straight onto the page.</p>

<!-- here -->
<div class="addition">
<p class="when">2026-09-03 10:00</p>
<p>Third note words.</p>
</div>
<div class="addition">
<p class="when">2026-09-01 09:00</p>
<h2>A heading in the first note</h2>
<p>First note words.</p>
<div class="aside"><p>Inside a div of its own.</p></div>
</div>

<p>A line between notes that belongs to nobody.</p>

<div class="addition">
<p class="when">2026-09-02 12:30</p>
<p>Second note words.</p>
</div>

<!-- <div class="addition"><p class="when">2020-01-01 00:00</p></div> -->

<template>
<div class="addition">
<p class="when">{when}</p>
<p>{note}</p>
</div>
</template>

</body>
</html>
"""


def whens(text):
    return [f["when"] for f in notes.find(text)]


def outside_notes(text):
    """The page with every note taken out - what must never change."""
    out, at = [], 0
    for f in notes.find(text):
        out.append(text[at:f["start"]])
        at = f["end"]
    out.append(text[at:])
    return "".join(out).split()


# --- finding notes -----------------------------------------------------

found = notes.find(PAGE)
check("three notes are found", len(found), 3)
check("they are found in page order, by their dates", whens(PAGE),
      ["2026-09-03 10:00", "2026-09-01 09:00", "2026-09-02 12:30"])
check("a note in a comment is not a note",
      "2020-01-01 00:00" in whens(PAGE), False)
check("the template is not a note", "{when}" in whens(PAGE), False)
check("a div inside a note does not end the note early",
      found[1]["words"].endswith("Inside a div of its own."), True)
check("the date is not counted among the words",
      "2026" in found[0]["words"], False)
check("a note is known by its date and first words",
      notes.label(found[1], most=4),
      "2026-09-01 09:00, A heading in the")
check("a note that is never closed is left out, not guessed at",
      len(notes.find('<div class="addition"><p class="when">x</p><p>y</p>')),
      0)
check("a note with another class beside addition is still a note",
      len(notes.find('<div class="addition kept"><p>y</p></div>')), 1)


# --- where each note can go --------------------------------------------

check("the first note is not offered the top",
      [v for v, _w in notes.choices(found, 0)], ["bottom", "after:1",
                                                  "after:2", "away"])
check("the last note is not offered the bottom",
      [v for v, _w in notes.choices(found, 2)], ["top", "after:0", "away"])
check("no note is offered to go after itself or where it already is",
      [v for v, _w in notes.choices(found, 1)],
      ["top", "bottom", "after:2", "away"])
check("every note can be put away, last in its list",
      [notes.choices(found, k)[-1] for k in range(3)],
      [("away", "Put it away")] * 3)


# --- moving -------------------------------------------------------------

new, trouble = notes.move(PAGE, 2, "top")
check("moving to the top reported no trouble", trouble, "")
check("the moved note is at the top", whens(new),
      ["2026-09-02 12:30", "2026-09-03 10:00", "2026-09-01 09:00"])
check("everything that is not a note is exactly as it was",
      outside_notes(new), outside_notes(PAGE))
check("the note arrived whole, heading, words and inner div included",
      sorted(PAGE[f["start"]:f["end"]] for f in notes.find(PAGE)),
      sorted(new[f["start"]:f["end"]] for f in notes.find(new)))
check("the top is still after the marker",
      new.index("<!-- here -->") < new.index("2026-09-02 12:30"), True)
check("no gap was left behind or doubled",
      "\n\n\n" in new, False)

new, trouble = notes.move(PAGE, 0, "bottom")
check("moving to the bottom reported no trouble", trouble, "")
check("the moved note is at the bottom", whens(new),
      ["2026-09-01 09:00", "2026-09-02 12:30", "2026-09-03 10:00"])
check("the bottom is still before the template",
      new.index("2026-09-03 10:00") < new.index("<template>"), True)

new, trouble = notes.move(PAGE, 0, "after:1")
check("moving after a named note reported no trouble", trouble, "")
check("it went straight after that note", whens(new),
      ["2026-09-01 09:00", "2026-09-03 10:00", "2026-09-02 12:30"])
check("so it sits before the line between notes, like the one it follows",
      new.index("2026-09-03 10:00")
      < new.index("A line between notes"), True)

new, trouble = notes.move(PAGE, 2, "after:0")
check("moving up past a named note works too", whens(new),
      ["2026-09-03 10:00", "2026-09-02 12:30", "2026-09-01 09:00"])

check("moving to where it already is changes nothing",
      notes.move(PAGE, 0, "top"), (PAGE, ""))
check("choosing nowhere is refused and changes nothing",
      notes.move(PAGE, 0, "")[0], None)
check("and says so", notes.move(PAGE, 0, "")[1] != "", True)
check("a note that is not there is refused",
      notes.move(PAGE, 9, "top")[0], None)
check("going after a note that is not there is refused",
      notes.move(PAGE, 0, "after:9")[0], None)
check("going after itself is refused",
      notes.move(PAGE, 1, "after:1")[0], None)
check("something odd typed as the place is refused",
      notes.move(PAGE, 1, "after:1; x")[0], None)

SIDE = ("<!-- here -->\n"
        '<div class="addition"><p class="when">2026-01-01 01:00</p></div>\n'
        '<div class="addition"><p class="when">2026-01-02 01:00</p></div>\n'
        '<div class="addition"><p class="when">2026-01-03 01:00</p></div>\n'
        "\n<template></template>\n")
there, _ = notes.move(SIDE, 0, "bottom")
back, _ = notes.move(there, 2, "top")
check("down and back up again gives back the very same file", back, SIDE)


# --- date order ---------------------------------------------------------

newest, undated = notes.sort(PAGE, newest_first=True)
check("newest first puts the dates in order", whens(newest),
      ["2026-09-03 10:00", "2026-09-02 12:30", "2026-09-01 09:00"])
check("every date could be read", undated, 0)
check("sorting leaves everything that is not a note where it was",
      outside_notes(newest), outside_notes(PAGE))
check("the line between notes is still in the same gap",
      newest.index("2026-09-02 12:30") < newest.index("A line between notes")
      < newest.index("2026-09-01 09:00"), True)
oldest, _ = notes.sort(PAGE, newest_first=False)
check("oldest first puts the dates the other way", whens(oldest),
      ["2026-09-01 09:00", "2026-09-02 12:30", "2026-09-03 10:00"])
check("sorting twice changes nothing the second time",
      notes.sort(newest, True)[0], newest)
check("oldest then newest gets back to the same file",
      notes.sort(oldest, True)[0], newest)

SAME = ('<div class="addition"><p class="when">2026-05-05 05:05</p>'
        "<p>Earlier on the page.</p></div>\n"
        '<div class="addition"><p class="when">someday</p>'
        "<p>No real date.</p></div>\n"
        '<div class="addition"><p class="when">2026-05-05 05:05</p>'
        "<p>Later on the page.</p></div>\n"
        '<div class="addition"><p class="when">2026-01-01</p>'
        "<p>Just a day.</p></div>\n")
for first in (True, False):
    got, undated = notes.sort(SAME, first)
    words = [f["words"] for f in notes.find(got)]
    way = "newest" if first else "oldest"
    check("notes from the same minute keep their order, " + way + " first",
          words.index("Earlier on the page.") < words.index(
              "Later on the page."), True)
    check("a note with no readable date goes to the end, " + way + " first",
          words[-1], "No real date.")
    check("and it is counted, " + way + " first", undated, 1)
check("a date with no time is still a date",
      notes.find(notes.sort(SAME, False)[0])[0]["words"], "Just a day.")

check("a page with one note sorts to itself",
      notes.sort(SIDE.split("\n", 2)[0] + SIDE.split("\n", 2)[1], True)[1], 0)
check("the fingerprint changes when the page does",
      notes.fingerprint(PAGE) != notes.fingerprint(newest), True)


# --- the page of controls, read the way NVDA would move through it -----

class Reading(HTMLParser):
    def __init__(self):
        super().__init__()
        self.order, self.ids, self.fors, self.selects = [], [], [], []
        self.autofocus = self.script = False
        self._in = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "autofocus" in a:
            self.autofocus = True
        if tag == "script":
            self.script = True
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "label":
            self.fors.append(a.get("for"))
        if tag == "select":
            self.selects.append(a.get("id"))
        if tag in ("h1", "h2", "legend", "label", "button", "a"):
            self._in = [tag, ""]

    def handle_data(self, data):
        if self._in:
            self._in[1] += data

    def handle_endtag(self, tag):
        if self._in and tag == self._in[0]:
            self.order.append((tag, " ".join(self._in[1].split())))
            self._in = None


root = Path(tempfile.mkdtemp(prefix="notescheck-"))
(root / "style.css").write_text("body { }", encoding="utf-8")
(root / "first-page.html").write_text(PAGE, encoding="utf-8", newline="\n")

r = Reading()
r.feed(wiki.notes_page(root, "first-page.html"))
check("every box on the controls page has a label pointing at it",
      sorted(r.selects), sorted(f for f in r.fors if f in r.selects))
check("there is one box per note", len(r.selects), 3)
check("no id is used twice", len(r.ids), len(set(r.ids)))
check("nothing on it grabs focus", r.autofocus, False)
check("there is no script on it", r.script, False)
check("it opens by saying what page it is",
      r.order[0], ("h1", "Moving notes on first-page.html"))
check("date order comes before the notes",
      [t for t in r.order if t[0] in ("legend", "h2")][:2],
      [("legend", "Put every note in date order"),
       ("legend", "2026-09-03 10:00, Third note words.")])
check("each note's box is in a group named after the note",
      [t for t in r.order if t[0] == "legend"][1:],
      [("legend", "2026-09-03 10:00, Third note words."),
       ("legend", "2026-09-01 09:00, A heading in the first note First note "
        "words. Inside"),
       ("legend", "2026-09-02 12:30, Second note words.")])
check("every Move button has a sentence before it saying what pressing does",
      wiki.notes_page(root, "first-page.html").count(
          "<p>Pressing this moves the note where you chose."), 3)
check("and so do the date order buttons",
      "<p>Pressing one of these puts every note in date order" in
      wiki.notes_page(root, "first-page.html"), True)

print("\n  The controls page, in reading order:")
for tag, words in r.order:
    print("    " + tag.ljust(7) + words)
print()

one = PAGE.split("<div class=\"addition\">\n<p class=\"when\">2026-09-01")[0]
one += "</body></html>"
(root / "one.html").write_text(one, encoding="utf-8")
check("a page with one note says there is nothing to move",
      "only one note" in wiki.notes_page(root, "one.html"), True)
check("and offers no boxes", "<select" in wiki.notes_page(root, "one.html"),
      False)
check("the tool link is offered where there are notes to move",
      "/notes?page=first-page.html" in wiki.with_tools(PAGE,
                                                       "first-page.html"),
      True)
check("and not where there is only one",
      "/notes?page" in wiki.with_tools(one, "one.html"), False)


# --- through the real program ------------------------------------------

import forms  # noqa: E402  (after the pieces above, so they fail on their own)

forms.HERE = root
server = ThreadingHTTPServer(("127.0.0.1", 0), forms.Handler)
base = "http://127.0.0.1:%d" % server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()


def get(path):
    try:
        with urllib.request.urlopen(base + path) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, ""


def post(path, fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    with urllib.request.urlopen(base + path, data) as resp:
        return resp.geturl(), resp.read().decode("utf-8")


def on_disk():
    return (root / "first-page.html").read_text(encoding="utf-8")


def seen():
    return notes.fingerprint(on_disk())


status, served = get("/first-page.html")
check("the page itself is served with the link to move notes",
      '<a href="/notes?page=first-page.html">Move or sort notes</a>' in served,
      True)
check("the link is not written into the file",
      "/notes?page" in on_disk(), False)
check("the controls page is served", get("/notes?page=first-page.html")[0],
      200)
check("asking for notes on a page that is not there is Not found",
      get("/notes?page=nothing.html")[0], 404)
check("asking for a page outside the folder is Not found",
      get("/notes?page=../outside.html")[0], 404)

before = on_disk()
url, body = post("/movenote", {"page": "first-page.html", "seen": seen(),
                               "n": "2", "to": "top"})
check("pressing Move lands back on the controls page",
      "/notes?page=first-page.html" in url, True)
check("and says what happened",
      "The note from 2026-09-02 12:30 is at the top now." in body, True)
check("the file on disk has the note at the top", whens(on_disk()),
      ["2026-09-02 12:30", "2026-09-03 10:00", "2026-09-01 09:00"])
check("the page as it was is kept beside it",
      (root / "first-page.html.bak").read_text(encoding="utf-8"), before)

stale = notes.fingerprint(before)
moved = on_disk()
url, body = post("/movenote", {"page": "first-page.html", "seen": stale,
                               "n": "0", "to": "bottom"})
check("a list made before the page changed moves nothing", on_disk(), moved)
check("and says why", "has changed since this list was made" in body, True)

url, body = post("/movenote", {"page": "first-page.html", "seen": seen(),
                               "n": "0", "to": ""})
check("pressing Move with nowhere chosen does not crash, and says so",
      "Nowhere was chosen" in body, True)
check("and moves nothing", on_disk(), moved)

url, body = post("/movenote", {"page": "first-page.html", "seen": seen(),
                               "n": "0", "to": "top"})
check("moving a note to where it is says nothing changed",
      "already there" in body, True)

url, body = post("/sortnotes", {"page": "first-page.html", "seen": seen(),
                                "order": "oldest"})
check("Oldest first puts the file in order", whens(on_disk()),
      ["2026-09-01 09:00", "2026-09-02 12:30", "2026-09-03 10:00"])
check("and says so", "Every note is in date order now, oldest first." in body,
      True)

url, body = post("/notesundo", {"page": "first-page.html"})
check("Go back puts the page as it was before the sort", on_disk(), moved)
check("and says so", "Put back." in body, True)

url, body = post("/sortnotes", {"page": "first-page.html", "seen": seen(),
                                "order": "newest"})
check("Newest first puts the file in order", whens(on_disk()),
      ["2026-09-03 10:00", "2026-09-02 12:30", "2026-09-01 09:00"])
url, body = post("/sortnotes", {"page": "first-page.html", "seen": seen(),
                                "order": "newest"})
check("sorting an already sorted page says nothing changed",
      "already in date order" in body, True)
url, body = post("/movenote", {"page": "first-page.html", "seen": seen(),
                               "n": "0", "to": "away"})
check("Put it away on a note keeps it in a file of its own",
      len(list((root / "_deleted" / "pieces").glob("first-page-*.html"))), 1)
check("and takes it off the page, date and all", len(notes.find(on_disk())),
      2)
check("and lands back on the notes page", "/notes?page=first-page.html" in url,
      True)
url, body = post("/movenote", {"page": "first-page.html", "seen": seen(),
                               "n": "0", "to": "away", "from": "edit"})
check("sent from the Edit page, it lands back on the Edit page",
      "/edit?page=first-page.html" in url, True)
check("nothing was logged as going wrong",
      (root / forms.LOG_NAME).exists(), False)

server.shutdown()
server.server_close()
shutil.rmtree(root, ignore_errors=True)


print("\n".join("  ok   " + n for n in PASS))
if FAIL:
    print("\n".join("  FAIL " + n for n in FAIL))
print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
