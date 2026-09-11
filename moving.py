"""Moving writing about: on its page, onto another page, or out of the way.

A piece is what the Edit page offers one at a time: a paragraph, a
heading, a list or a quote. Any piece can move to another spot on its
page. A heading moves on its own. Writing is often put under the wrong
heading, and moving a heading must never drag that along.

A heading can also take its section with it, when that is asked for:
itself and the pieces after it, down to the next heading at its level or
above. A section stops at anything that is not writing - the edge of a
note, the spot new notes go, a form - because carrying one of those off
would tear the page.

Several picked pieces can move together too. They go in the order they
were on the page, wherever they were on it.

Out of the way means the same two things it means for a page: onto
another page, or put away. Put away writing is kept in _deleted/pieces,
in a file of its own that says where it came from. Nothing is destroyed.
A note with nothing left in it can be put away the same way.
"""

import html
import re

import editing
import links
import notes

AWAY = "_deleted/pieces"

KINDS = {"p": "Paragraph", "ul": "Bulleted list", "ol": "Numbered list",
         "blockquote": "Quote"}

GONE = ("That piece is not on the page any more. The page may have changed "
        "since this was shown.")
NOWHERE = "Nowhere was chosen, so nothing moved."
NOTHING = "Nothing was picked, so nothing moved."
INSIDE = ("It cannot go after itself, or after something that is moving "
          "with it.")


def what(tag):
    if re.fullmatch(r"h[1-6]", tag):
        return "Heading level " + tag[1]
    return KINDS.get(tag, "Piece")


def label(piece, most=10):
    """A piece by what it is and its first few words."""
    words = editing.as_words(piece[3]).split()
    return (what(piece[1]) + ": "
            + (" ".join(words[:most]) or "nothing written in it"))


def level(piece):
    return int(piece[1][1]) if re.fullmatch(r"h[1-6]", piece[1]) else None


def section_end(text, pieces, n):
    """The number of the last piece in piece n's section.

    n itself for anything that is not a heading, and for a heading with
    nothing it can take along.
    """
    lv = level(pieces[n])
    if lv is None:
        return n
    last = n
    for m in range(n + 1, len(pieces)):
        if text[pieces[m - 1][5]:pieces[m][4]].strip():
            break                   # something that is not writing between
        other = level(pieces[m])
        if other is not None and other <= lv:
            break
        last = m
    return last


def _lift(text, start, end):
    """(the writing, the page without it).

    Taken out with the line breaks around it, leaving as many as the
    wider side had, so a blank line is neither lost nor doubled.
    """
    before = start - len(text[:start].rstrip("\n"))
    after = len(text[end:]) - len(text[end:].lstrip("\n"))
    return (text[start:end],
            text[:start - before] + "\n" * max(before, after)
            + text[end + after:])


def _picks(picks):
    return sorted(set([picks] if isinstance(picks, int) else picks))


def take(text, picks, whole=False):
    """(the writing, the page without it, trouble).

    One piece, with its section when whole is asked for, is lifted as a
    single stretch of the page, so the spacing inside a section is kept
    exactly. Several picked pieces are lifted one at a time, the last
    first so the places of the earlier ones still hold, and joined in
    page order.
    """
    picks = _picks(picks)
    pieces = editing.blocks(text)
    if not picks:
        return None, None, NOTHING
    if picks[0] < 0 or picks[-1] >= len(pieces):
        return None, None, GONE
    if len(picks) == 1:
        n = picks[0]
        last = section_end(text, pieces, n) if whole else n
        piece, rest = _lift(text, pieces[n][4], pieces[last][5])
        return piece, rest, ""
    taken, rest = [], text
    for n in reversed(picks):
        piece, rest = _lift(rest, pieces[n][4], pieces[n][5])
        taken.append(piece)
    return "\n".join(reversed(taken)), rest, ""


def _edges(text):
    """(start of the first thing, end of the last thing), or None.

    A thing is a note, as a whole, or a piece that is not inside a note.
    The top of a page is above all of them and the bottom is below all of
    them, so neither ever lands inside a dated note.
    """
    spans = [(f["start"], f["end"]) for f in notes.find(text)]
    inside = spans[:]
    for p in editing.blocks(text):
        if not any(s <= p[4] and p[5] <= e for s, e in inside):
            spans.append((p[4], p[5]))
    if not spans:
        return None
    return min(s for s, _e in spans), max(e for _s, e in spans)


def put(text, piece, where="bottom"):
    """Writing put at the top or the bottom of a page.

    A page with nothing written on it yet takes it just above the spot new
    notes go, or above the end of the page when it has no such spot.
    """
    edges = _edges(text)
    if edges and where == "top":
        return text[:edges[0]] + piece + "\n" + text[edges[0]:]
    if edges:
        return text[:edges[1]] + "\n" + piece + text[edges[1]:]
    at = text.find("<!-- here -->")
    if at == -1:
        m = re.search(r"</body>", text, re.I)
        at = m.start() if m else len(text)
    return text[:at] + piece + "\n" + text[at:]


def _valid(to):
    return to in ("top", "bottom") or re.fullmatch(r"after:\d+", to or "")


def move(text, n, to, whole=False):
    """Move piece n, or its section, on its own page.

    to is "top", "bottom" or "after:<number of another piece>".
    Returns (new_text, trouble). The same text back means it was already
    there.
    """
    pieces = editing.blocks(text)
    if n < 0 or n >= len(pieces):
        return None, GONE
    if not _valid(to):
        return None, NOWHERE
    last = section_end(text, pieces, n) if whole else n
    start, end = pieces[n][4], pieces[last][5]

    if to.startswith("after:"):
        m = int(to[6:])
        if m >= len(pieces):
            return None, GONE
        if n <= m <= last:
            return None, INSIDE
        if m < n and not text[pieces[m][5]:start].strip():
            return text, ""
    edges = _edges(text)
    if to == "top" and edges and edges[0] == start:
        return text, ""
    if to == "bottom" and edges and edges[1] == end:
        return text, ""

    piece, rest = _lift(text, start, end)
    if not _edges(rest):
        return text, ""
    if to in ("top", "bottom"):
        return put(rest, piece, to), ""
    m = int(to[6:])
    left = editing.blocks(rest)
    at = left[m if m < n else m - (last - n + 1)][5]
    return rest[:at] + "\n" + piece + rest[at:], ""


def move_many(text, picks, to):
    """Move several picked pieces together, in page order.

    Returns (new_text, trouble), the same as move.
    """
    picks = _picks(picks)
    pieces = editing.blocks(text)
    if not picks:
        return None, NOTHING
    if not _valid(to):
        return None, NOWHERE
    m = int(to[6:]) if to.startswith("after:") else None
    if m is not None and m >= len(pieces):
        return None, GONE
    if m in picks:
        return None, INSIDE
    piece, rest, trouble = take(text, picks)
    if trouble:
        return None, trouble
    if m is None:
        return put(rest, piece, to), ""
    at = editing.blocks(rest)[m - sum(1 for p in picks if p < m)][5]
    return rest[:at] + "\n" + piece + rest[at:], ""


def rebase(piece, from_rel, to_rel):
    """Every address in the writing, recomputed for where it is going."""
    return links.retarget(piece, from_rel, None, None, moved_page=to_rel)


def _moved(count):
    return "Moved" if count == 1 else "Moved " + str(count) + " pieces"


def _said_where(text, to, count=1):
    if to == "top":
        return _moved(count) + " to the top of the page."
    if to == "bottom":
        return _moved(count) + " to the bottom of the page."
    return (_moved(count) + " to just after "
            + label(editing.blocks(text)[int(to[6:])]) + ".")


def within(root, page_rel, picks, whole, to, read, write):
    """Move it on its page and write that down. Returns what to say."""
    picks = _picks(picks)
    path = root / page_rel
    text = read(path)
    if text is None:
        return "That page could not be read, so nothing was moved."
    if len(picks) == 1:
        new, trouble = move(text, picks[0], to, whole)
    else:
        new, trouble = move_many(text, picks, to)
    if trouble:
        return trouble
    if new == text:
        return "It was already there, so nothing changed."
    if not write(root / (page_rel + ".bak"), text):
        return "The previous version could not be kept, so nothing was moved."
    if not write(path, new):
        return "That page could not be written to."
    return _said_where(text, to, len(picks))


def onto(root, page_rel, picks, whole, target_rel, where, read, write):
    """Move it onto another page. Returns what to say."""
    picks = _picks(picks)
    if target_rel == page_rel:
        return "That is the page it is already on, so nothing was moved."
    if where not in ("top", "bottom"):
        return "The top or the bottom of that page was not chosen."
    text, other = read(root / page_rel), read(root / target_rel)
    if text is None or other is None:
        return "One of those pages could not be read, so nothing was moved."
    piece, rest, trouble = take(text, picks, whole)
    if trouble:
        return trouble
    if not write(root / (page_rel + ".bak"), text):
        return "The previous version could not be kept, so nothing was moved."
    if not write(root / target_rel,
                 put(other, rebase(piece, page_rel, target_rel), where)):
        return target_rel + " could not be written to, so nothing was moved."
    if not write(root / page_rel, rest):
        return ("It was put onto " + target_rel + ", but this page could not "
                "be written to, so right now it is on both.")
    return (_moved(len(picks)) + " onto " + links.title_of(root, target_rel)
            + ", at the " + where + " of it.")


AWAY_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Put away from {title}</title>
</head>
<body>

<h1>Put away from {title}</h1>

<p>This was on <a href="{back}">{page}</a> until {when}. It was put away
rather than deleted.</p>

{piece}

</body>
</html>
"""


def _keep(root, page_rel, text, piece, rest, count, read, write, when):
    """Keep the writing in a file of its own, then take it off the page."""
    stem = re.sub(r"\.html?$", "", page_rel, flags=re.I).replace("/", "-")
    name = stem + "-" + re.sub(r"[^0-9]+", "-", when).strip("-")
    kept = AWAY + "/" + name + ".html"
    number = 2
    while (root / kept).exists():
        kept = AWAY + "/" + name + "-" + str(number) + ".html"
        number += 1
    (root / AWAY).mkdir(parents=True, exist_ok=True)

    title = links.title_of(root, page_rel)
    page = AWAY_PAGE.format(
        title=html.escape(title), page=html.escape(page_rel),
        back=html.escape(links.address_from(kept, page_rel), quote=True),
        when=html.escape(when), piece=rebase(piece, page_rel, kept))
    if not write(root / (page_rel + ".bak"), text):
        return "The previous version could not be kept, so nothing was put away."
    if not write(root / kept, page):
        return "It could not be kept, so nothing was put away."
    if not write(root / page_rel, rest):
        return ("It was kept safe, but this page could not be changed, so "
                "right now it is in both places.")
    if count == 1:
        return ("Put away. It is kept safe on the Put away page, and you can "
                "bring it back from there.")
    return ("Put away " + str(count) + " pieces. They are kept safe together "
            "on the Put away page, and you can bring them back from there.")


def away(root, page_rel, picks, whole, read, write, when):
    """Put it out of the way, kept in a file of its own. Returns what to say.

    when is the date and time, as the program writes them.
    """
    picks = _picks(picks)
    text = read(root / page_rel)
    if text is None:
        return "That page could not be read, so nothing was put away."
    piece, rest, trouble = take(text, picks, whole)
    if trouble:
        return trouble
    return _keep(root, page_rel, text, piece, rest, len(picks), read, write,
                 when)


def away_note(root, page_rel, k, read, write, when):
    """Put note k away, date and all. Returns what to say."""
    text = read(root / page_rel)
    if text is None:
        return "That page could not be read, so nothing was put away."
    found = notes.find(text)
    if k < 0 or k >= len(found):
        return notes.GONE
    piece, rest = _lift(text, found[k]["start"], found[k]["end"])
    return _keep(root, page_rel, text, piece, rest, 1, read, write, when)
