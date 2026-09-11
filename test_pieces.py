#!/usr/bin/env python3
"""Checks for saying what a piece is before typing it.

The box on the Add page: paragraph, heading level 1 to 6, bulleted list,
numbered list, quote. Checked as pieces first, then through the real
program on a throwaway folder.
"""

import re
import shutil
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path

import editing
import markup
import wiki

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


# --- what the box offers -----------------------------------------------

check("the box offers every kind, paragraph first, in the agreed order",
      [w for _v, w in markup.PIECES],
      ["Paragraph", "Heading level 1", "Heading level 2", "Heading level 3",
       "Heading level 4", "Heading level 5", "Heading level 6",
       "Bulleted list", "Numbered list", "Quote"])


# --- headings -------------------------------------------------------------

for n in range(1, 7):
    check("heading level %d is a level %d heading" % (n, n),
          markup.as_piece("First Heading", "h%d" % n),
          "<h%d>First Heading</h%d>" % (n, n))
check("a heading typed over two lines is still one heading",
      markup.as_piece("First\nHeading", "h3"), "<h3>First Heading</h3>")
check("a heading keeps its marks", markup.as_piece("A **bold** one", "h2"),
      "<h2>A <strong>bold</strong> one</h2>")
check("a heading does not treat a # as a mark",
      markup.as_piece("# Not a level", "h4"), "<h4># Not a level</h4>")
check("a tag typed in a heading stays text",
      "<script>" in markup.as_piece("<script>x</script>", "h2"), False)


# --- lists -----------------------------------------------------------------

check("a bulleted list is one item per line",
      markup.as_piece("list thing\nlist thing 2\nlist thing 3", "ul"),
      "<ul>\n<li>list thing</li>\n<li>list thing 2</li>\n"
      "<li>list thing 3</li>\n</ul>")
check("a numbered list is one item per line, numbered by the page",
      markup.as_piece("list thing\nlist thing 2", "ol"),
      "<ol>\n<li>list thing</li>\n<li>list thing 2</li>\n</ol>")
check("numbers typed anyway are taken off, so they are not read twice",
      markup.as_piece("1. list thing\n2) list thing 2", "ol"),
      "<ol>\n<li>list thing</li>\n<li>list thing 2</li>\n</ol>")
check("only one typed number is taken off a line",
      markup.as_piece("3. 3. list thing 3.", "ol"),
      "<ol>\n<li>3. list thing 3.</li>\n</ol>")
check("dashes typed in a bulleted list are taken off",
      markup.as_piece("- list thing\n* list thing 2", "ul"),
      "<ul>\n<li>list thing</li>\n<li>list thing 2</li>\n</ul>")
check("a bulleted list keeps numbers that start a line, they are words there",
      markup.as_piece("2. list thing", "ul"),
      "<ul>\n<li>2. list thing</li>\n</ul>")
check("blank lines in a list do not make empty items",
      markup.as_piece("list thing\n\n\nlist thing 2", "ul").count("<li>"), 2)
check("a list item keeps its marks",
      "<li>a <em>small</em> thing</li>" in markup.as_piece(
          "a *small* thing", "ol"), True)
check("a tag typed in a list item stays text",
      "&lt;script&gt;" in markup.as_piece("<script>x</script>", "ul"), True)


# --- quotes and paragraphs ---------------------------------------------

check("a quote holds its paragraphs",
      markup.as_piece("First part.\n\nSecond part.", "quote"),
      "<blockquote>\n<p>First part.</p>\n<p>Second part.</p>\n</blockquote>")
check("a quote keeps a line break",
      "First line<br>\nSecond line" in markup.as_piece(
          "First line\nSecond line", "quote"), True)
TYPED = "## A mark\n\nSome <b>typed</b> words.\n\n- a\n- b"
check("paragraph is the note box exactly as it always was",
      markup.as_piece(TYPED, "paragraph"), markup.to_html(TYPED))
check("choosing nothing is paragraph", markup.as_piece(TYPED, ""),
      markup.to_html(TYPED))
check("something odd sent as the kind is paragraph too",
      markup.as_piece(TYPED, "h7"), markup.to_html(TYPED))
check("nothing typed is nothing, whatever was chosen",
      [markup.as_piece("  \n ", v) for v, _w in markup.PIECES],
      [""] * len(markup.PIECES))


# --- the Add page, read the way NVDA would move through it -------------

class Reading(HTMLParser):
    def __init__(self):
        super().__init__()
        self.order, self.ids, self.fors = [], [], []
        self.controls, self.options = [], []
        self.autofocus = False
        self._in = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.autofocus = self.autofocus or "autofocus" in a
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "label":
            self.fors.append(a.get("for"))
        if tag in ("select", "textarea"):
            self.controls.append(a.get("id"))
            self.order.append((tag, a.get("id")))
        if tag in ("h1", "label", "button", "option"):
            self._in = [tag, ""]

    def handle_data(self, data):
        if self._in:
            self._in[1] += data

    def handle_endtag(self, tag):
        if self._in and tag == self._in[0]:
            words = " ".join(self._in[1].split())
            if tag == "option":
                self.options.append(words)
            else:
                self.order.append((tag, words))
            self._in = None


def slug(text, fallback=""):
    out = "".join(c.lower() if c.isalnum() else "-" for c in text)
    return "-".join(p for p in out.split("-") if p) or fallback


def write(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="\n")
    return True


root = Path(tempfile.mkdtemp(prefix="piecescheck-"))
rel, _t = wiki.make_page(root, "First Page", "", slug, write)

for after in (None, 0):
    where = "at the end" if after is None else "after a piece"
    r = Reading()
    r.feed(wiki.add_page(root, rel, after=after))
    check("adding " + where + ": every box has a label pointing at it",
          sorted(r.controls), sorted(f for f in r.fors if f in r.controls))
    check("adding " + where + ": what it is comes before what you say",
          [x for x in r.order if x[0] in ("label", "select", "textarea")],
          [("label", "What is it?"), ("select", "note-as"),
           ("label", "What do you want to say?"), ("textarea", "note-box")])
    check("adding " + where + ": the choices are the agreed ones",
          r.options, [w for _v, w in markup.PIECES])
    check("adding " + where + ": no id is used twice",
          len(r.ids), len(set(r.ids)))
    check("adding " + where + ": nothing grabs focus", r.autofocus, False)

print("\n  The Add page, in reading order:")
for tag, words in r.order:
    print("    " + tag.ljust(9) + str(words))
print()


# --- through the real program ------------------------------------------

import forms  # noqa: E402

forms.HERE = root
server = ThreadingHTTPServer(("127.0.0.1", 0), forms.Handler)
base = "http://127.0.0.1:%d" % server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()


def post(path, fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    with urllib.request.urlopen(base + path, data) as resp:
        return resp.status, resp.read().decode("utf-8")


def on_disk():
    return (root / rel).read_text(encoding="utf-8")


def add(kind, note):
    fields = {"page": rel, "_to": rel, "_back": "/" + rel, "note": note}
    if kind is not None:
        fields["_as"] = kind
    return post("/save", fields)


status, _b = add("ol", "list thing\nlist thing 2")
check("saving a numbered list works", status, 200)
check("the numbered list is in the file, inside a dated note",
      re.search(r'<div class="addition">\s*<p class="when">[^<]+</p>\s*'
                r"<ol>\n<li>list thing</li>\n<li>list thing 2</li>\n</ol>",
                on_disk()) is not None, True)
check("the choice itself is not written into the page",
      "_as" in on_disk() or "as: ol" in on_disk(), False)

add("h1", "First Heading")
check("a level 1 heading can be saved from the box",
      "<h1>First Heading</h1>" in on_disk(), True)

add(None, "Plain words with **bold**.")
check("a form sent without the box still saves paragraphs as before",
      "<p>Plain words with <strong>bold</strong>.</p>" in on_disk(), True)

before = on_disk()
first = editing.blocks(before)[0]
print("  The first piece on the page, which the quote should follow: "
      + editing.as_words(first[3]))
status, _b = post("/addafter", {"page": rel, "n": "0", "_as": "quote",
                                "note": "Quoted words."})
check("adding a quote after a piece works", status, 200)
text = on_disk()
check("the quote is in the file",
      "<blockquote>\n<p>Quoted words.</p>\n</blockquote>" in text, True)
check("it landed straight after the first piece, and nothing else changed",
      text, before[:first[5]]
      + "\n<blockquote>\n<p>Quoted words.</p>\n</blockquote>"
      + before[first[5]:])
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
