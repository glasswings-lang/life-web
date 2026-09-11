#!/usr/bin/env python3
"""Checks for moving.py - moving writing on a page, onto another page,
and out of the way. The last part goes through the real program on a
throwaway folder."""

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
<link rel="stylesheet" href="style.css">
</head>
<body>

<h1>First Page</h1>

<nav>
<a href="index.html">Back to the top</a>
</nav>

<h2>First Section</h2>
<p>Under the first section, with a link to <a href="places/second-place.html">Second Place</a>.</p>
<ul>
<li>list thing</li>
<li>list thing 2</li>
</ul>
<h3>Smaller Section</h3>
<p>Under the smaller section.</p>
<h2>Second Section</h2>
<p>Under the second section.</p>
<h1>Chosen Level One</h1>

<!-- here -->
<div class="addition">
<p class="when">2026-09-01 09:00</p>
<h2>Heading in a note</h2>
<p>Words in a note.</p>
</div>

<template>
<div class="addition">
<p class="when">{when}</p>
<p>{note}</p>
</div>
</template>

</body>
</html>
"""


def words(text):
    return [editing.as_words(p[3]) for p in editing.blocks(text)]


S = words(PAGE)


def order(*picks):
    return [S[i] for i in picks]


def machinery(text):
    """Everything that is not writing, which moving must never touch."""
    return [text.count(x) for x in ("<h1>First Page</h1>", "<nav>",
                                    "<!-- here -->", '<div class="addition">',
                                    "<template>", "</body>")]


# --- what the pieces are ---------------------------------------------------

check("ten pieces are found", len(S), 10)
check("the page's own title is not a piece", "First Page" in S, False)
check("a level 1 heading chosen from the Add page is a piece",
      S[7], "Chosen Level One")
P = editing.blocks(PAGE)
check("each heading's section ends at the next heading at its level or above, "
      "or at anything that is not writing",
      [moving.section_end(PAGE, P, i) for i in range(10)],
      [4, 1, 2, 4, 4, 6, 6, 7, 9, 9])
check("a piece is named by what it is and its first words",
      [moving.label(P[i], most=3) for i in (0, 1, 2, 7, 3)],
      ["Heading level 2: First Section", "Paragraph: Under the first",
       "Bulleted list: list thing list", "Heading level 1: Chosen Level One",
       "Heading level 3: Smaller Section"])


# --- moving on the page ------------------------------------------------------

new, trouble = moving.move(PAGE, 0, "after:4")
check("moving a heading reported no trouble", trouble, "")
check("A HEADING MOVES ON ITS OWN, and what was under it stays put",
      words(new), order(1, 2, 3, 4, 0, 5, 6, 7, 8, 9))
check("nothing that is not writing was touched", machinery(new),
      machinery(PAGE))

new, _t = moving.move(PAGE, 0, "after:6", whole=True)
check("a heading can take its section along when asked",
      words(new), order(5, 6, 0, 1, 2, 3, 4, 7, 8, 9))
check("the link inside it came along untouched, since it stayed on its page",
      'href="places/second-place.html"' in new, True)

new, _t = moving.move(PAGE, 3, "top", whole=True)
check("a smaller section moves to the top",
      words(new), order(3, 4, 0, 1, 2, 5, 6, 7, 8, 9))
back, _t = moving.move(new, 0, "after:4", whole=True)
check("and back again gives the very same file", back, PAGE)

new, _t = moving.move(PAGE, 6, "bottom")
check("the bottom is below everything, notes included",
      words(new), order(0, 1, 2, 3, 4, 5, 7, 8, 9, 6))
check("so it did not land inside the note",
      "<p>Words in a note.</p>\n</div>" in new
      and new.index("Under the second section.")
      < new.index("<template>"), True)

new, _t = moving.move(PAGE, 9, "top")
check("writing can come out of a note to the top of the page",
      words(new), order(9, 0, 1, 2, 3, 4, 5, 6, 7, 8))
check("and the note keeps its date and its heading",
      '<p class="when">2026-09-01 09:00</p>\n<h2>Heading in a note</h2>' in new,
      True)
check("nothing that is not writing was touched by that either",
      machinery(new), machinery(PAGE))

new, _t = moving.move(PAGE, 8, "after:4", whole=True)
check("a section inside a note can move out of it", words(new),
      order(0, 1, 2, 3, 4, 8, 9, 5, 6, 7))

check("moving to where it already is changes nothing",
      [moving.move(PAGE, 0, "top"), moving.move(PAGE, 1, "after:0")],
      [(PAGE, ""), (PAGE, "")])
check("a section cannot go after something inside itself",
      moving.move(PAGE, 0, "after:2", whole=True)[0], None)
check("but a heading alone can go after what was under it",
      moving.move(PAGE, 0, "after:2")[1], "")
check("choosing nowhere is refused", moving.move(PAGE, 0, "")[0], None)
check("something odd sent as the place is refused",
      moving.move(PAGE, 0, "after:1; x")[0], None)
check("a piece that is not there is refused", moving.move(PAGE, 99, "top")[0],
      None)
check("going after a piece that is not there is refused",
      moving.move(PAGE, 0, "after:99")[0], None)


# --- several picked pieces together -------------------------------------------

new, trouble = moving.move_many(PAGE, [6, 1, 4], "top")
check("picked pieces move together, in page order, whatever order they came in",
      words(new), order(1, 4, 6, 0, 2, 3, 5, 7, 8, 9))
check("and nothing that is not writing was touched", machinery(new),
      machinery(PAGE))
new, _t = moving.move_many(PAGE, [0, 9], "after:5")
check("picked pieces can go after another piece, one of them out of a note",
      words(new), order(1, 2, 3, 4, 5, 0, 9, 6, 7, 8))
check("a heading picked with others moves on its own",
      words(moving.move_many(PAGE, [0, 6], "bottom")[0]),
      order(1, 2, 3, 4, 5, 7, 8, 9, 0, 6))
check("they cannot go after one of themselves",
      moving.move_many(PAGE, [1, 4], "after:4")[0], None)
check("picking nothing is refused, and says so",
      moving.move_many(PAGE, [], "top"), (None, moving.NOTHING))
check("a picked piece that is not there is refused",
      moving.move_many(PAGE, [1, 99], "top")[0], None)
check("choosing nowhere for picked pieces is refused",
      moving.move_many(PAGE, [1, 4], "")[0], None)


# --- putting writing onto a page, and its links ---------------------------------

EMPTY = "<body>\n<h1>Second Place</h1>\n\n<!-- here -->\n\n</body>"
check("a page with nothing written takes it above the spot notes go",
      moving.put(EMPTY, "<p>x</p>", "bottom"),
      "<body>\n<h1>Second Place</h1>\n\n<p>x</p>\n<!-- here -->\n\n</body>")
check("so does its top", moving.put(EMPTY, "<p>x</p>", "top"),
      moving.put(EMPTY, "<p>x</p>", "bottom"))
check("a page with no spot for notes takes it above its end",
      moving.put("<body><h1>A</h1></body>", "<p>x</p>"),
      "<body><h1>A</h1><p>x</p>\n</body>")
LINKY = ('<a href="places/second-place.html">Second Place</a> '
         '<a href="/search">Find</a> <a href="https://example.com/">Site</a>')
check("a link is rewritten for the page it is going onto",
      moving.rebase(LINKY, "first-page.html", "places/other.html"),
      '<a href="second-place.html">Second Place</a> '
      '<a href="/search">Find</a> <a href="https://example.com/">Site</a>')
check("and for the place put-away writing is kept",
      'href="../../places/second-place.html"' in moving.rebase(
          LINKY, "first-page.html", "_deleted/pieces/x.html"), True)


# --- onto another page and away, on disk ----------------------------------------

def read(path):
    return links._read(Path(path))


def write(path, text):
    try:
        Path(path).write_text(text, encoding="utf-8", newline="\n")
        return True
    except OSError:
        return False


def fresh():
    root = Path(tempfile.mkdtemp(prefix="movingcheck-"))
    (root / "style.css").write_text("body { }", encoding="utf-8")
    (root / "first-page.html").write_text(PAGE, encoding="utf-8",
                                          newline="\n")
    (root / "places").mkdir()
    (root / "places" / "second-place.html").write_text(
        wiki.PAGE.format(title="Second Place", up="../",
                         to="places/second-place.html"),
        encoding="utf-8", newline="\n")
    return root


root = fresh()
said = moving.onto(root, "first-page.html", 0, True,
                   "places/second-place.html", "bottom", read, write)
check("moving a section onto another page says so", said,
      "Moved onto Second Place, at the bottom of it.")
here = read(root / "first-page.html")
there = read(root / "places" / "second-place.html")
check("the section has left its page", words(here), order(5, 6, 7, 8, 9))
check("and arrived on the other, whole", words(there), order(0, 1, 2, 3, 4))
check("its link was rewritten so it still lands on the same page",
      '<a href="second-place.html">Second Place</a>' in there, True)
check("the page it left is kept as it was",
      read(root / "first-page.html.bak"), PAGE)
check("moving onto the page it is already on is refused and changes nothing",
      [moving.onto(root, "first-page.html", 0, False, "first-page.html",
                   "top", read, write).startswith("That is the page"),
       read(root / "first-page.html")], [True, here])

n = words(here).index("Second Section")
said = moving.away(root, "first-page.html", n, True, read, write,
                   "2026-09-11 12:30")
kept = root / "_deleted" / "pieces" / "first-page-2026-09-11-12-30.html"
check("putting a section away says, in plain words, that it is kept safe",
      said, "Put away. It is kept safe on the Put away page, and you can "
      "bring it back from there.")
check("it is kept in a file of its own", kept.is_file(), True)
check("that file holds the whole section",
      words(kept.read_text(encoding="utf-8"))[-2:], order(5, 6))
check("and says which page it came from, with a link that works from there",
      'This was on <a href="../../first-page.html">first-page.html</a> until '
      "2026-09-11 12:30." in kept.read_text(encoding="utf-8"), True)
check("it is gone from the page", "Second Section" in read(
    root / "first-page.html"), False)
check("put-away writing is not listed as a page",
      [p for p in links.pages(root) if "_deleted" in p], [])
moving.away(root, "first-page.html", 0, False, read, write, "2026-09-11 12:30")
check("putting something else away in the same minute keeps both",
      (root / "_deleted" / "pieces"
       / "first-page-2026-09-11-12-30-2.html").is_file(), True)
shutil.rmtree(root, ignore_errors=True)

root = fresh()
said = moving.onto(root, "first-page.html", [1, 6], False,
                   "places/second-place.html", "top", read, write)
check("several picked pieces go onto another page, and it says how many",
      said, "Moved 2 pieces onto Second Place, at the top of it.")
there = read(root / "places" / "second-place.html")
check("they arrive in page order", words(there)[:2], order(1, 6))
check("with the link inside rewritten",
      '<a href="second-place.html">Second Place</a>' in there, True)
said = moving.away(root, "first-page.html", [0, 1], False, read, write,
                   "2026-09-11 13:30")
check("several picked pieces put away are kept together, and it says so",
      said, "Put away 2 pieces. They are kept safe together on the Put away "
      "page, and you can bring them back from there.")
check("the kept file holds both, in page order",
      words((root / "_deleted" / "pieces" / "first-page-2026-09-11-13-30.html")
            .read_text(encoding="utf-8"))[-2:], order(0, 2))
EMPTIED = PAGE.replace("<h2>Heading in a note</h2>\n<p>Words in a note.</p>\n",
                       "")
write(root / "emptied.html", EMPTIED)
said = moving.away_note(root, "emptied.html", 0, read, write,
                        "2026-09-11 13:31")
check("an empty note can be put away, date and all",
      [said.startswith("Put away."), notes.find(read(root / "emptied.html"))],
      [True, []])
shutil.rmtree(root, ignore_errors=True)


# --- moving from the Edit page, read the way NVDA would move through it ------

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
        if tag in ("select", "textarea") or (
                tag == "input" and a.get("type") != "hidden"):
            self.controls.append(a.get("id"))
            self.order.append((tag, a.get("id")))
        if tag == "select":
            self._select = a.get("id")
            self.options[self._select] = []
        if tag in ("h2", "legend", "label", "button", "option", "a"):
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
edit = wiki.pieces_page(root, "first-page.html")
r = Reading()
r.feed(edit)
check("every control on the Edit page has a label pointing at it",
      sorted(r.controls), sorted(f for f in r.fors if f in r.controls))
check("no id is used twice", len(r.ids), len(set(r.ids)))
check("nothing grabs focus", r.autofocus, False)
check("every piece has its own Move form, right on the Edit page",
      edit.count('action="/movepiece"'), 10)
check("each Move form has one button, so Enter in it presses Move",
      [form.split("</form>")[0].count("<button")
       for form in edit.split('action="/movepiece"')[1:]], [1] * 10)
first = r.order.index(("h2", "Heading"))
after = next(i for i in range(first + 1, len(r.order))
             if r.order[i][0] == "h2")
check("under a heading: its words, Add, then Move with its tick box",
      r.order[first:after],
      [("h2", "Heading"), ("legend", "Heading level 2: First Section"),
       ("label", "The words"), ("textarea", "piece0"),
       ("button", "Save this piece"), ("a", "Add something after this piece"),
       ("input", "pick0"), ("label", "Pick this one"),
       ("label", "Move it to"), ("select", "move0"),
       ("input", "move0-all"), ("label", "Take the 4 pieces under it too"),
       ("label", "or onto a new page called"), ("input", "move0-new"),
       ("button", "Move")])
check("each moving group is named after its piece, so NVDA says which",
      [w for t, w in r.order if t == "legend"][:4],
      ["Heading level 2: First Section",
       "Paragraph: Under the first section, with a link to",
       "Bulleted list: list thing list thing 2",
       "Heading level 3: Smaller Section"])
check("every Move button has a sentence before it saying what pressing does",
      edit.count("<p>Pressing this moves it where you chose."), 10)
check("and so does every Save button",
      edit.count("<p>Pressing this saves your new words in place of the old "
                 "ones."), 10)
inside = edit.split("<legend>Heading level 2: First Section</legend>",
                    1)[1].split("</fieldset>", 1)[0]
check("a piece's words box, Add link and Move list are all in its one group",
      ['action="/editpiece"' in inside, "Add something after this piece"
       in inside, 'action="/movepiece"' in inside], [True, True, True])
check("each piece is named once, not once for the words and again for moving",
      edit.count("<legend>Heading level 2: First Section</legend>"), 1)
check("only a heading with writing under it has the tick box",
      [c for c in r.controls if c.endswith("-all")],
      ["move0-all", "move3-all", "move5-all", "move8-all"])
check("and it says how much it would take",
      [w for t, w in r.order if t == "label" and w.startswith("Take")],
      ["Take the 4 pieces under it too", "Take the 1 piece under it too",
       "Take the 1 piece under it too", "Take the 1 piece under it too"])
opts = r.options["move0"]
check("the list starts with nowhere chosen, then this page's top and bottom",
      opts[:3], ["(choose where)", "The top of this page",
                 "The bottom of this page"])
check("it does not offer after itself",
      "After Heading level 2: First Section" in opts, False)
check("it offers the other pages, and not this one",
      ["Onto Second Place - places/second-place.html" in opts,
       any(o.endswith("- first-page.html") for o in opts)], [True, False])
check("Put it away is last in the list", opts[-1], "Put it away")
print("\n  One heading on the Edit page, in reading order:")
for tag, got in r.order[first:after]:
    print("    " + tag.ljust(9) + got)
print()

check("every piece has a Pick this one box, tied to the form at the bottom",
      edit.count('form="bulk" id="pick'), 10)
check("the picked pieces go from one list and one button at the bottom",
      [r.options["bulk-to"][0], r.options["bulk-to"][-1],
       ("legend", "The picked ones") in r.order,
       ("label", "Move them to") in r.order,
       ("button", "Move the picked ones") in r.order],
      ["(choose where)", "Put them away", True, True, True])
check("and says what pressing it does, before the button",
      "<p>Pressing this moves every picked one there" in edit, True)
check("the bottom list comes after every piece",
      edit.index('<h2>Move the picked ones together</h2>')
      > edit.index(">Words in a note.</textarea>"), True)
write(root / "one.html", "<html><body><h1>One</h1>\n<p>Only piece.</p>\n"
      "</body></html>")
check("a page with one piece has nothing to pick",
      'form="bulk"' in wiki.pieces_page(root, "one.html"), False)

EMPTIED = PAGE.replace("<h2>Heading in a note</h2>\n<p>Words in a note.</p>\n",
                       "")
write(root / "emptied.html", EMPTIED)
emptied = wiki.pieces_page(root, "emptied.html")
check("a note with nothing left in it shows in the editor, in a named group",
      "<legend>An empty note from 2026-09-01 09:00</legend>" in emptied, True)
check("saying gently what pressing does",
      "<p>Pressing this puts the note away. It is kept safe, and you can "
      "bring it back from the Put away page.</p>" in emptied, True)
check("where it sits on the page: after the pieces before it",
      emptied.index(">Chosen Level One</textarea>")
      < emptied.index("<legend>An empty note")
      < emptied.index("<h2>Move the picked ones together</h2>"), True)
check("with a button that puts it away", "Put this note away" in emptied, True)
check("a note with writing in it is not called empty",
      "An empty note" in edit, False)


# --- through the real program --------------------------------------------------

import forms  # noqa: E402

forms.HERE = root
server = ThreadingHTTPServer(("127.0.0.1", 0), forms.Handler)
base = "http://127.0.0.1:%d" % server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()


def get(path):
    try:
        with urllib.request.urlopen(base + path) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code


def post(fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    with urllib.request.urlopen(base + "/movepiece", data) as resp:
        return resp.geturl(), resp.read().decode("utf-8")


def page():
    return read(root / "first-page.html")


def send(**fields):
    fields.setdefault("page", "first-page.html")
    fields.setdefault("seen", notes.fingerprint(page()))
    return post(fields)


check("the Edit page is served with its Move forms",
      get("/edit?page=first-page.html"), 200)

url, body = send(n="6", to="bottom")
check("pressing Move lands back on the Edit page",
      "/edit?page=first-page.html" in url, True)
check("and says what happened", "Moved to the bottom of the page." in body,
      True)
check("the file has it at the bottom", words(page())[-1],
      "Under the second section.")

before = page()
url, body = send(n="0", to="bottom", seen=notes.fingerprint(PAGE))
check("a page changed since it was shown moves nothing", page(), before)
check("and says why", "has changed since that was shown" in body, True)

url, body = send(n="0", to="")
check("Move with nowhere chosen does not crash, and says so",
      "Nowhere was chosen" in body, True)

url, body = send(n="0", to="top", newpage="Ignored Page")
check("a place chosen from the list wins over a typed page name",
      [(root / "ignored-page.html").exists(), "already there" in body],
      [False, True])

url, body = send(n="0", to="", what="section", newpage="Third Place")
check("with nothing chosen, a typed name takes the section onto a new page",
      words(read(root / "third-place.html")), order(0, 1, 2, 3, 4))
check("and the page says so",
      "Moved onto Third Place, at the bottom of it." in body, True)

n = words(page()).index("Second Section")
url, body = send(n=str(n), to="onto:places/second-place.html")
check("a heading chosen onto another page goes on its own",
      [words(read(root / "places" / "second-place.html"))[-1],
       "Under the second section." in page()],
      ["Second Section", True])

n = words(page()).index("Chosen Level One")
url, body = send(n=str(n), to="away")
check("Put it away through the program keeps it",
      len(list((root / "_deleted" / "pieces").glob("first-page-*.html"))), 1)
check("and takes it off the page", "Chosen Level One" in page(), False)


def post_many(pairs):
    data = urllib.parse.urlencode(pairs).encode("utf-8")
    with urllib.request.urlopen(base + "/movepieces", data) as resp:
        return resp.geturl(), resp.read().decode("utf-8")


def base_pairs():
    return [("page", "first-page.html"), ("seen", notes.fingerprint(page()))]


check("what is left before picking", words(page()),
      ["Heading in a note", "Words in a note.", "Under the second section."])
url, body = post_many(base_pairs() + [("pick", "0"), ("pick", "2"),
                                      ("to", "top")])
check("picked pieces sent together through the program move together",
      words(page()),
      ["Heading in a note", "Under the second section.", "Words in a note."])
check("and it says how many", "Moved 2 pieces to the top of the page." in body,
      True)
url, body = post_many(base_pairs() + [("to", "top")])
check("the bottom button with nothing picked says so",
      "Nothing was picked, so nothing moved." in body, True)

send(n="2", to="top")
check("moving the last words out of a note leaves it empty",
      [f["words"] for f in notes.find(page())], [""])
with urllib.request.urlopen(base + "/edit?page=first-page.html") as resp:
    shown = resp.read().decode("utf-8")
check("and the Edit page shows the empty note", "An empty note" in shown, True)
data = urllib.parse.urlencode({"page": "first-page.html", "n": "0",
                               "to": "away", "from": "edit",
                               "seen": notes.fingerprint(page())})
with urllib.request.urlopen(base + "/movenote", data.encode("utf-8")) as resp:
    url, body = resp.geturl(), resp.read().decode("utf-8")
check("Put this note away takes it off the page",
      notes.find(page()), [])
check("and lands back on the Edit page, saying so",
      ["/edit?page=first-page.html" in url, "Put away." in body],
      [True, True])
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
