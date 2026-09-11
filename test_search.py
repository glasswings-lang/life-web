#!/usr/bin/env python3
"""Checks for finding words anywhere on a page. The last part goes
through the real program on a throwaway folder."""

import shutil
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path

import wiki

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


def page(title, body):
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<title>" + title
            + "</title>\n</head>\n<body>\n<h1>" + title + "</h1>\n"
            '<nav>\n<a href="index.html">Back to the top</a>\n</nav>\n'
            + body + "\n</body>\n</html>\n")


root = Path(tempfile.mkdtemp(prefix="searchcheck-"))
(root / "one.html").write_text(page(
    "First Place", "<p>The note came first, before the singing.</p>\n"
    "<p>Later it was singing again.</p>"), encoding="utf-8")
(root / "two.html").write_text(page(
    "Second Place", "<p>First note of the day.</p>"), encoding="utf-8")
(root / "three.html").write_text(page(
    "Third Place", "<p>Nothing to see here.</p>"), encoding="utf-8")
# One word six times, each far enough from the last that every one would
# get a line of its own if nothing stopped it.
(root / "four.html").write_text(page(
    "Fourth Place", "<p>" + " ".join("marker " + "word " * 60
                                     for _ in range(6)) + "</p>"),
    encoding="utf-8")


(root / "places").mkdir()
(root / "places" / "fifth.html").write_text(page(
    "Fifth Place", "<p>A bell on the door.</p>\n"
    '<div class="addition">\n<p class="when">2026-08-30 10:00</p>\n'
    "<p>The bell rang early.</p>\n</div>\n"
    '<div class="addition">\n<p class="when">2026-09-05 10:00</p>\n'
    "<p>The lamp was lit.</p>\n</div>\n"
    '<div class="addition">\n<p class="when">someday</p>\n'
    "<p>A lamp with no date.</p>\n</div>"), encoding="utf-8")
(root / "places" / "inner").mkdir()
(root / "places" / "inner" / "sixth.html").write_text(page(
    "Sixth Place", "<p>A bell in the inner room.</p>"), encoding="utf-8")
(root / "first-kind").mkdir()
(root / "first-kind" / "_kind.html").write_text(
    page("First Kind shape", "<p>A lamp in the shape.</p>"), encoding="utf-8")
(root / "first-kind" / "index.html").write_text(
    page("First Kind", "<p>Every lamp listed here.</p>"), encoding="utf-8")
(root / "first-kind" / "entry.html").write_text(
    page("First Entry", "<p>A lamp in the hall.</p>"), encoding="utf-8")


def found(query, together=False, **narrow):
    return sorted(p for p, _t, _l in wiki.hits(root, query,
                                               together=together, **narrow))


# --- which pages are found ------------------------------------------------------

check("words apart on a page are found, not only side by side",
      found("first note"), ["one.html", "two.html"])
check("in any order", found("note first"), ["one.html", "two.html"])
check("ticked together, only the pages with the words side by side, in order",
      found("first note", together=True), ["two.html"])
check("ticked together, the other order finds nothing",
      found("note first", together=True), [])
check("every word has to be there somewhere",
      found("first zebra"), [])
check("a word counts inside a longer one", found("sing"), ["one.html"])
check("and so sing finds singing, with another word",
      found("sing again"), ["one.html"])
check("extra spaces make no difference",
      found("   first    note  "), found("first note"))
check("capitals make no difference", found("FIRST Note"), found("first note"))
check("the page's own links around it are still not searched",
      found("top"), [])
check("nothing typed lists every page",
      found(""), ["first-kind/entry.html", "first-kind/index.html",
                  "four.html", "one.html", "places/fifth.html",
                  "places/inner/sixth.html", "three.html", "two.html"])


# --- narrowing it down -------------------------------------------------------------

from datetime import date  # noqa: E402

check("narrowed to a folder, its pages and the folders inside it",
      found("bell", folder="places"),
      ["places/fifth.html", "places/inner/sixth.html"])
check("narrowed to the inner folder, only that one",
      found("bell", folder="places/inner"), ["places/inner/sixth.html"])
check("a folder name is not matched as the start of another name",
      found("", folder="first"), [])
check("narrowed to the top folder, nothing in a folder",
      found("lamp", folder=""), [])
check("and the top folder's own pages are still found",
      found("first note", folder=""), ["one.html", "two.html"])
check("narrowed to a kind, only that kind's pages",
      found("lamp", kind="first-kind"), ["first-kind/entry.html"])
check("and not the kind's own list of its pages",
      found("", kind="first-kind"), ["first-kind/entry.html"])
SEPT = dict(start=date(2026, 9, 1), end=date(2026, 9, 30))
check("with dates, only notes from those dates are searched",
      found("lamp", **SEPT), ["places/fifth.html"])
check("so words on the page outside those notes do not count",
      found("bell", **SEPT), [])
check("a note with no readable date is left out once dates are given",
      found("no date", **SEPT), [])
check("pages with no notes at all are left out once dates are given",
      "first-kind/entry.html" in found("lamp", **SEPT), False)
check("only a first date is enough",
      found("lamp", start=date(2026, 9, 1)), ["places/fifth.html"])
check("only a last date is enough",
      found("bell", end=date(2026, 8, 31)), ["places/fifth.html"])
check("the first and last days themselves count",
      found("", start=date(2026, 9, 5), end=date(2026, 9, 5)),
      ["places/fifth.html"])
lines = dict((p, l) for p, _t, l in wiki.hits(root, "", **SEPT))
check("with dates and no words, the notes from those dates are shown",
      lines, {"places/fifth.html": ["2026-09-05 10:00 The lamp was lit."]})
check("a folder, a kind and dates together must all hold",
      found("lamp", folder="places", kind="first-kind", **SEPT), [])
check("narrowed to one page, only that page",
      found("bell", page="places/fifth.html"), ["places/fifth.html"])
check("a page without the words finds nothing, even if others have them",
      found("bell", page="one.html"), [])
check("a page and dates together must both hold",
      found("lamp", page="places/fifth.html", **SEPT), ["places/fifth.html"])
check("with one page and no words, that page is listed",
      found("", page="two.html"), ["two.html"])


# --- the lines shown with each page ---------------------------------------------

lines = dict((p, l) for p, _t, l in wiki.hits(root, "sing"))["one.html"]
check("a stretch of the page is shown once, not once per word in it",
      len(lines), len(set(lines)))
check("and never more than three lines, even with six places to show",
      len(dict((p, l) for p, _t, l in wiki.hits(root, "marker"))["four.html"]),
      3)
lines = dict((p, l) for p, _t, l in wiki.hits(root, "note day"))["two.html"]
check("the line shown holds the words", "First note of the day." in lines[0],
      True)


# --- the Find something page, read the way NVDA would move through it ----------

class Reading(HTMLParser):
    def __init__(self):
        super().__init__()
        self.labels, self.fors, self.inputs, self.checked = [], [], [], None
        self._label = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "input":
            self.inputs.append(a.get("id"))
            if a.get("type") == "checkbox":
                self.checked = "checked" in a
        if tag == "label":
            self.fors.append(a.get("for"))
            self._label = ""

    def handle_data(self, data):
        if self._label is not None:
            self._label += data

    def handle_endtag(self, tag):
        if tag == "label" and self._label is not None:
            self.labels.append(" ".join(self._label.split()))
            self._label = None


r = Reading()
r.feed(wiki.search_page(root, "first note"))
check("every box on the page has a label pointing at it",
      [i for i in r.inputs if i not in r.fors], [])
check("the search comes first: the words, then the tick box",
      r.inputs[:2], ["q", "together"])
check("the tick box says what it does",
      r.labels[:2], ["Words to look for",
                     "Only where these words sit together, in this order"])
check("it starts unticked", r.checked, False)
shown = wiki.search_page(root, "first note")
check("and the page says how it looked",
      "2 pages have those words somewhere on the page, in any order." in shown,
      True)
r = Reading()
r.feed(wiki.search_page(root, "first note", together=True))
check("ticked, it stays ticked on the results", r.checked, True)
check("and the page says so",
      "1 page has those words together, in that order." in wiki.search_page(
          root, "first note", together=True), True)
check("finding nothing says how it looked",
      "Nothing has those words somewhere on the page, in any order."
      in wiki.search_page(root, "first zebra"), True)

narrowed = wiki.search_page(root, "lamp", folder="places", start="2026-09-01",
                            end="2026-09-30")
check("narrowed, the page says everything it looked through",
      "1 page has those words somewhere on the page, in any order, in notes "
      "from 2026-09-01 to 2026-09-30, in the folder places." in narrowed, True)
check("the narrowing is in a group, so NVDA says what the boxes are for",
      "<fieldset>\n<legend>Narrow it down</legend>" in narrowed, True)
check("what was chosen stays chosen on the results",
      ['<option value="places" selected>' in narrowed,
       'id="from" name="from" value="2026-09-01"' in narrowed,
       'id="to" name="to" value="2026-09-30"' in narrowed], [True, True, True])
check("the kind list names each kind by its own title",
      '<option value="first-kind">First Kind</option>' in narrowed, True)
check("with no words, the page says how many are in that folder",
      "2 pages are in the folder places." in wiki.search_page(
          root, "", folder="places"), True)
check("with no words and dates, how many have notes from then",
      "1 page has notes from 2026-09-01 to 2026-09-30." in wiki.search_page(
          root, "", start="2026-09-01", end="2026-09-30"), True)
check("the top folder is said as the top folder",
      "those words somewhere on the page, in any order, in the top folder."
      in wiki.search_page(root, "first note", folder="/"), True)
check("a kind is said by its name",
      "among First Kind pages" in wiki.search_page(root, "lamp",
                                                   kind="first-kind"), True)
bad = wiki.search_page(root, "lamp", start="not a date")
plain = wiki.search_page(root, "lamp")
check("a date that cannot be read is said, and left out",
      ["The first date could not be read as a date, so it was left out."
       in bad, bad.count("<h3>"), "in notes" in bad],
      [True, plain.count("<h3>"), False])
onepage = wiki.search_page(root, "bell", page="places/fifth.html")
check("the page list comes first in the narrowing, with Any page first",
      onepage.index('<label for="on-page">On which page</label>')
      < onepage.index('<label for="in-folder">'), True)
check("a chosen page stays chosen, and is said by its title",
      ['<option value="places/fifth.html" selected>' in onepage,
       "in any order, on the page Fifth Place." in onepage], [True, True])
check("a page that is not there is ignored rather than finding nothing",
      "Nothing has" in wiki.search_page(root, "bell", page="gone.html"),
      False)
check("a kind that is not there is ignored rather than finding nothing",
      "Nothing has" in wiki.search_page(root, "lamp", kind="no-such-kind"),
      False)


# --- through the real program ------------------------------------------------------

import forms  # noqa: E402

forms.HERE = root
server = ThreadingHTTPServer(("127.0.0.1", 0), forms.Handler)
base = "http://127.0.0.1:%d" % server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()


def get(query):
    with urllib.request.urlopen(base + "/search?" + urllib.parse.urlencode(
            query)) as resp:
        return resp.read().decode("utf-8")


# A page's title is in the page list on every search now, so a title
# only counts as found when it is a result heading.
def result(title, body):
    return title + "</a></h3>" in body


body = get({"q": "note first"})
check("searching through the program finds words in any order",
      [result("First Place", body), result("Second Place", body)],
      [True, True])
body = get({"q": "first note", "together": "1"})
check("and the tick box, sent from the browser, keeps the words together",
      [result("First Place", body), result("Second Place", body)],
      [False, True])
body = get({"q": "lamp", "folder": "places", "kind": "", "from": "2026-09-01",
            "to": "2026-09-30"})
check("the narrowing boxes, sent from the browser, narrow the search",
      [result("Fifth Place", body), result("First Entry", body),
       "in notes from 2026-09-01 to 2026-09-30, in the folder places" in body],
      [True, False, True])
body = get({"q": "lamp", "kind": "first-kind"})
check("and so does the kind list",
      [result("First Entry", body), result("Fifth Place", body)],
      [True, False])
body = get({"q": "bell", "page": "places/inner/sixth.html"})
check("and so does the page list",
      ["Sixth Place</a></h3>" in body, "Fifth Place</a></h3>" in body],
      [True, False])
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
