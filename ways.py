"""Ways of answering a question, kept in a file instead of in the code.

The asymmetry this rests on is yours: kinds of thing are infinite, ways
of answering are finite. Finite does not mean known, though - HTML has
more of them than this program started with, they are all documented on
MDN, and new ones arrive without asking anybody here.

So they live in `_ways.html`, in your folder, next to your pages. Adding
one is pasting the example straight off MDN into a box. Nothing is
converted, nothing has to be written in a syntax of mine, and there are
no placeholders to remember: whatever you paste is used as it stands,
with only the id and name rewritten so it belongs to the question it is
being used for.

Each one records three things:

    what it is called   what you pick from the list
    how it reads        what NVDA makes of it, in your words, so the
                        list can be judged by how it sounds and not by
                        what it is called
    the paste           the HTML, exactly as you pasted it

The underscore on the filename is what keeps it out of the pages: it is
a list the program reads, not something anybody visits.
"""

import html
import re

WAYS_FILE = "_ways.html"

SECTION_RE = re.compile(
    r'<section\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</section>', re.S | re.I)
NAME_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
READS_RE = re.compile(r'<p[^>]*class="reads"[^>]*>(.*?)</p>', re.S | re.I)
PASTE_RE = re.compile(r"<template[^>]*>(.*?)</template>", re.S | re.I)

CONTROL_RE = re.compile(r"<(input|textarea|select)\b", re.I)
ID_RE = re.compile(r'\bid="([^"]*)"', re.I)
REFERS_RE = re.compile(r'\b(for|list|form|aria-labelledby|aria-controls)'
                       r'="([^"]*)"', re.I)
NAME_ATTR_RE = re.compile(r'\bname="[^"]*"', re.I)
VALUE_ATTR_RE = re.compile(r'\bvalue="[^"]*"', re.I)
TAG_RE = re.compile(r"<[^>]+>")

STARTER = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ways to answer</title>
</head>
<body>

<h1>Ways to answer</h1>

<p>Each section below is one way of answering a question. The heading is
what it is called in the list. The paragraph says how it reads. What is
inside the template is the HTML, exactly as it was pasted.</p>

<p>You can change any of it by hand. Nothing here is generated.</p>

<!-- ways -->

</body>
</html>
"""

BLOCK = """<section id="{key}">
<h2>{name}</h2>
<p class="reads">{reads}</p>
<template>
{paste}
</template>
</section>
"""


def plain(fragment):
    return re.sub(r"\s+", " ",
                  html.unescape(TAG_RE.sub("", fragment or ""))).strip()


def key_for(name, taken):
    """A short name for a way, made from what it is called."""
    stem = "".join(c.lower() if c.isalnum() else "-" for c in name)
    stem = "-".join(p for p in stem.split("-") if p) or "way"
    out, n = stem, 2
    while out in taken:
        out, n = stem + "-" + str(n), n + 1
    return out


def load(text):
    """{key: {name, reads, paste}} - every way in the file."""
    out = {}
    for m in SECTION_RE.finditer(text or ""):
        inner = m.group(2)
        name = NAME_RE.search(inner)
        reads = READS_RE.search(inner)
        paste = PASTE_RE.search(inner)
        if not (name and paste):
            continue
        out[m.group(1)] = {
            "name": plain(name.group(1)),
            "reads": plain(reads.group(1)) if reads else "",
            "paste": paste.group(1).strip(),
        }
    return out


def add(text, name, reads, paste):
    """Put a new way into the file. Returns (new_text, key, trouble)."""
    name = " ".join((name or "").split())
    paste = (paste or "").strip()
    if not name:
        return None, None, "That way had no name."
    if not paste:
        return None, None, "Nothing was pasted, so there is no control."
    if not CONTROL_RE.search(paste):
        return None, None, ("There is no box in what was pasted. It needs "
                            "an <input>, a <textarea> or a <select> "
                            "somewhere in it.")
    if "<script" in paste.lower():
        return None, None, "That had a script in it, so it was not added."
    have = load(text)
    key = key_for(name, have)
    block = BLOCK.format(key=html.escape(key, quote=True),
                         name=html.escape(name),
                         reads=html.escape(" ".join((reads or "").split())),
                         paste=paste)
    if "<!-- ways -->" not in text:
        return None, None, ("That file has no <!-- ways --> in it, so there "
                            "is nowhere to put this.")
    at = text.index("<!-- ways -->") + len("<!-- ways -->")
    return text[:at] + "\n\n" + block + text[at:], key, ""


def page(have, said=""):
    """The list of ways, and the box that adds one."""
    rows = []
    for key, spec in sorted(have.items()):
        rows.append("<h3>" + html.escape(spec["name"]) + "</h3>\n<p>"
                    + (html.escape(spec["reads"]) if spec["reads"]
                       else "How it reads was not written down.")
                    + "</p>\n<pre><code>"
                    + html.escape(spec["paste"]) + "</code></pre>")
    return ("<h2>Ways you have added</h2>\n"
            + ("\n\n".join(rows) if rows else
               "<p>None yet. The built-in ones are still all there.</p>")
            + """

<h2>Add a way to answer</h2>

<p>Find the control you want on MDN, copy its example, and paste it
below exactly as it is. Nothing needs changing: the id and the name are
rewritten for you when it is used, so the same way can be used by two
questions on one page without them colliding.</p>

<form method="post" action="/newway">
<fieldset>
<legend>A new way to answer</legend>
<label for="w-name">What is it called?</label>
<input type="text" id="w-name" name="name" value="">
<label for="w-reads">How does it read?</label>
<input type="text" id="w-reads" name="reads" value="">
<p>What NVDA makes of it, in your words &mdash; so the list can be
judged by how it sounds rather than by what it is called.</p>
<label for="w-paste">The HTML</label>
<textarea id="w-paste" name="paste" rows="6"></textarea>
<p>It needs a box in it somewhere: an input, a textarea or a select.</p>
<button type="submit">Add this way</button>
</fieldset>
</form>

<p>All of this lives in <code>_ways.html</code> in your folder. You can
open it and change any of it by hand; nothing there is generated.</p>""")


def build(paste, field_id, question):
    """One question's worth of that way, as HTML for a page.

    Every id in what was pasted is given the question's name in front of
    it, and anything that pointed at one of those ids is repointed, so
    two questions using the same way cannot collide. The first box gets
    the name the saving side looks for. A label is always written here
    rather than taken from the paste, so that every question on a page
    is labelled the same way and none can arrive without one.
    """
    box_id = field_id + "-box"
    seen = {}

    def rename(m):
        was = m.group(1)
        seen[was] = box_id if not seen else field_id + "-" + was
        return 'id="' + html.escape(seen[was], quote=True) + '"'

    out = ID_RE.sub(rename, paste or "")

    def repoint(m):
        attr, was = m.group(1), m.group(2)
        return (attr + '="' + html.escape(seen.get(was, was), quote=True)
                + '"')

    out = REFERS_RE.sub(repoint, out)

    # The first box carries the name, because that is the one whose
    # value is saved. Any name already pasted in is replaced, not kept.
    m = CONTROL_RE.search(out)
    if m:
        end = out.index(">", m.start())
        head = NAME_ATTR_RE.sub("", out[m.start():end])
        # The value in an MDN example is sample data, not part of the
        # control. Left in, every entry of that kind would arrive
        # pre-filled with somebody's demonstration date.
        head = VALUE_ATTR_RE.sub("", head)
        if 'id="' not in head:
            head += ' id="' + html.escape(box_id, quote=True) + '"'
        head += ' name="set-' + html.escape(field_id, quote=True) + '"'
        out = out[:m.start()] + re.sub(r"\s{2,}", " ", head) + out[end:]

    return ('  <label for="%s">%s</label>\n  %s'
            % (html.escape(box_id, quote=True), html.escape(question),
               out.strip()))
