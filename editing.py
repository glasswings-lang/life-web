"""Changing words that are already on a page, without seeing any tags.

The rule this is built to: if you cannot get at it through the browser,
it does not exist. Opening a file in Notepad is not a way to fix a
sentence - not for someone who never learned HTML, and not for anyone
who would look at a page full of angle brackets and decide they are
going to break something.

So a page is offered back as its pieces. One paragraph, one heading,
one list at a time, each in a box holding your words and nothing else.
Change the words, press save, and only that piece is rewritten. The
worst thing that can go wrong is one wrong paragraph.

The catch, and how it is dealt with:

    A link on this page was made by pressing a button, not by typing
    anything. It lives in the file as markup you never wrote. Show the
    words alone in a box and save them back, and that link would
    quietly disappear - not losing anything you typed, but undoing what
    the button did for you.

    So links are put back. Every link already on a block is remembered
    before the box opens, and afterwards any whose words are still
    there is restored. Change the words and the link goes, which is
    right. Leave them and it survives, with nothing to remember and
    nothing to type.

Anything a block carries that plain words cannot say - a class, an id,
something unusual - means the plain box is not offered for it, and it
says so. Guessing there would lose things silently, which is the one
thing that must not happen.
"""

import html
import re

import markup

# What counts as a piece you can edit. Everything else on a page is
# either machinery or belongs to the whole page rather than a part.
BLOCK_RE = re.compile(
    r"<(p|h[1-6]|ul|ol|blockquote)\b([^>]*)>(.*?)</\1>", re.S | re.I)

# Never offered: the parts of the page that are not writing.
SKIP_RE = re.compile(
    r"<nav\b.*?</nav>|<form\b.*?</form>|<template\b.*?</template>"
    r"|<script\b.*?</script>|<style\b.*?</style>|<head\b.*?</head>",
    re.S | re.I)

LINK_RE = re.compile(r'<a\s[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.S | re.I)
DRESS_RE = re.compile(r"<(strong|em|code)\b[^>]*>(.*?)</\1>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")

# What can be taken off a block and put back on afterwards. Everything
# here survives the trip into a plain box and out again; anything else
# means the box is not offered, because the alternative is losing it
# without saying so.
KEEPABLE = {"a", "strong", "em", "code"}

# Structure the box can rebuild from the words themselves.
REBUILDABLE = {"p", "ul", "ol", "li", "blockquote", "br", "hr",
               "h2", "h3", "h4", "h5", "h6"}


def plain(fragment):
    return re.sub(r"\s+", " ",
                  html.unescape(TAG_RE.sub("", fragment or ""))).strip()


def blocks(text):
    """[(n, tag, attrs, inner, start, end), ...] - the pieces of a page.

    Positions are into the real text, so a block can be replaced without
    touching a byte of anything else.
    """
    hidden = SKIP_RE.sub(lambda m: " " * (m.end() - m.start()), text or "")
    out = []
    # The first level 1 heading is the page's own name, not writing. Any
    # other one was chosen from the Add page, and is a piece like the rest.
    title = True
    for m in BLOCK_RE.finditer(hidden):
        if m.group(1).lower() == "h1" and title:
            title = False
            continue
        if m.group(2).strip().startswith("class=\"when\""):
            continue                       # a timestamp, not writing
        if 'class="when"' in m.group(2):
            continue
        out.append((len(out), m.group(1).lower(), m.group(2),
                    text[m.start(3):m.end(3)], m.start(), m.end()))
    return out


def simple_enough(inner):
    """Whether everything in this block can survive the round trip.

    A block's OWN attributes are not the question - those are kept as
    they are, untouched. This is about what is inside it.
    """
    for m in re.finditer(r"<\s*/?\s*([a-zA-Z0-9]+)([^>]*)>", inner or ""):
        tag = m.group(1).lower()
        if tag not in KEEPABLE and tag not in REBUILDABLE:
            return False
        # href is the only attribute carried across, because a link is
        # put back afterwards. Anything else would vanish in silence.
        for a in re.finditer(r'([a-zA-Z-]+)\s*=', m.group(2)):
            if a.group(1).lower() != "href":
                return False
    return True


def as_words(inner):
    """A block as the words in it, with the tags taken off."""
    return plain(inner)


def dressing_of(inner):
    """[(words, what, href), ...] - the marks already on this block.

    Links, bold, italic and code, remembered by the words they sit on.
    None of these were typed by the writer - they were made by pressing
    something, or by a mark that has already been turned into markup -
    so losing them on a save would undo work rather than words.
    """
    out = [(plain(m.group(2)), "a", m.group(1))
           for m in LINK_RE.finditer(inner) if plain(m.group(2))]
    out += [(plain(m.group(2)), m.group(1).lower(), "")
            for m in DRESS_RE.finditer(inner) if plain(m.group(2))]
    return out


def put_back(rendered, remembered):
    """Restore marks whose words are still there.

    Longest words first, so that dressing a short phrase cannot get in
    the way of a longer one that contains it. Only outside tags, only
    once each, and never inside something already dressed.
    """
    for words, what, href in sorted(remembered, key=lambda r: -len(r[0])):
        needle = html.escape(words)
        if not needle:
            continue
        opener = ('<a href="' + html.escape(href, quote=True) + '">'
                  if what == "a" else "<" + what + ">")
        closer = "</a>" if what == "a" else "</" + what + ">"
        at = 0
        while True:
            found = rendered.find(needle, at)
            if found == -1:
                break
            before = rendered[:found]
            inside_tag = before.rfind("<") > before.rfind(">")
            already = (before.rfind(opener) > before.rfind(closer))
            if not inside_tag and not already:
                rendered = (rendered[:found] + opener + needle + closer
                            + rendered[found + len(needle):])
                break
            at = found + len(needle)
    return rendered


def rewrite(text, n, words, top=2):
    """Put new words into one block. Returns (new_text, trouble)."""
    found = blocks(text)
    if n < 0 or n >= len(found):
        return None, ("That piece is not on the page any more. It may have "
                      "been changed since this list was made.")
    _n, tag, attrs, inner, start, end = found[n]
    if not simple_enough(inner):
        return None, ("That piece has something in it that plain words "
                      "cannot carry, so it was left alone.")
    words = (words or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not words:
        return None, ("That would have left the piece empty, so nothing was "
                      "changed. Take it out with the whole-page editor if "
                      "that is what you meant.")

    if tag.startswith("h"):
        body = "<" + tag + attrs + ">" + markup.inline(
            html.escape(words).replace("\n", " ")) + "</" + tag + ">"
    else:
        body = markup.to_html(words, top)
        if len(found) and attrs.strip() and body.startswith("<p>"):
            body = "<p" + attrs + ">" + body[3:]

    body = put_back(body, dressing_of(inner))
    return text[:start] + body + text[end:], ""


def insert_after(text, n, words, top=2, kind="paragraph"):
    """Put new writing straight after one piece. Returns (new, trouble).

    This is what the marker in the file used to be for - choosing where
    something lands. Choosing it is now pressing a button beside the
    piece you want it to follow, which is a thing you can see. The
    marker stays as the default spot, and stops being anybody's problem.
    """
    found = blocks(text)
    if n < 0 or n >= len(found):
        return None, ("That piece is not on the page any more. It may have "
                      "been changed since this list was made.")
    words = (words or "").strip()
    if not words:
        return None, "Nothing was typed, so nothing was added."
    end = found[n][5]
    return (text[:end] + "\n" + markup.as_piece(words, kind, top)
            + text[end:], "")
