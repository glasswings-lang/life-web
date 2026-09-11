#!/usr/bin/env python3
"""Checks for restore.py - bringing back what was put away. The last part
goes through the real program on a throwaway folder."""

import re
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

import editing
import links
import moving
import restore
import wiki

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


def read(path):
    return links._read(Path(path))


def write(path, text):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, encoding="utf-8", newline="\n")
        return True
    except OSError:
        return False


FIRST = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>First Page</title>
</head>
<body>

<h1>First Page</h1>

<p>A line with a link to <a href="places/second-place.html">Second Place</a>.</p>
<p>Another line.</p>

<!-- here -->

</body>
</html>
"""

THIRD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Third Page</title>
<link rel="stylesheet" href="style.css">
</head>
<body>

<h1>Third Page</h1>

<p>Back to <a href="first-page.html">First Page</a>.</p>

</body>
</html>
"""

SECOND = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Second Place</title>
</head>
<body>

<h1>Second Place</h1>

<p>Next door is <a href="other-place.html">Other Place</a>.</p>
<form method="post" action="/save">
<input type="hidden" name="_to" value="places/second-place.html">
</form>

</body>
</html>
"""


def fresh():
    root = Path(tempfile.mkdtemp(prefix="restorecheck-"))
    write(root / "style.css", "body { }")
    write(root / "first-page.html", FIRST)
    write(root / "third-page.html", THIRD)
    write(root / "places" / "second-place.html", SECOND)
    write(root / "places" / "other-place.html",
          SECOND.replace("Second Place", "Other Place"))
    return root


def put_things_away(root):
    """One of each: writing, a page, a page from a folder, a whole folder."""
    moving.away(root, "first-page.html", 0, False, read, write,
                "2026-09-11 14:00")
    links.remove(root, "third-page.html", read, write)
    links.remove(root, "places/second-place.html", read, write)
    write(root / "_deleted" / "archive" / "a.html",
          "<html><head><title>First Archived</title></head><body></body></html>")
    write(root / "_deleted" / "archive" / "sub" / "b.html",
          "<html><head><title>Second Archived</title></head><body></body></html>")


def words(text):
    return [editing.as_words(p[3]) for p in editing.blocks(text)]


TIDY = '<ul id="tidy"></ul>'


# --- finding what was put away ------------------------------------------------

root = fresh()
check("nothing put away counts as nothing", restore.count(root), 0)
check("and the Put away page says so",
      "Nothing is put away right now." in wiki.putaway_page(root), True)
check("the front page does not mention it when nothing is put away",
      "/putaway" in wiki.fill_tidy(TIDY, root), False)

put_things_away(root)
found = restore.writing(root)
check("put-away writing is found", len(found), 1)
check("with the page it came from, and when",
      (found[0]["page"], found[0]["when"]),
      ("first-page.html", "2026-09-11 14:00"))
check("and its words", found[0]["words"],
      "A line with a link to Second Place.")
pages, folders = restore.top(root)
check("a page put away from the top is found",
      "_deleted/third-page.html" in pages, True)
check("a page put away from a folder that is still there is offered on its own",
      "_deleted/places/second-place.html" in pages, True)
check("a folder with nothing of its name left is offered whole",
      folders, [("archive", 2)])
check("put-away writing is not listed as a page too",
      [p for p in pages if "pieces" in p], [])
check("everything is counted", restore.count(root), 4)
check("and the front page says how many",
      "Put away</a> &mdash; 4 things you can bring back." in wiki.fill_tidy(
          TIDY, root), True)


# --- bringing writing back ----------------------------------------------------

before = read(root / "first-page.html")
check("bringing writing back reports no trouble",
      restore.bring_writing(root, found[0]["kept"], "first-page.html", read,
                            write), "")
now = read(root / "first-page.html")
check("it is back, at the bottom of the page", words(now),
      ["Another line.", "A line with a link to Second Place."])
check("its link is as it was before it was put away",
      '<a href="places/second-place.html">Second Place</a>' in now, True)
check("the put-away copy is gone", restore.writing(root), [])
check("the page as it was is kept", read(root / "first-page.html.bak"), before)
check("writing that is not put away any more is refused",
      restore.bring_writing(root, found[0]["kept"], "first-page.html", read,
                            write) != "", True)


# --- bringing pages back --------------------------------------------------------

check("a page comes back to the address it had",
      restore.bring_page(root, "_deleted/third-page.html", "third-page.html",
                         read, write), ("third-page.html", ""))
check("exactly as it was", read(root / "third-page.html"), THIRD)
check("and it is off the list",
      "_deleted/third-page.html" in restore.top(root)[0], False)

write(root / "places" / "second-place.html",
      SECOND.replace("Second Place", "A New Second Place"))
to, trouble = restore.bring_page(root, "_deleted/places/second-place.html",
                                 "places/second-place.html", read, write)
check("a page does not come back over one that is there now",
      (to, trouble.startswith("There is already a page")), ("", True))
to, trouble = restore.bring_page(root, "_deleted/places/second-place.html",
                                 "old-second-place", read, write)
got = read(root / "old-second-place.html") or ""
check("it can come back to an address you type, with .html added",
      (to, trouble), ("old-second-place.html", ""))
check("its links are rewritten for where it landed",
      '<a href="places/other-place.html">Other Place</a>' in got, True)
check("and so is the field naming its own file",
      'name="_to" value="old-second-place.html"' in got, True)
check("the empty folder it left in _deleted is tidied away",
      (root / "_deleted" / "places").exists(), False)

write(root / "_deleted" / "_ways.html",
      "<html><head><title>Ways</title></head><body></body></html>")
check("a new address starting with an underscore is refused",
      restore.bring_page(root, "_deleted/_ways.html", "_other.html", read,
                         write)[1] != "", True)
check("an address climbing out of the folder is refused",
      restore.bring_page(root, "_deleted/_ways.html", "../outside.html", read,
                         write)[1] != "", True)
check("but a page that had an underscore address can go back to it",
      restore.bring_page(root, "_deleted/_ways.html", "_ways.html", read,
                         write), ("_ways.html", ""))
check("something that was never put away is refused",
      restore.bring_page(root, "first-page.html", "x.html", read,
                         write)[1] != "", True)
check("a path climbing out of _deleted is refused",
      restore.bring_page(root, "_deleted/../first-page.html", "x.html", read,
                         write)[1] != "", True)


# --- bringing folders back -----------------------------------------------------

check("a folder's pages can be listed one at a time",
      restore.in_folder(root, "archive"),
      ["_deleted/archive/a.html", "_deleted/archive/sub/b.html"])
(root / "archive").mkdir()
check("a whole folder does not come back over something of the same name",
      restore.bring_folder(root, "archive").startswith("There is already"),
      True)
(root / "archive").rmdir()
check("a whole folder comes back in one go, everything in it",
      [restore.bring_folder(root, "archive"),
       (root / "archive" / "a.html").is_file(),
       (root / "archive" / "sub" / "b.html").is_file(),
       (root / "_deleted" / "archive").exists()], ["", True, True, False])
check("a folder name that climbs is refused",
      restore.bring_folder(root, "../x") != "", True)
check("the put-away writing folder is not a folder to bring back",
      restore.bring_folder(root, "pieces") != "", True)
check("nothing is left to bring back", restore.count(root), 0)
shutil.rmtree(root, ignore_errors=True)


# --- the Put away page, read the way NVDA would move through it ---------------

class Reading(HTMLParser):
    def __init__(self):
        super().__init__()
        self.order, self.ids, self.fors, self.controls = [], [], [], []
        self.options, self.autofocus = {}, False
        self._in = self._select = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.autofocus = self.autofocus or "autofocus" in a
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "label":
            self.fors.append(a.get("for"))
        if tag == "select" or (tag == "input" and a.get("type") != "hidden"):
            self.controls.append(a.get("id"))
        if tag == "select":
            self._select = a.get("id")
            self.options[self._select] = []
        if tag in ("h2", "h3", "legend", "label", "button", "option"):
            self._in = [tag, ""]

    def handle_data(self, data):
        if self._in:
            self._in[1] += data

    def handle_endtag(self, tag):
        if self._in and tag == self._in[0]:
            got = " ".join(self._in[1].split())
            if tag == "option":
                self.options[self._select].append(got)
            else:
                self.order.append((tag, got))
            self._in = None


root = fresh()
put_things_away(root)
shown = wiki.putaway_page(root)
r = Reading()
r.feed(shown)
check("every control on the Put away page has a label pointing at it",
      sorted(r.controls), sorted(f for f in r.fors if f in r.controls))
check("no id is used twice", len(r.ids), len(set(r.ids)))
check("nothing grabs focus", r.autofocus, False)
check("it comes in order: writing, pages, folders",
      [w for t, w in r.order if t == "h2"], ["Writing", "Pages", "Folders"])
check("each thing is in a group named after it, so NVDA says which",
      [w for t, w in r.order if t == "legend"],
      ["A line with a link to Second Place.", "Second Place", "Third Page",
       "archive"])
check("every button has a sentence before it saying what pressing does",
      shown.count("<p>Pressing this "), 4)
# Hidden values are sent back when a button is pressed and never read
# aloud, so only what is read aloud is looked at here.
aloud = re.sub(r"<[^>]+>", " ", re.sub(r"<input[^>]*>", " ", shown))
check("what is read aloud talks about keeping things safe, not about files",
      ["_deleted" in aloud, "keep them safe" in aloud], [False, True])
check("writing offers the page it came from first",
      r.options["writing0"][0],
      "The page it came from: First Page - first-page.html")
check("a page's box holds the address it had",
      'id="page0" name="to" value="places/second-place.html"' in shown, True)
check("a folder has one button and a way to see its pages",
      ['href="/putaway?folder=archive"' in shown,
       "Bring the whole folder back" in shown], [True, True])
print("\n  The Put away page, in reading order:")
for tag, got in r.order:
    print("    " + tag.ljust(7) + got)
print()
inside = wiki.putaway_page(root, folder="archive")
check("a folder's own page offers each page in it",
      inside.count("Bring it back</button>"), 2)
check("and says which folder, so each comes back to it",
      inside.count('name="folder" value="archive"'), 2)
check("a folder that is not there says so",
      "Nothing is left in a put-away folder called nothing."
      in wiki.putaway_page(root, folder="nothing"), True)
check("putting a page away now says where to get it back",
      "on the Put away page" in wiki.remove_page(root, "first-page.html"), True)
check("and Repairs points there too",
      'href="/putaway"' in links.repairs_page(root), True)


# --- through the real program --------------------------------------------------

import forms  # noqa: E402

forms.HERE = root
server = ThreadingHTTPServer(("127.0.0.1", 0), forms.Handler)
base = "http://127.0.0.1:%d" % server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(base + path) as resp:
        return resp.status, resp.read().decode("utf-8")


def post(fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    with urllib.request.urlopen(base + "/bringback", data) as resp:
        return resp.geturl(), resp.read().decode("utf-8")


check("the Put away page is served", get("/putaway")[0], 200)
write(root / "index.html", wiki.STARTER)
check("the front page, as served, links to it with a count",
      '<a href="/putaway">Put away</a> &mdash; 4 things you can bring back.'
      in get("/index.html")[1], True)
try:
    urllib.request.urlopen(base + "/nothing-here.html")
    dead_end = ""
except urllib.error.HTTPError as err:
    dead_end = err.read().decode("utf-8")
check("the Not found page points to Put away too",
      '<a href="/putaway">Put away</a> lists it' in dead_end, True)

kept = restore.writing(root)[0]["kept"]
url, body = post({"kind": "writing", "item": kept,
                  "target": "first-page.html"})
check("Bring it back for writing lands on the Put away page, saying where",
      ["/putaway" in url, "It is back, at the bottom of First Page."
       in body], [True, True])
check("and the writing is on the page",
      "A line with a link to Second Place." in words(
          read(root / "first-page.html")), True)

moving.away(root, "first-page.html", 0, False, read, write, "2026-09-11 14:05")
kept = restore.writing(root)[0]["kept"]
url, body = post({"kind": "writing", "item": kept, "target": "",
                  "newpage": "Fourth Page"})
check("with no page chosen, a typed name makes one and brings it back there",
      words(read(root / "fourth-page.html") or "")[-1:], ["Another line."])
url, body = post({"kind": "writing", "item": kept, "target": "",
                  "newpage": ""})
check("with nothing chosen and nothing typed, it says so",
      "No page was chosen and no new page was named" in body, True)

url, body = post({"kind": "page", "item": "_deleted/third-page.html",
                  "to": "third-page.html"})
check("Bring it back for a page says it is back",
      "Third Page is back." in body, True)
check("and it is", (root / "third-page.html").is_file(), True)

write(root / "_deleted" / "old" / "c.html",
      "<html><head><title>Old Page</title></head><body></body></html>")
write(root / "_deleted" / "old" / "d.html",
      "<html><head><title>Old Page Two</title></head><body></body></html>")
url, body = post({"kind": "page", "item": "_deleted/old/c.html",
                  "to": "old/c.html", "folder": "old"})
check("a page brought back from a folder's own page lands back on that page",
      ["/putaway?folder=old" in url, (root / "old" / "c.html").is_file()],
      [True, True])

url, body = post({"kind": "folder", "item": "archive"})
check("Bring the whole folder back says so, and does it",
      ["The folder archive is back" in body,
       (root / "archive" / "sub" / "b.html").is_file()], [True, True])
url, body = post({"kind": "nonsense", "item": "x"})
check("something that cannot be brought back says so",
      "That is not something that can be brought back." in body, True)
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
