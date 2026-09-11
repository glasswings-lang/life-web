"""Moving notes about on a page, and putting them in date order.

A note is what the Add box leaves on a page: a <div class="addition">
holding its date and everything written under it. It moves as one
piece, so a date is never separated from its words.

Nothing keeps a list of notes anywhere. The page is read, the notes are
found in it, and the file is written back with them in their new
places. Everything that is not a note - writing put straight onto the
page, the marker, the template - stays exactly where it was.
"""

import hashlib
import html
import re
from datetime import datetime

# Blanked out before looking, keeping every position the same. A note
# inside a template is the shape of a future note, not a note, and a
# comment or an edit box that mentions one is not one either.
MASK_RE = re.compile(
    r"<!--.*?-->|<template\b.*?</template>|<textarea\b.*?</textarea>"
    r"|<script\b.*?</script>|<style\b.*?</style>", re.S | re.I)

DIV_RE = re.compile(r"<(/?)div\b([^>]*)>", re.I)
NOTE_CLASS_RE = re.compile(r'\bclass\s*=\s*"[^"]*\baddition\b[^"]*"', re.I)
WHEN_RE = re.compile(
    r'<([a-zA-Z0-9]+)\b[^>]*\bclass\s*=\s*"[^"]*\bwhen\b[^"]*"[^>]*>'
    r"(.*?)</\1>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")

# The shape the program writes dates in, and two near relations that a
# hand-written note might use.
STAMPS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")

GONE = ("That note is not on the page any more. The page may have changed "
        "since this list was made.")


def _words(fragment):
    return re.sub(r"\s+", " ",
                  html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def find(text):
    """[{start, end, when, words}, ...] - every note, in page order.

    Divs are counted in and out, so a note holding a div of its own is
    still one note. A note that is never closed is left out rather than
    guessed at: moving something whose end is unknown could tear the
    page in half.
    """
    text = text or ""
    hidden = MASK_RE.sub(lambda m: " " * (m.end() - m.start()), text)
    out, depth, start = [], 0, None
    for m in DIV_RE.finditer(hidden):
        closing = m.group(1) == "/"
        if start is None:
            if not closing and NOTE_CLASS_RE.search(m.group(2)):
                start, depth = m.start(), 1
            continue
        depth += -1 if closing else 1
        if depth == 0:
            inner = text[start:m.end()]
            w = WHEN_RE.search(inner)
            rest = inner[w.end():] if w else inner
            out.append({"start": start, "end": m.end(),
                        "when": _words(w.group(2)) if w else "",
                        "words": _words(rest)})
            start = None
    return out


def label(note, most=10):
    """A note by its date and its first few words."""
    words = note["words"].split()
    short = " ".join(words[:most])
    if note["when"] and short:
        return note["when"] + ", " + short
    return note["when"] or short or "A note with nothing written in it"


def moment(note):
    for shape in STAMPS:
        try:
            return datetime.strptime(note["when"], shape)
        except ValueError:
            pass
    return None


def fingerprint(text):
    """Changes whenever the page does.

    Every move form carries the one its page had when the list was
    made. If they no longer match, the numbers in the form may point at
    different notes, so nothing is moved.
    """
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def choices(found, n):
    """[(value, words), ...] - everywhere note n could go."""
    out = []
    if n != 0:
        out.append(("top", "The top, above every other note"))
    if n != len(found) - 1:
        out.append(("bottom", "The bottom, below every other note"))
    for m, other in enumerate(found):
        if m != n and m != n - 1:
            out.append(("after:" + str(m), "After " + label(other)))
    return out


def move(text, n, to):
    """Move note n. Returns (new_text, trouble).

    to is "top", "bottom" or "after:<number of another note>". The note
    is lifted out with the line breaks around it, leaving as many as the
    wider side had, so a blank line between two things is neither lost
    nor doubled. It goes back in with a line break of its own.
    """
    found = find(text)
    if n < 0 or n >= len(found):
        return None, GONE
    if to not in ("top", "bottom") and not re.fullmatch(r"after:\d+", to or ""):
        return None, "Nowhere was chosen, so that note stayed where it was."
    if to.startswith("after:"):
        m = int(to[6:])
        if m >= len(found):
            return None, GONE
        if m == n:
            return None, "A note cannot go after itself."
    if len(found) < 2:
        return text, ""

    s, e = found[n]["start"], found[n]["end"]
    piece = text[s:e]
    before = s - len(text[:s].rstrip("\n"))
    after = len(text[e:]) - len(text[e:].lstrip("\n"))
    rest = text[:s - before] + "\n" * max(before, after) + text[e + after:]
    left = find(rest)

    if to == "top":
        at = left[0]["start"]
        return rest[:at] + piece + "\n" + rest[at:], ""
    if to == "bottom":
        at = left[-1]["end"]
    else:
        m = int(to[6:])
        at = left[m if m < n else m - 1]["end"]
    return rest[:at] + "\n" + piece + rest[at:], ""


def said_after_move(found, n, to):
    """What to say once note n has gone where it was sent."""
    what = ("The note from " + found[n]["when"] if found[n]["when"]
            else "That note")
    if to == "top":
        return what + " is at the top now."
    if to == "bottom":
        return what + " is at the bottom now."
    return what + " is now after " + label(found[int(to[6:])]) + "."


def sort(text, newest_first=True):
    """Every note in date order. Returns (new_text, undated).

    The notes swap places and nothing else moves: whatever sits between
    two notes stays in that gap. Notes written in the same minute keep
    the order they were in. A note whose date cannot be read goes after
    the dated ones, in the order it was already in, and undated says
    how many there were so that can be said out loud.
    """
    found = find(text)
    if len(found) < 2:
        return text, 0
    dated = [f for f in found if moment(f)]
    undated = [f for f in found if not moment(f)]
    dated = sorted(dated, key=moment, reverse=newest_first)
    out, at = [], 0
    for slot, note in zip(found, dated + undated):
        out.append(text[at:slot["start"]])
        out.append(text[note["start"]:note["end"]])
        at = slot["end"]
    out.append(text[at:])
    return "".join(out), len(undated)
