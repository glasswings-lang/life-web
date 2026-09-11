"""Pages, links inside sentences, and finding things.

The three things a wiki is, and none of them go through a kind.

  a page        prose and a box to add more prose. Nothing else is
                required of it. No questions, no shape, no folder it
                has to belong to.

  a flag        [[words]] typed mid-sentence means SOMETHING GOES HERE,
                sort it later. Nothing to spell, nothing to get wrong,
                and it never stops you writing. The flagged list turns
                one into a real link afterwards, and the words on the
                page stay the words you wrote.

  finding       reads every page every time you ask. No index to build,
                nothing to go stale, and a typo fixed in Notepad is
                findable a second later.

Kinds still work and are untouched. They are one shape a page can take,
for the rare thing that really is the same questions over and over.
They are no longer the way in.
"""

import html
import re
from urllib.parse import quote

import editing
import links

# [[like this]]. No nesting, no brackets inside.
FLAG_RE = re.compile(r"\[\[([^\[\]\n]+)\]\]")

# Blanked out before looking for flags, keeping every position the same.
# A comment that MENTIONS a flag is not a flag, and neither is one in a
# template - which is not rendered and not read out by anything.
# A textarea is where you TYPE a flag, not where one lives. Saving a
# field writes its text into two places - the bit that displays it and
# the box you edit it in - so a flag put in a field would otherwise be
# counted twice, and "resolving" the copy in the box would push <a href>
# markup into an edit box, where it would show as literal angle
# brackets. Both happened.
MASK_RE = re.compile(
    r"<!--.*?-->|<template[^>]*>.*?</template>"
    r"|<textarea[^>]*>.*?</textarea>"
    r"|<script.*?</script>|<style.*?</style>", re.S | re.I)

BOX_RE = re.compile(r"(<textarea[^>]*>)(.*?)(</textarea>)", re.S | re.I)


# Searching looks at prose only. Without this every page matches on the
# words in its own nav and its own Save box, and every result reads the
# same - which is a search that technically works and is no use.
# Dropping the whole <form> was too big a swing. The thing worth losing
# is the machinery - a Save button, a label, the options in a combo box -
# because without that every page matches on the words in its own form
# and every result reads the same. But an answer's shown paragraph lives
# inside the Details form, so taking the form wholesale took the answers
# with it: a term could be found by its name and never by a word of what
# it said. The controls go; prose inside a form stays.
FURNITURE_RE = re.compile(
    r"<head[^>]*>.*?</head>|<nav[^>]*>.*?</nav>"
    r"|<label[^>]*>.*?</label>|<button[^>]*>.*?</button>"
    r"|<legend[^>]*>.*?</legend>|<option[^>]*>.*?</option>"
    r"|<select[^>]*>.*?</select>|<input[^>]*>"
    r"|<form[^>]*>|</form>|<fieldset[^>]*>|</fieldset>",
    re.S | re.I)


def blank(m):
    return " " * (m.end() - m.start())


def masked(text):
    return MASK_RE.sub(blank, text)


def prose(text):
    """Just what was written, with the page's own machinery taken out."""
    return FURNITURE_RE.sub(blank, MASK_RE.sub(blank, text))


def in_tag(text, at):
    """True if this spot is inside a < >, where prose never is."""
    return text.rfind("<", 0, at) > text.rfind(">", 0, at)


def flags_in(text):
    """[(words, start, end), ...] - every flag in real prose."""
    hidden = masked(text)
    return [(m.group(1).strip(), m.start(), m.end())
            for m in FLAG_RE.finditer(hidden) if not in_tag(hidden, m.start())]


def flags(root):
    """[(page, words, sentence), ...] - every loose flag in the folder."""
    out = []
    for page_rel in links.pages(root):
        text = links._read(root / page_rel)
        if text is None:
            continue
        for words, start, _end in flags_in(text):
            out.append((page_rel, words, links.sentence_of(text, start)))
    return out


def unbracket_boxes(text, words):
    """Take the brackets off the same flag where it sits in an edit box.

    A field's text is kept in two places. Link the one on show and leave
    the box alone, and they disagree - and the next press of Save copies
    the box over the top, taking the new link with it. So the box keeps
    the words and loses the brackets: it can't hold a link, but it must
    not hold a flag that has already been dealt with.
    """
    flag = "[[" + words + "]]"
    esc = html.escape(flag)

    def one(m):
        inner = m.group(2).replace(flag, words).replace(esc,
                                                        html.escape(words))
        return m.group(1) + inner + m.group(3)

    return BOX_RE.sub(one, text)


def resolve(root, page_rel, words, target_rel, read, write):
    """Turn one flag into a real link. The words stay the writer's."""
    text = read(root / page_rel)
    if text is None:
        return "That page could not be read."
    if not (root / target_rel).is_file():
        return "There is no page at " + target_rel + "."
    flag = "[[" + words + "]]"
    for got, start, end in flags_in(text):
        if got != words:
            continue
        link = ('<a href="' + html.escape(
            links.address_from(page_rel, target_rel), quote=True) + '">'
            + html.escape(words) + "</a>")
        new = unbracket_boxes(text[:start] + link + text[end:], words)
        if not write(root / page_rel, new):
            return "That page could not be written to."
        return ""
    return ("There is no " + flag + " in " + page_rel + " any more. It may "
            "have been changed since this list was made.")


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{up}style.css">
</head>
<body>

<h1>{title}</h1>

<nav>
<a href="{up}index.html">Back to the top</a>
</nav>

<!-- here -->

<template>
<div class="addition">
<p class="when">{{when}}</p>
<p>{{note}}</p>
</div>
</template>

</body>
</html>
"""


STARTER = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Everything</title>
<link rel="stylesheet" href="style.css">
</head>
<body>

<h1>Everything</h1>

<p>This is your page. Gut it, rewrite it, put what you like on it. The
program only ever fills in the list below and leaves the rest alone.</p>

<h2>Waiting</h2>

<ul id="tidy">
</ul>

<h2>Make a new page</h2>

<form method="post" action="/newpage">
  <label for="np-name">What is it called?</label>
  <input type="text" id="np-name" name="name">
  <label for="np-where">Which folder (leave empty for the top)</label>
  <input type="text" id="np-where" name="where" value="">
  <button type="submit">Make the page</button>
</form>

<h2>Kinds of thing</h2>

<p>For anything that really is the same questions over and over. Most
things are not, and do not need one.</p>

<ul>
<!-- kinds -->
</ul>

<h2>Make a new kind</h2>

<form method="post" action="/newkind">
  <label for="kindname">What is this kind of thing called?</label>
  <input type="text" id="kindname" name="name">
  <button type="submit">Make the kind</button>
</form>

</body>
</html>
"""


STYLE = """html { color-scheme: light dark; }
body { max-width: 35em; margin: 0 auto; padding: 0 1rem 4rem;
       font-family: Tahoma, Verdana, Arial, sans-serif; line-height: 1.5; }
nav a { margin-right: 1rem; }
.count { opacity: 0.8; font-size: 0.9rem; }
.addition { border-left: 3px solid; padding-left: 0.8em; margin: 1.2em 0; }
.addition .when { opacity: 0.7; font-size: 0.9rem; margin: 0 0 0.3em; }
label { display: block; font-weight: bold; margin-top: 0.8rem; }
textarea, input[type=text], input[type=number], input[type=date], select {
  font: inherit; padding: 0.4rem; box-sizing: border-box; }
textarea, input[type=text] { width: 100%; }
button { font: inherit; padding: 0.4rem 1rem; margin-top: 0.6rem; }
"""


def ensure_style(root, write):
    """Put the stylesheet there if it is not, and never touch one that
    is. Every page this program writes asks for style.css, so a folder
    without one shows unstyled pages and nothing says why. Yours is
    yours the moment it exists: this only ever fills an absence.
    """
    style = root / "style.css"
    if not style.exists():
        write(style, STYLE)


def make_page_at(root, rel, title, write):
    """A page at an address somebody asked for, rather than one worked
    out from a name. Returns "" or what went wrong.

    make_page turns a name into a filename. This is the other way round:
    a link already exists, it points here, and the page it wants does
    not. Slugging the name would sometimes land somewhere else and leave
    the link still broken, which is the one thing this must not do.

    The top page is a special case. Somebody arriving at an empty folder
    has nothing to look at and nowhere to start, so index.html is made
    as a working front page rather than a blank one, and the stylesheet
    every page asks for is written beside it if it is not there.
    """
    if rel.startswith("_") or ".." in rel or chr(92) in rel:
        return "That is not an address a page can be made at."
    if not rel.lower().endswith((".html", ".htm")):
        return "A page has to end in .html."
    spot = root / rel
    if spot.exists():
        return "There is already a page at " + rel + "."
    spot.parent.mkdir(parents=True, exist_ok=True)

    if rel == "index.html":
        if not write(spot, STARTER):
            return "That page could not be written."
        ensure_style(root, write)
        return ""

    up = "../" * rel.count("/")
    if not write(spot, PAGE.format(title=html.escape(title or rel),
                                   up=up,
                                   to=html.escape(rel, quote=True))):
        return "That page could not be written."
    ensure_style(root, write)
    return ""


def make_page(root, name, where, slug, write):
    """A page. Prose and a box. Returns (path, trouble)."""
    name = " ".join(name.split())
    if not name:
        return None, "That page had no name."
    stem = slug(name)
    if not stem:
        return None, "That name had no letters or numbers in it."
    where = (where or "").strip().strip("/")
    if where and (".." in where or "\\" in where):
        return None, "That folder cannot be used."
    rel = (where + "/" + stem + ".html") if where else stem + ".html"
    spot = root / rel
    if spot.exists():
        return rel, "There is already a page at " + rel + "."
    up = "../" * rel.count("/")
    spot.parent.mkdir(parents=True, exist_ok=True)
    if not write(spot, PAGE.format(title=html.escape(name), up=up,
                                   to=html.escape(rel, quote=True))):
        return None, "That page could not be written."
    ensure_style(root, write)
    return rel, ""


TOOLS = ('<a href="/search">Find something</a>\n'
         '<a href="/flags">Loose ends</a>')

EDIT_LINK = ('<a href="/add?page={rel}">Add to this page</a>\n'
             '<a href="/edit?page={rel}">Edit this page</a>\n'
             '<a href="/here?page={rel}">What links here</a>')

NAV_END_RE = re.compile(r"(</nav>)", re.I)
H1_END_RE = re.compile(r"(</h1>)", re.I)
BODY_RE = re.compile(r"(<body\b[^>]*>)", re.I)


def with_tools(text, rel=""):
    """Put the tool links on a page as it is served, never in the file.

    They are addresses only this program answers, so writing them into
    a page makes that page depend on the program being up. Every file
    here is meant to still work with nothing running - and to still
    work if the folder is put somewhere else entirely - so these live
    for exactly as long as the page is on its way to the browser.

    After the <h1>, not before it: the first thing a page should say
    is what page it is, not where else you could go.
    """
    if not text or "\x3ca href=\"/search\"" in text:
        return text
    # The edit link needs to know which page it is on, so it is only
    # offered when the page's own address is known - which is whenever
    # a real file is being served.
    tools = TOOLS
    if rel:
        tools += "\n" + EDIT_LINK.format(
            rel=html.escape(quote(rel), quote=True))
    # At the END of an existing nav, not the start. The links a page
    # already had are the ones about where you are - back to the
    # section, back to the top. Those should be read first; these are
    # for going somewhere else entirely.
    m = NAV_END_RE.search(text)
    if m:
        return text[:m.start()] + tools + "\n" + text[m.start():]
    m = H1_END_RE.search(text) or BODY_RE.search(text)
    if not m:
        return text
    return (text[:m.end()] + "\n<nav>\n" + tools + "\n</nav>"
            + text[m.end():])


def pieces_page(root, page_rel, said=""):
    """The page as its pieces, each in a box holding only words.

    No tags anywhere on this page. Anything that could not survive being
    shown as plain words is listed but not offered, and says why, so
    nothing is ever lost quietly.
    """
    text = links._read(root / page_rel)
    if text is None:
        return frame("Cannot edit that", "<p>There is no page at "
                     + html.escape(page_rel) + ".</p>")
    parts = []
    if said:
        parts.append('<p id="said">' + html.escape(said) + "</p>")
    found = editing.blocks(text)
    parts.append("<p>Every piece of " + html.escape(page_rel)
                 + " is below. Change the words in any box and press the "
                 "button under it. Nothing else on the page is touched.</p>")
    if not found:
        parts.append("<p>There is nothing written on this page yet.</p>")
    for n, tag, _attrs, inner, _s, _e in found:
        me = "piece" + str(n)
        what = "Heading" if tag.startswith("h") else (
            "List" if tag in ("ul", "ol") else "Paragraph")
        if not editing.simple_enough(inner):
            parts.append(
                "<h2>" + what + "</h2>\n<p>"
                + html.escape(editing.as_words(inner)) + "</p>\n"
                "<p>This one has something in it that plain words cannot "
                "carry, so changing it here would lose that. Use the "
                'whole-page editor for it: <a href="/edit?page='
                + html.escape(quote(page_rel), quote=True)
                + '&amp;raw=1">show the page as it really is</a>.</p>')
            continue
        parts.append(
            '<form method="post" action="/editpiece">\n'
            "<h2>" + what + "</h2>\n"
            '<input type="hidden" name="page" value="'
            + html.escape(page_rel, quote=True) + '">\n'
            '<input type="hidden" name="n" value="' + str(n) + '">\n'
            '<label for="' + me + '">The words</label>\n'
            '<textarea id="' + me + '" name="words" rows="4">'
            + html.escape(editing.as_words(inner)) + "</textarea>\n"
            '<button type="submit">Save this piece</button>\n</form>\n'
            '<p><a href="/add?page='
            + html.escape(quote(page_rel), quote=True) + '&amp;after='
            + str(n) + '">Add something after this piece</a></p>')
    parts.append('<h2>Other ways in</h2>\n<ul>\n'
                 '<li><a href="/add?page='
                 + html.escape(quote(page_rel), quote=True)
                 + '">Add something new to this page</a></li>\n'
                 '<li><a href="/edit?page='
                 + html.escape(quote(page_rel), quote=True)
                 + '&amp;raw=1">Show the page as it really is</a> '
                 "&mdash; the whole file, tags and all.</li>\n"
                 '<li><a href="/here?page='
                 + html.escape(quote(page_rel), quote=True)
                 + '">What links to this page, and what it links to</a>'
                 "</li>\n"
                 '<li><a href="/remove?page='
                 + html.escape(quote(page_rel), quote=True)
                 + '">Put this page away</a></li>\n'
                 '<li><a href="/' + html.escape(quote(page_rel), quote=True)
                 + '">Back to the page itself</a></li>\n</ul>')
    return frame("Editing " + html.escape(page_rel), "\n\n".join(parts))


def add_page(root, page_rel, said="", after=None):
    """The box that adds something new, on its own page.

    It used to sit on every page, which made every page read like a
    draft - and would have shown a visitor a dead box if the folder
    were ever put online. It is a thing you go to, now.
    """
    text = links._read(root / page_rel)
    if text is None:
        return frame("Cannot add to that", "<p>There is no page at "
                     + html.escape(page_rel) + ".</p>")
    parts = []
    if said:
        parts.append('<p id="said">' + html.escape(said) + "</p>")
    if "<!-- here -->" not in text:
        return frame("Nowhere to put it yet", "\n".join(parts) + '''
<p>This page has no spot marked for new writing, so there is nowhere to
put it. That is a one-off: press the button and one is added at the end
of the page, and after that this page takes writing like any other.</p>
<form method="post" action="/makewritable">
<input type="hidden" name="page" value="'''
            + html.escape(page_rel, quote=True) + '''">
<button type="submit">Make this page writable</button>
</form>''')
    parts.append(
        "<p>This will go "
        + ("at the end of the page, with today's date on it."
           if after is None else
           "straight after the piece you picked, as ordinary writing.")
        + "</p>")
    parts.append(
        '<form method="post" action="'
        + ("/save" if after is None else "/addafter") + '">\n'
        '<input type="hidden" name="page" value="'
        + html.escape(page_rel, quote=True) + '">\n'
        + ('<input type="hidden" name="n" value="' + str(after) + '">\n'
           if after is not None else "")
        + '<input type="hidden" name="_to" value="'
        + html.escape(page_rel, quote=True) + '">\n'
        '<input type="hidden" name="_back" value="/'
        + html.escape(page_rel, quote=True) + '">\n'
        '<label for="note-box">What do you want to say?</label>\n'
        '<textarea id="note-box" name="note" rows="10"></textarea>\n'
        "<p>Put &#91;&#91;double brackets&#93;&#93; round anything you want "
        "to link later. It stays visible until you deal with it, on the "
        "Loose ends page.</p>\n"
        '<button type="submit">Add it</button>\n</form>')
    parts.append('<p><a href="/' + html.escape(quote(page_rel), quote=True)
                 + '">Back to the page without adding anything</a></p>')
    return frame("Adding to " + html.escape(page_rel), "\n\n".join(parts))


def make_writable(root, page_rel, read, write):
    """Put a spot for new writing at the end of a page that has none."""
    path = root / page_rel
    text = read(path)
    if text is None:
        return "There is no page at " + page_rel + "."
    if "<!-- here -->" in text:
        return ""
    m = re.search(r"</body>", text, re.I)
    spot = m.start() if m else len(text)
    new = text[:spot] + "\n<!-- here -->\n" + text[spot:]
    if not write(path, new):
        return "That page could not be written to."
    return ""


def here_page(root, page_rel, said=""):
    """What points at this page, and what this page points at.

    A page you press rather than a list that grows on every page whether
    you wanted it or there or not. Both directions in one place, because
    the question "what is this connected to" does not care which way the
    arrow runs.
    """
    every = [(p, links.title_of(root, p) + "  -  " + p)
             for p in links.pages(root)]
    parts = []
    if said:
        parts.append('<p id="said">' + html.escape(said) + "</p>")

    coming = links.points_at(root, page_rel)
    parts.append("<h2>What points here</h2>")
    if not coming:
        parts.append("<p>Nothing links to this page yet.</p>")
    for where, title, words, sentence in coming:
        parts.append('<p><a href="/' + html.escape(quote(where), quote=True)
                     + '">' + html.escape(title) + "</a> &mdash; on the "
                     "words " + html.escape(words) + "</p>\n<p>"
                     + html.escape(sentence) + "</p>")

    going = links.links_on(root, page_rel)
    parts.append("<h2>What this page points at</h2>")
    if not going:
        parts.append("<p>This page has no links on it.</p>")
    for n, (addr, words, target, sentence) in enumerate(going, 1):
        me = "to" + str(n)
        where = ("nothing - there is no file there" if target is None
                 or not (root / target).exists()
                 else links.title_of(root, target))
        parts.append(
            '<form method="post" action="/relink">\n<fieldset>\n<legend>'
            + html.escape(words or addr) + "</legend>\n"
            '<input type="hidden" name="page" value="'
            + html.escape(page_rel, quote=True) + '">\n'
            '<input type="hidden" name="addr" value="'
            + html.escape(addr, quote=True) + '">\n'
            '<input type="hidden" name="words" value="'
            + html.escape(words, quote=True) + '">\n'
            "<p>" + html.escape(sentence) + "</p>\n"
            "<p>It goes to " + html.escape(where) + ".</p>\n"
            '<label for="' + me + '">Point it somewhere else</label>\n'
            '<select id="' + me + '" name="target">\n'
            '<option value="">(leave it alone)</option>\n'
            + links._options(every) + "\n</select>\n"
            '<button type="submit" name="do" value="point">Point it '
            "there</button>\n"
            '<button type="submit" name="do" value="unlink">Take the link '
            "off and keep the words</button>\n"
            "</fieldset>\n</form>")

    parts.append('<p><a href="/' + html.escape(quote(page_rel), quote=True)
                 + '">Back to the page itself</a></p>')
    return frame("What links to " + html.escape(page_rel),
                 "\n\n".join(parts))


def remove_page(root, page_rel, said=""):
    """Ask before putting a page away, and show what it would break."""
    coming = links.points_at(root, page_rel)
    warn = ""
    if coming:
        warn = ("<p>" + str(len(coming))
                + (" link points" if len(coming) == 1 else " links point")
                + " at this page. Putting it away will leave "
                + ("that one" if len(coming) == 1 else "them")
                + " going nowhere, and "
                + ("it" if len(coming) == 1 else "they")
                + " will turn up on the Loose ends page:</p>\n<ul>"
                + "".join("<li>" + html.escape(t) + " &mdash; on the words "
                          + html.escape(w) + "</li>"
                          for _p, t, w, _s in coming) + "</ul>")
    else:
        warn = "<p>Nothing links to this page, so nothing will break.</p>"
    return frame(
        "Putting away " + html.escape(page_rel),
        ('<p id="said">' + html.escape(said) + "</p>" if said else "")
        + warn + '''

<p>Nothing is destroyed. The page is moved into <code>_deleted</code>,
which is not served, not searched and not in any list. Getting it back
is moving it out again by hand.</p>

<form method="post" action="/removepage">
<input type="hidden" name="page" value="'''
        + html.escape(page_rel, quote=True) + '''">
<button type="submit">Put this page away</button>
</form>

<p><a href="/''' + html.escape(quote(page_rel), quote=True)
        + '">Leave it where it is</a></p>')


def edit_page(root, page_rel, said=""):
    """The page, as it really is, in a box you can change.

    Not a rich editor and not a converted-back version of anything. The
    file IS the record, so what you get is the file - the same bytes you
    would see in Notepad - and what you save is what you typed. Nothing
    is translated in either direction, so nothing can be lost in the
    translation.

    Markdown belongs in the box that ADDS to a page, where there is
    nothing to preserve. Turning existing HTML back into markdown to
    show it here would be a guess, and it would quietly flatten
    anything you had hand-written.
    """
    text = links._read(root / page_rel)
    if text is None:
        return frame("Cannot edit that",
                     "<p>There is no page at "
                     + html.escape(page_rel) + ".</p>")
    kept = (root / (page_rel + ".bak")).exists()
    parts = []
    if said:
        parts.append('<p id="said">' + html.escape(said) + "</p>")
    parts.append(
        "<p>This is " + html.escape(page_rel) + " exactly as it is on "
        "disk. Change any part of it and press Save. What you type is "
        "what the file becomes.</p>\n"
        '<form method="post" action="/editsave">\n'
        '<input type="hidden" name="page" value="'
        + html.escape(page_rel, quote=True) + '">\n'
        '<label for="page-box">The page</label>\n'
        '<textarea id="page-box" name="text" rows="30" cols="80">'
        + html.escape(text) + "</textarea>\n"
        "<p>The version before your last save is kept beside it as "
        + html.escape(page_rel) + ".bak, so one step back is always "
        "possible.</p>\n"
        '<button type="submit">Save the page</button>\n</form>')
    if kept:
        parts.append('<h2>Put it back</h2>\n<p>There is a saved previous '
                     'version of this page.</p>\n'
                     '<form method="post" action="/editundo">\n'
                     '<input type="hidden" name="page" value="'
                     + html.escape(page_rel, quote=True) + '">\n'
                     '<button type="submit">Go back to the previous '
                     'version</button>\n</form>')
    parts.append('<p><a href="/' + html.escape(quote(page_rel), quote=True)
                 + '">Back to the page itself</a></p>')
    return frame("Editing " + html.escape(page_rel), "\n\n".join(parts))


def save_edit(root, page_rel, text, read, write):
    """Write the box back into the file, keeping one step of undo."""
    path = root / page_rel
    if not path.is_file():
        return "There is no page at " + page_rel + "."
    before = read(path)
    if before is None:
        return "That page could not be read, so it was not written to."
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return ("That would have emptied the page completely, so nothing "
                "was saved. Delete the file yourself if that is what you "
                "meant.")
    if not write(root / (page_rel + ".bak"), before):
        return "The previous version could not be kept, so nothing was saved."
    if not write(path, text):
        return "That page could not be written to."
    return ""


def undo_edit(root, page_rel, read, write):
    """Swap the page and its kept previous version."""
    path, kept = root / page_rel, root / (page_rel + ".bak")
    if not kept.is_file():
        return "There is no previous version of " + page_rel + " kept."
    old, now = read(kept), read(path)
    if old is None or now is None:
        return "Those could not be read, so nothing was changed."
    if not write(kept, now) or not write(path, old):
        return "That page could not be written to."
    return ""


def frame(title, inside):
    return ('<!doctype html>\n<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, '
            'initial-scale=1">\n<title>' + title + "</title>\n"
            '<link rel="stylesheet" href="/style.css">\n</head>\n<body>\n'
            "<h1>" + title + "</h1>\n"
            '<nav>\n<a href="/index.html">Back to the top</a>\n'
            '<a href="/search">Find something</a>\n'
            '<a href="/flags">Loose ends</a>\n'
            '<a href="/repairs">Repairs</a>\n</nav>\n\n'
            + inside + "\n</body>\n</html>\n")


def new_page_form(where=""):
    return ('<h2>Make a new page</h2>\n'
            '<form method="post" action="/newpage">\n<fieldset>\n'
            "<legend>A new page</legend>\n"
            '<label for="np-name">What is it called?</label>\n'
            '<input type="text" id="np-name" name="name" value="">\n'
            '<label for="np-where">Which folder (leave empty for the '
            'top)</label>\n'
            '<input type="text" id="np-where" name="where" value="'
            + html.escape(where, quote=True) + '">\n'
            "<p>It will be prose and a box to add more. No questions, "
            "nothing to fill in.</p>\n"
            '<button type="submit">Make the page</button>\n'
            "</fieldset>\n</form>")


def search_page(root, query):
    found = hits(root, query)
    box = ('<form method="get" action="/search">\n'
           '<label for="q">Words to look for</label>\n'
           '<input type="search" id="q" name="q" value="'
           + html.escape(query, quote=True) + '">\n'
           '<button type="submit">Find them</button>\n</form>')
    if not query:
        head = ("<p>Every page, " + str(len(found)) + " of them. Type "
                "something above to narrow it down. Every page is read "
                "each time you ask, so nothing here can be out of date.</p>")
    elif found:
        head = ("<p>" + str(len(found)) + (" page has" if len(found) == 1
                else " pages have") + " those words in.</p>")
    else:
        head = ("<p>Nothing has those words in it. Nothing is hidden - "
                "this read every page in the folder just now.</p>")
    rows = []
    for page_rel, title, lines in found:
        rows.append('<h3><a href="/' + html.escape(page_rel, quote=True)
                    + '">' + html.escape(title) + "</a></h3>\n<p>"
                    + html.escape(page_rel) + "</p>"
                    + "".join("\n<p>&hellip;" + html.escape(ln)
                              + "&hellip;</p>" for ln in lines))
    return frame("Find something",
                 box + "\n\n" + head + "\n\n" + "\n\n".join(rows)
                 + "\n\n" + new_page_form())


def fill_tidy(page_text, root):
    """Fill <ul id="tidy"> with whatever is waiting, when the page loads.

    Repairs, the flagged list and Find were reachable only by typing
    their addresses. Nothing on disk linked to any of them, so a flag
    could sit waiting for as long as you like and the page you actually
    look at would never mention it. Knowing where to look is not a
    feature; it is a thing you have to be told once and then remember,
    which is the shape this program is supposed to avoid.

    Counted when the page is served and never stored, the same as combo
    boxes and "what points here", so there is no second copy to go
    stale and no rebuild step. The list says nothing about a thing with
    nothing in it: an empty Repairs is not news.
    """
    def one(m):
        rows = []
        ends = len(links.loose_ends(root))
        if ends:
            rows.append('<li><a href="/repairs">Repairs</a> &mdash; %d link%s '
                        "%s nowhere.</li>"
                        % (ends, "" if ends == 1 else "s",
                           "goes" if ends == 1 else "go"))
        waiting = len(flags(root))
        if waiting:
            rows.append('<li><a href="/flags">Flagged</a> &mdash; %d thing%s '
                        "waiting to be pointed at a page.</li>"
                        % (waiting, "" if waiting == 1 else "s"))
        rows.append('<li><a href="/search">Find something</a> by any word '
                    "in it.</li>")
        return m.group(1) + chr(10) + chr(10).join(rows) + chr(10) + "</ul>"

    return re.sub(r'(<ul[^>]*\bid="tidy"[^>]*>).*?</ul>',
                  one, page_text, flags=re.S | re.I)


def flags_page(root, said=""):
    loose = flags(root)
    every = [(p, links.title_of(root, p) + "  -  " + p)
             for p in links.pages(root)]
    parts = []
    if said:
        parts.append('<p id="said">' + html.escape(said) + "</p>")
    if not loose:
        parts.append("<p>Nothing is flagged. Write [[double brackets]] "
                     "round anything mid-sentence and it turns up here.</p>")
    else:
        parts.append("<p>" + str(len(loose)) + (" flag is" if len(loose) == 1
                     else " flags are") + " waiting. Each one shows the "
                     "sentence you wrote it in. Point it at a page, or make "
                     "a new page for it - the words on your page stay "
                     "exactly as you typed them either way.</p>")
    for n, (page_rel, words, sentence) in enumerate(loose, 1):
        me = "flag" + str(n)
        parts.append(
            '<form method="post" action="/resolveflag">\n<fieldset>\n'
            "<legend>" + html.escape(words) + ", in "
            + html.escape(page_rel) + "</legend>\n"
            '<input type="hidden" name="page" value="'
            + html.escape(page_rel, quote=True) + '">\n'
            '<input type="hidden" name="words" value="'
            + html.escape(words, quote=True) + '">\n'
            "<p>" + html.escape(sentence) + "</p>\n"
            '<label for="' + me + '">Link it to</label>\n'
            '<select id="' + me + '" name="target">\n'
            '<option value="">(choose a page)</option>\n'
            + links._options(every) + "\n</select>\n"
            '<label for="' + me + '-new">or a new page called</label>\n'
            '<input type="text" id="' + me + '-new" name="newpage" value="'
            + html.escape(words, quote=True) + '">\n'
            "<p>Pressing this puts a link on the words "
            + html.escape(words) + " and takes the brackets off. The "
            "sentence is not otherwise touched.</p>\n"
            '<button type="submit">Link it</button>\n'
            "</fieldset>\n</form>")
    return frame("Loose ends", "\n\n".join(parts) + "\n\n" + new_page_form())


def hits(root, query, most=200):
    """[(page, title, [line, ...]), ...] - every page holding those words.

    Read off disk each time. The whole folder is a few hundred small
    files, which is nothing to read, and it means there is no index
    anywhere that can disagree with what is actually written.
    """
    want = " ".join(query.split()).lower()
    out = []
    for page_rel in links.pages(root):
        text = links._read(root / page_rel)
        if text is None:
            continue
        flat = links.plain(prose(text))
        if not want:
            out.append((page_rel, links.title_of(root, page_rel), []))
            continue
        low = flat.lower()
        at, lines = low.find(want), []
        while at != -1 and len(lines) < 3:
            lines.append(flat[max(0, at - 90):at + len(want) + 90].strip())
            at = low.find(want, at + len(want))
        if lines:
            out.append((page_rel, links.title_of(root, page_rel), lines))
        if len(out) >= most:
            break
    return out
