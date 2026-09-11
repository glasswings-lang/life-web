"""Turns what you typed into HTML, once, when you save it.

The note box takes plain typing, Markdown, HTML, or any mix of them. This
is what makes a blank line into a new paragraph, a line starting with ##
into a heading, and a <b> you typed into bold - so the shape of a page
can be built from the box, without opening the file.

It happens at save time and the RESULT is what goes in your file. Open
the page in Notepad afterwards and you find real HTML: <h2>, <p>, <ul>.
Not markdown waiting to be re-read by something. Nothing has to run for
the page to look right, and there is no second copy of your words in a
different format that could drift from the first.

The marks it knows, kept deliberately small, because every mark is a
thing you have to remember and a thing that can surprise you:

    ## words           a heading. The number of #s is its level, the way
                       Markdown means it: ## is 2, ### is 3, up to ######.
                       A single # is 2 as well - the page's own name is
                       the only level 1.
    - words            a list. 1. words is a numbered one.
    > words            a quote.
    **words**          bold.
    *words*            italic.
    `words`            code. Nothing inside is a mark or a tag.
    [words](page.html) a link.
    ---                a dividing line.
    a blank line       a new paragraph.
    a line break       stays a line break.

HTML you type is kept as real HTML: headings, paragraphs, lists, bold,
links, tables, and the rest of what writing uses. A heading typed in the
middle of a paragraph is lifted out of it, because a heading inside a
paragraph is broken HTML and sounds broken to a screen reader. An <h1>
becomes an <h2>, for the same reason a single # does.

Anything that would make the page DO something rather than SAY
something - a script, a style block, a frame, an onclick, a link that is
really an instruction - is left as the text you typed. It stays visible
rather than vanishing, so you can see it was not taken.

Underscores do NOT make italics. file_name_like_this is far commoner in
what you write than emphasis is, and having it silently eaten would be
worse than not having the mark.

[[flags]] pass through untouched. They are not a link yet; that is the
whole point of them.
"""

import html
import re

HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_RE = re.compile(r"^[-*+]\s+(.*)$")
NUMBER_RE = re.compile(r"^\d+[.)]\s+(.*)$")
QUOTE_RE = re.compile(r"^&gt;\s?(.*)$")           # after escaping, > is &gt;
RULE_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")

CODE_RE = re.compile(r"`([^`\n]+)`")
LINK_RE = re.compile(r"\[([^\[\]]+)\]\(([^()\s]+)\)")
BOLD_RE = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
ITALIC_RE = re.compile(r"\*(?=\S)([^*]+?)(?<=\S)\*")

HOLD = "\x00%d\x00"            # a code span, while other marks are looked for
TAG_HOLD = "\x01%d\x01"        # a tag you typed, kept aside until the end
TAG_HOLD_RE = re.compile("\x01(\\d+)\x01")

# What you typed that might be a tag. Code spans are found in the same pass
# so a tag you are quoting between backticks is never mistaken for one.
LIFT_RE = re.compile(r"`[^`\n]+`|<[^<>\n]*>")
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)(\s[^<>]*?)?\s*(/?)>")
ATTR_RE = re.compile(
    r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?""")

# Pieces of a page. A line starting with one of these is its own piece,
# never wrapped in a <p>.
BLOCK_TAGS = {"p", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
              "blockquote", "pre", "hr", "div", "table", "thead", "tbody",
              "tr", "th", "td", "dl", "dt", "dd", "figure", "figcaption"}
INLINE_TAGS = {"br", "strong", "b", "em", "i", "u", "s", "del", "ins",
               "code", "a", "span", "sup", "sub", "small", "mark", "abbr",
               "q", "cite", "kbd"}
VOID_TAGS = {"hr", "br"}
KEPT_TAGS = BLOCK_TAGS | INLINE_TAGS | {"h1"}
KEPT_ATTRS = {"class", "id", "title", "lang", "dir"}       # plus href, on a link


BAD_TARGET_RE = re.compile(r"^(javascript|data|vbscript):", re.I)


def safe_target(where):
    """Whether that is somewhere a link may point.

    Left as typed text if not. These pages are opened locally, by hand,
    with nothing running - a link is for getting to another page, and
    anything that is really an instruction to the browser is not that.
    Checked with entities decoded and spaces and control characters taken
    out, because a browser does both before deciding what a link is.
    A quote is refused because a target containing one is a typo, and
    a typo should stay visible rather than become a broken address.
    """
    if not where or "&quot;" in where or '"' in where:
        return False
    squeezed = re.sub(r"[\x00-\x20]+", "", html.unescape(where))
    return not BAD_TARGET_RE.match(squeezed)


def typed_tag(m):
    """The tag you typed, tidied, if it is one a page of writing uses.

    None means it is shown as the text you typed instead. A tag is only
    kept when every part of it is understood - one unknown attribute and
    the whole tag stays visible, rather than being quietly trimmed into
    something you did not write.
    """
    closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3) or ""
    if name not in KEPT_TAGS:
        return None
    if name == "h1":
        name = "h2"
    if closing:
        return None if attrs.strip() else "</" + name + ">"
    kept, at = [], 0
    for a in ATTR_RE.finditer(attrs):
        if attrs[at:a.start()].strip():
            return None
        at = a.end()
        key = a.group(1).lower()
        value = next((v for v in a.group(2, 3, 4) if v is not None), None)
        if key == "href" and name == "a":
            if value is None or not safe_target(value):
                return None
        elif key not in KEPT_ATTRS:
            return None
        kept.append(key if value is None
                    else key + '="' + html.escape(html.unescape(value), quote=True) + '"')
    if attrs[at:].strip():
        return None
    return "<" + name + "".join(" " + k for k in kept) + ">"


def lift(text, kept):
    """Everything escaped, except tags worth keeping, which are set aside.

    Escaping first is what makes it safe: nothing you type can become a
    tag unless it is on the short list and was written plainly.
    """
    out, last = [], 0
    for m in LIFT_RE.finditer(text):
        out.append(html.escape(text[last:m.start()]))
        chunk = m.group(0)
        tag = None if chunk.startswith("`") else TAG_RE.fullmatch(chunk)
        tidy = typed_tag(tag) if tag else None
        if tidy is None:
            out.append(html.escape(chunk))
        else:
            kept.append(tidy)
            out.append(TAG_HOLD % (len(kept) - 1))
        last = m.end()
    out.append(html.escape(text[last:]))
    text = "".join(out)

    # A piece of a page typed mid-line gets a line of its own, so it is
    # never wrapped inside a paragraph.
    def own_line(m):
        tag = kept[int(m.group(1))]
        name = re.match(r"</?([a-z0-9]+)", tag).group(1)
        if name not in BLOCK_TAGS or name == "li":
            return m.group(0)
        if tag.startswith("</") or name in VOID_TAGS:
            return m.group(0).strip(" \t") + "\n"
        return "\n" + m.group(0).strip(" \t")
    return re.sub(r"[ \t]*\x01(\d+)\x01[ \t]*", own_line, text)


def restore(text, kept):
    return TAG_HOLD_RE.sub(lambda m: kept[int(m.group(1))], text)


def inline(text):
    """The marks that happen inside a line.

    Code is lifted out first and put back last, so that a * or a # you
    are quoting stays exactly as you typed it.
    """
    stashed = []

    def stash(m):
        stashed.append("<code>" + m.group(1) + "</code>")
        return HOLD % (len(stashed) - 1)

    text = CODE_RE.sub(stash, text)
    text = LINK_RE.sub(
        lambda m: ('<a href="' + m.group(2) + '">' + m.group(1) + "</a>"
                   if safe_target(m.group(2)) else m.group(0)), text)
    text = BOLD_RE.sub(lambda m: "<strong>" + m.group(1) + "</strong>", text)
    text = ITALIC_RE.sub(lambda m: "<em>" + m.group(1) + "</em>", text)
    for n, code in enumerate(stashed):
        text = text.replace(HOLD % n, code)
    return text


def _list(lines, kind, pattern):
    out = ["<" + kind + ">"]
    for line in lines:
        m = pattern.match(line)
        out.append("<li>" + inline(m.group(1) if m else line) + "</li>")
    out.append("</" + kind + ">")
    return "\n".join(out)


def _block(lines, top):
    """One run of non-blank lines, as one piece of HTML."""
    first = lines[0]

    if len(lines) == 1 and RULE_RE.match(first.strip()):
        return "<hr>"

    m = HEAD_RE.match(first)
    if m:
        # The number of #s is the level, the way Markdown means it. Only a
        # single # is moved: the page already has its <h1>, its own name,
        # and two <h1>s make heading navigation lie about the page's shape.
        level = max(len(m.group(1)), 2)
        rest = _block(lines[1:], top) if len(lines) > 1 else ""
        tag = "h%d" % level
        return ("<" + tag + ">" + inline(m.group(2).rstrip("#").strip())
                + "</" + tag + ">" + ("\n" + rest if rest else ""))

    if BULLET_RE.match(first):
        return _list(lines, "ul", BULLET_RE)
    if NUMBER_RE.match(first):
        return _list(lines, "ol", NUMBER_RE)
    if QUOTE_RE.match(first):
        inner = [QUOTE_RE.match(l).group(1) if QUOTE_RE.match(l) else l
                 for l in lines]
        return ("<blockquote>\n<p>" + inline("<br>\n".join(inner))
                + "</p>\n</blockquote>")

    # A line break you typed is kept. Typing is not an essay being
    # reflowed; if you pressed Enter, you meant it.
    return "<p>" + inline("<br>\n".join(lines)) + "</p>"


def _typed_piece(line, kept):
    """(tag name, closing?) if this line starts with a typed piece of page."""
    m = TAG_HOLD_RE.match(line)
    if not m:
        return None
    tag = re.match(r"<(/?)([a-z0-9]+)", kept[int(m.group(1))])
    if tag.group(2) not in BLOCK_TAGS:
        return None
    return tag.group(2), bool(tag.group(1))


def _closed(chunk, name, kept):
    written = restore("\n".join(chunk), kept)
    opens = len(re.findall(r"<" + name + r"\b", written))
    return written.count("</" + name + ">") >= opens


def to_html(text, top=2):
    """Everything you typed, as blocks of HTML.

    `top` is kept so callers need not change, but a heading's level now
    comes from its #s alone - see _block.
    """
    kept = []
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = lift(text, kept).split("\n")
    out, run, i = [], [], 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            if run:
                out.append(_block(run, top))
                run = []
            i += 1
            continue
        piece = _typed_piece(line.strip(), kept)
        if piece:
            if run:
                out.append(_block(run, top))
                run = []
            name, closing = piece
            chunk = [line.strip()]
            i += 1
            if not closing and name not in VOID_TAGS:
                # A typed piece runs until its own closing tag, however many
                # lines that takes - a <ul> of items is one piece, not six.
                while i < len(lines) and not _closed(chunk, name, kept):
                    chunk.append(lines[i].rstrip())
                    i += 1
            out.append(inline("\n".join(chunk)))
            continue
        run.append(line)
        i += 1
    if run:
        out.append(_block(run, top))
    return restore("\n".join(out), kept)


HEADING_TAG_RE = re.compile(r"<h([1-6])\b", re.I)


def level_at(page_text, marker):
    """Which heading level sits just above this spot in this page.

    Headings typed in the box no longer use this - their #s decide - but
    it still answers the question for anything that asks where writing
    lands relative to the page's own headings.
    """
    at = page_text.find(marker) if marker else -1
    before = page_text[:at] if at != -1 else (page_text or "")
    found = HEADING_TAG_RE.findall(before)
    return min(int(found[-1]) + 1, 6) if found else 2
