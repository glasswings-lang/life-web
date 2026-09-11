"""Keeping links working when files move.

A link in these pages is a real relative address - ../places/x.html -
which is what lets a page still work with nothing running. The cost of
that is that the address knows where both ends live. Move either end and
the address is wrong, and nothing says so: the page still opens, the
prose is all there, the link just goes nowhere.

So two things here.

  moving        move or rename a page from a form, and every address on
                both sides is rewritten to match. Links pointing at it,
                links inside it, and the hidden _to that tells a form
                which file to save into.

  loose ends    for when a file is moved in Explorer instead, which is
                allowed and will happen. Every address that does not
                land on a file is listed, with the sentence it came
                from, and a control to point it somewhere real.

Nothing is indexed. Both read the files each time they are asked, the
same as everything else here, so there is no list anywhere that can rot.
"""

import html
import posixpath
import re

# href= and src= together, because a stylesheet is as breakable as a
# link and breaks more visibly. <form action="/save"> is left alone;
# addresses starting with / are the program's own and do not move.
ADDR_RE = re.compile(r'\b(href|src)="([^"]*)"', re.I)

LINK_RE = re.compile(r'<a\s[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.S | re.I)

# The hidden field naming the file a form writes into. Its value is a
# path from the top folder, so it moves when the file does. Missing this
# means a moved page's Save box quietly writes into the old address.
TO_RE = re.compile(r'(name="_to"\s+value=")([^"]*)(")', re.I)

TAG_RE = re.compile(r"<[^>]+>")
PARA_RE = re.compile(r"<p[^>]*>|</p>", re.I)

SKIP = ("#", "/", "http:", "https:", "mailto:", "data:", "javascript:", "//")


def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub("", fragment))).strip()


def pages(root, templates=False):
    """Every page in the folder, as paths from the top, forward slashes.

    Kind templates are left out unless asked for. They are a shape, not
    a page: nothing links at them and they are not read by anybody.
    Rewriting still visits them, because a shape can carry a stylesheet
    address that has to keep working.
    """
    out = []
    for p in sorted(root.rglob("*.html")):
        if p.name.endswith(".tmp"):
            continue
        # An underscore anywhere in the path means the program's own
        # storage rather than a page anybody visits - a kind's shape,
        # the list of ways to answer, the pages put away in _deleted.
        # The FOLDER has to count too, not just the filename: a page
        # moved into _deleted keeps its own name, and checking only the
        # name left it showing up in search and breaking loose-ends.
        rel = p.relative_to(root)
        if not templates and any(part.startswith("_") for part in rel.parts):
            continue
        out.append(p.relative_to(root).as_posix())
    return out


def target_of(page_rel, addr):
    """What a link points at, as a path from the top folder.

    None when it does not name a file inside here at all - an anchor, a
    website, a mail address, or one of the program's own /addresses.
    """
    if not addr or addr.lower().startswith(SKIP):
        return None
    addr = addr.split("#", 1)[0].split("?", 1)[0]
    if not addr:
        return None
    base = posixpath.dirname(page_rel)
    landed = posixpath.normpath(posixpath.join(base, addr))
    if landed.startswith(".."):
        return None
    return landed


def address_from(page_rel, target_rel):
    """The relative address one page should use to reach another."""
    base = posixpath.dirname(page_rel) or "."
    return posixpath.relpath(target_rel, base)


def keep_tail(addr, rebuilt):
    """Put back the #anchor a link had, if it had one."""
    cut = addr.find("#")
    return rebuilt + addr[cut:] if cut != -1 else rebuilt


def sentence_of(text, at):
    """The paragraph a link sits in, as plain words.

    This is what makes a loose end fixable. Seeing the address on its
    own tells you nothing; seeing the sentence you wrote it in tells you
    what you meant by it.
    """
    starts = [m.end() for m in PARA_RE.finditer(text[:at])]
    open_at = starts[-1] if starts else max(0, at - 300)
    close = PARA_RE.search(text, at)
    shut = close.start() if close else min(len(text), at + 300)
    got = plain(text[open_at:shut])
    return got if got else plain(text[max(0, at - 200):at + 200])


def loose_ends(root):
    """[(page, address, words, sentence), ...] - every link that lands
    on nothing. Sorted by page so a bad move reads as one run."""
    out = []
    for page_rel in pages(root):
        text = _read(root / page_rel)
        if text is None:
            continue
        for m in LINK_RE.finditer(text):
            addr = m.group(1)
            landed = target_of(page_rel, addr)
            if landed is None or (root / landed).exists():
                continue
            out.append((page_rel, addr, plain(m.group(2)),
                        sentence_of(text, m.start())))
    return out


def points_at(root, target_rel):
    """[(page, title, words, sentence), ...] - what links to this page.

    Every page in the folder, not only the ones belonging to a kind.
    The old version walked kinds, so once there were no kinds it found
    nothing at all and said so silently - a list that is empty because
    it never looked reads exactly like a page nothing points at.

    Read fresh each time it is asked for. Nothing is indexed, so a link
    made a second ago is in here and one removed by hand is not.
    """
    out = []
    for page_rel in pages(root):
        if page_rel == target_rel:
            continue
        text = _read(root / page_rel)
        if text is None:
            continue
        for m in LINK_RE.finditer(text):
            if target_of(page_rel, m.group(1)) != target_rel:
                continue
            out.append((page_rel, title_of(root, page_rel),
                        plain(m.group(2)), sentence_of(text, m.start())))
    out.sort(key=lambda r: (r[1].lower(), r[0].lower()))
    return out


def links_on(root, page_rel):
    """[(address, words, target, sentence), ...] - the links a page has.

    target is where it lands as a path from the top, or None when it
    points outside the folder or at nothing that can be checked.
    """
    text = _read(root / page_rel)
    if text is None:
        return []
    out = []
    for m in LINK_RE.finditer(text):
        addr = m.group(1)
        if addr.startswith("/"):
            continue                      # the program's own addresses
        out.append((addr, plain(m.group(2)), target_of(page_rel, addr),
                    sentence_of(text, m.start())))
    return out


def repoint_any(root, page_rel, was_addr, words, target_rel, read, write):
    """Point one link somewhere else, whether or not it was broken.

    Matched on the address AND the words, because a page can hold two
    links to the same place on different words, and changing the wrong
    one would be worse than refusing.
    """
    text = read(root / page_rel)
    if text is None:
        return "That page could not be read."
    if not (root / target_rel).is_file():
        return "There is no page at " + target_rel + "."
    for m in LINK_RE.finditer(text):
        if m.group(1) != was_addr or plain(m.group(2)) != words:
            continue
        rebuilt = html.escape(
            keep_tail(was_addr, address_from(page_rel, target_rel)),
            quote=True)
        new = (text[:m.start()]
               + '<a href="' + rebuilt + '">' + m.group(2) + "</a>"
               + text[m.end():])
        if not write(root / page_rel, new):
            return "That page could not be written to."
        return ""
    return ("That link is not on " + page_rel + " any more. It may have "
            "been changed since this list was made.")


def unlink(root, page_rel, was_addr, words, read, write):
    """Take a link off, keeping the words exactly as they are."""
    text = read(root / page_rel)
    if text is None:
        return "That page could not be read."
    for m in LINK_RE.finditer(text):
        if m.group(1) != was_addr or plain(m.group(2)) != words:
            continue
        new = text[:m.start()] + m.group(2) + text[m.end():]
        if not write(root / page_rel, new):
            return "That page could not be written to."
        return ""
    return "That link is not on " + page_rel + " any more."


def orphan_forms(root):
    """[(page, address), ...] - forms told to save into a file that is
    not there. Silent otherwise: the box takes your words and the save
    fails afterwards, which is the worst order for that to happen in."""
    out = []
    for page_rel in pages(root):
        text = _read(root / page_rel)
        if text is None:
            continue
        for m in TO_RE.finditer(text):
            to = html.unescape(m.group(2))
            if to and not (root / to).exists():
                out.append((page_rel, to))
    return out


def retarget(text, page_rel, was, now, moved_page=None):
    """Rewrite every address in one page's text.

    was/now is the file that moved. moved_page is set when the text
    being rewritten IS the moved file, in which case every address it
    holds is recomputed for where it has landed, not just the ones
    that pointed at itself.
    """
    here = moved_page or page_rel

    def one(m):
        attr, addr = m.group(1), m.group(2)
        landed = target_of(page_rel, addr)
        if landed is None:
            return m.group(0)
        if landed == was:
            landed = now
        elif moved_page is None:
            return m.group(0)
        return attr + '="' + html.escape(
            keep_tail(addr, address_from(here, landed)), quote=True) + '"'

    return ADDR_RE.sub(one, text)


NAME_RE = re.compile(r"(<(h1|title)\b[^>]*>)(.*?)(</\2>)", re.S | re.I)


def rename_inside(text, called):
    """Give the page its new name, in the two places it says it.

    A file renamed but still calling itself the old thing is worse than
    either, because search results and every list read from the title
    keep saying the name you just changed.
    """
    def one(m):
        return m.group(1) + html.escape(called) + m.group(4)

    return NAME_RE.sub(one, text, count=2)


def remove(root, page_rel, read, write):
    """Put a page out of the way rather than destroying it.

    It goes to _deleted/, which is not served, not searched and not in
    any list, because the underscore keeps it out of pages(). Getting it
    back is moving it out again. Nothing here should be able to make
    something you wrote genuinely unrecoverable in one press.
    """
    path = root / page_rel
    if not path.is_file():
        return "There is no page at " + page_rel + "."
    if page_rel.startswith("_"):
        return "That is a file the program reads, not a page."
    text = read(path)
    if text is None:
        return "That page could not be read, so it was not touched."
    gone = root / "_deleted" / page_rel
    gone.parent.mkdir(parents=True, exist_ok=True)
    if gone.exists():
        stem = gone.stem
        n = 2
        while (gone.parent / (stem + "-" + str(n) + ".html")).exists():
            n += 1
        gone = gone.parent / (stem + "-" + str(n) + ".html")
    if not write(gone, text):
        return "That page could not be put away, so nothing was changed."
    try:
        path.unlink()
    except OSError:
        return ("A copy was put in _deleted but the page itself could not "
                "be removed. Both exist right now.")
    return ""


def move(root, was, now, read, write, called=""):
    """Move a page and keep every address on both sides working.

    Returns "" when it worked, or a sentence saying what stopped it.
    Nothing is touched until the move itself has succeeded, so a
    failure leaves everything exactly as it was.
    """
    was = was.strip().strip("/")
    now = now.strip().strip("/")
    if not was or not now:
        return "A page and somewhere to put it are both needed."
    if was == now:
        return "That is where it already is."
    src, dst = root / was, root / now
    if not src.is_file():
        return "There is no page at " + was + "."
    if dst.exists():
        return "There is already something at " + now + "."
    if src.name == "_kind.html":
        return ("That is the shape a kind's pages take, not a page. "
                "Moving it would change what its kind means.")

    text = read(src)
    if text is None:
        return "That page could not be read."

    # Its own addresses first, then the hidden field naming itself,
    # then write it where it is going. Only once that has landed do the
    # pages pointing at it get touched.
    moved = retarget(text, was, was, now, moved_page=now)
    if called.strip():
        moved = rename_inside(moved, " ".join(called.split()))
    moved = TO_RE.sub(
        lambda m: m.group(1) + (html.escape(now, quote=True)
                                if html.unescape(m.group(2)) == was
                                else m.group(2)) + m.group(3), moved)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not write(dst, moved):
        return "That page could not be written to " + now + "."
    try:
        src.unlink()
    except OSError:
        return ("The page was copied to " + now + " but the old one at "
                + was + " could not be removed. Both exist right now.")

    for page_rel in pages(root, templates=True):
        if page_rel == now:
            continue
        other = read(root / page_rel)
        if other is None:
            continue
        fixed = retarget(other, page_rel, was, now)
        fixed = TO_RE.sub(
            lambda m: m.group(1) + (html.escape(now, quote=True)
                                    if html.unescape(m.group(2)) == was
                                    else m.group(2)) + m.group(3), fixed)
        if fixed != other:
            write(root / page_rel, fixed)
    return ""


def repoint(root, page_rel, was_addr, target_rel, read, write):
    """Point one loose end at a real page. The words stay yours."""
    path = root / page_rel
    text = read(path)
    if text is None:
        return "That page could not be read."
    if not (root / target_rel).is_file():
        return "There is no page at " + target_rel + "."
    rebuilt = html.escape(
        keep_tail(was_addr, address_from(page_rel, target_rel)), quote=True)
    want = 'href="' + html.escape(was_addr, quote=True) + '"'
    if want not in text:
        return ("That link is not in " + page_rel + " any more. It may "
                "have been changed since this list was made.")
    new = text.replace(want, 'href="' + rebuilt + '"', 1)
    if not write(path, new):
        return "That page could not be written to."
    return ""


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def title_of(root, page_rel):
    """What to call a page in a list. Its <title>, or its filename."""
    text = _read(root / page_rel)
    m = TITLE_RE.search(text or "")
    got = plain(m.group(1)) if m else ""
    return got or page_rel.rsplit("/", 1)[-1]


def folders_in(root):
    """Every folder that holds pages, plus the top, as addresses."""
    out = {""}
    for page_rel in pages(root, templates=True):
        if "/" in page_rel:
            out.add(page_rel.rsplit("/", 1)[0])
    return sorted(out)


def _options(rows, chosen=""):
    out = []
    for value, label in rows:
        picked = " selected" if value == chosen else ""
        out.append('<option value="' + html.escape(value, quote=True) + '"'
                   + picked + ">" + html.escape(label) + "</option>")
    return "\n".join(out)


def repairs_page(root, said=""):
    """The whole page. Built when asked for, never stored.

    A list of what is broken cannot be a file, because the moment it is
    written down it is a second copy that can disagree with the folder.
    This is read off disk every time it is opened, so F5 is the refresh.
    """
    every = [(p, title_of(root, p) + "  -  " + p) for p in pages(root)]
    picker = _options(every)
    parts = ['<h1>Repairs</h1>', '<nav><a href="/index.html">'
             "Back to the top</a></nav>"]
    if said:
        parts.append('<p id="said">' + html.escape(said) + "</p>")

    ends = loose_ends(root)
    parts.append("<h2>Loose ends</h2>")
    if not ends:
        parts.append("<p>Every link on every page lands on a real file. "
                     "Nothing to fix.</p>")
    else:
        parts.append("<p>" + str(len(ends)) + (" link goes" if len(ends) == 1
                     else " links go") + " nowhere. Each one below shows the "
                     "sentence it came from, so you can see what you meant "
                     "by it. Choosing a page rewrites the address and leaves "
                     "your words alone.</p>")
    for n, (page_rel, addr, words, sentence) in enumerate(ends, 1):
        me = "end" + str(n)
        parts.append(
            '<form method="post" action="/repoint">\n<fieldset>\n<legend>'
            + html.escape(words or addr) + ", in " + html.escape(page_rel)
            + "</legend>\n"
            '<input type="hidden" name="page" value="'
            + html.escape(page_rel, quote=True) + '">\n'
            '<input type="hidden" name="addr" value="'
            + html.escape(addr, quote=True) + '">\n'
            '<input type="hidden" name="words" value="'
            + html.escape(words, quote=True) + '">\n'
            "<p>" + html.escape(sentence) + "</p>\n"
            "<p>It points at " + html.escape(addr)
            + ", and there is no file there.</p>\n"
            '<label for="' + me + '">Point it at</label>\n'
            '<select id="' + me + '" name="target">\n'
            '<option value="">(choose a page)</option>\n' + picker
            + "\n</select>\n"
            '<p>Pressing this changes only the address. The words '
            + html.escape(words or "in the link") + " stay as they are.</p>\n"
            '<button type="submit" name="do" value="point">Point '
            "it there</button>\n"
            '<p>Or, if the page it named is gone on purpose and there is '
            'nothing it should point at instead, take the link off. Your '
            "words stay; only the link goes.</p>\n"
            '<button type="submit" name="do" value="unlink">Take the link '
            "off and keep the words</button>\n"
            "</fieldset>\n</form>")

    orphans = orphan_forms(root)
    parts.append("<h2>Boxes that would not save</h2>")
    if not orphans:
        parts.append("<p>Every Save box on every page names a file that "
                     "is really there.</p>")
    else:
        parts.append("<p>These pages have a box that says it saves into a "
                     "file that is not there. Typing in one and pressing "
                     "Save would fail after you had written it, which is "
                     "the worst order for that to happen in. Moving the "
                     "page with the form below fixes this.</p>\n<ul>"
                     + "".join("<li>" + html.escape(p) + " tries to save "
                               "into " + html.escape(t) + "</li>"
                               for p, t in orphans) + "</ul>")

    parts.append(
        "<h2>Put away</h2>\n"
        "<p>Pages and writing that were put away are kept, not deleted. The "
        '<a href="/putaway">Put away</a> page lists them, with a button to '
        "bring each one back.</p>")

    parts.append(
        "<h2>Move or rename a page</h2>\n"
        "<p>This moves the file and rewrites every address on both sides: "
        "links pointing at it, links inside it, its stylesheet, and the "
        "hidden field telling its Save box which file to write into.</p>\n"
        '<form method="post" action="/move">\n<fieldset>\n'
        "<legend>Move a page</legend>\n"
        '<label for="mv-page">Which page</label>\n'
        '<select id="mv-page" name="page">\n'
        '<option value="">(choose a page)</option>\n' + picker + "\n</select>\n"
        '<label for="mv-folder">Into which folder</label>\n'
        '<select id="mv-folder" name="folder">\n'
        + _options([(f, f or "(the top folder)") for f in folders_in(root)])
        + "\n</select>\n"
        '<label for="mv-newfolder">or a new folder called</label>\n'
        '<input type="text" id="mv-newfolder" name="newfolder" value="">\n'
        '<label for="mv-name">and call it</label>\n'
        '<input type="text" id="mv-name" name="name" value="">\n'
        "<p>Leave the name empty to keep the name it has. Type one to "
        "rename it at the same time.</p>\n"
        '<button type="submit">Move it</button>\n'
        "</fieldset>\n</form>")

    return ('<!doctype html>\n<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, '
            'initial-scale=1">\n<title>Repairs</title>\n'
            '<link rel="stylesheet" href="/style.css">\n</head>\n<body>\n'
            + "\n\n".join(parts) + "\n</body>\n</html>\n")


def _read(path):
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    for enc in ("utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")
