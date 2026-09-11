"""Bringing back what was put away.

Nothing put away is destroyed. A page goes into _deleted at the address
it had. Writing goes into _deleted/pieces, in a file of its own that
names the page it came from. This finds all of it and puts it back from
a page in the browser, so getting something back is never a job for
Explorer.

A folder in _deleted is offered as a whole folder when nothing of that
name is left at the top - the whole thing was put aside. When the folder
is still there, what is in _deleted is pages put away from it one at a
time, and they are offered one at a time.

Read off disk each time it is asked, like everything else here. There is
no list of put-away things anywhere to fall out of step with the folder.
"""

import html
import re
import shutil

import links
import moving

DELETED = "_deleted"
MARK = "rather than deleted."
ORIGIN_RE = re.compile(
    r'This was on <a href="([^"]*)">.*?</a> until ([^.<]*)\.', re.S)
BODY_END_RE = re.compile(r"</body>", re.I)


def _html(folder):
    return sorted(p for p in folder.rglob("*.html") if p.is_file())


def _body(text):
    """The writing in a put-away file: after the note of where it came
    from, up to the end of the page."""
    at = text.find(MARK)
    close = text.find("</p>", at)
    start = close + 4 if close != -1 else at + len(MARK)
    end = BODY_END_RE.search(text, start)
    return text[start:end.start() if end else len(text)].strip("\n")


def writing(root):
    """[{kept, page, when, text, words}, ...] - put-away writing, newest first.

    page is where it came from, as an address from the top, or None when
    that cannot be told.
    """
    out = []
    folder = root / moving.AWAY
    if not folder.is_dir():
        return out
    for p in folder.glob("*.html"):
        text = links._read(p)
        if not text or MARK not in text:
            continue
        kept = p.relative_to(root).as_posix()
        m = ORIGIN_RE.search(text)
        body = _body(text)
        out.append({"kept": kept,
                    "page": (links.target_of(kept, html.unescape(m.group(1)))
                             if m else None),
                    "when": m.group(2).strip() if m else "",
                    "text": body, "words": links.plain(body)})
    out.sort(key=lambda w: (w["when"], w["kept"]), reverse=True)
    return out


def top(root):
    """(pages, folders) - what is put away, apart from writing.

    pages is [address in _deleted, ...]; folders is [(name, pages in it)].
    """
    pages, folders = [], []
    base = root / DELETED
    if not base.is_dir():
        return pages, folders
    for p in sorted(base.iterdir()):
        if p.is_file() and p.suffix.lower() in (".html", ".htm"):
            pages.append(p.relative_to(root).as_posix())
        elif p.is_dir():
            inside = _html(p)
            if p.name == "pieces":
                inside = [q for q in inside
                          if MARK not in (links._read(q) or "")]
            if not inside:
                continue
            if p.name == "pieces" or (root / p.name).exists():
                pages += [q.relative_to(root).as_posix() for q in inside]
            else:
                folders.append((p.name, len(inside)))
    return pages, folders


def in_folder(root, name):
    """Every page in one put-away folder, or None if there is no such folder."""
    if not _plain_name(name) or not (root / DELETED / name).is_dir():
        return None
    return [p.relative_to(root).as_posix() for p in _html(root / DELETED / name)]


def count(root):
    pages, folders = top(root)
    return len(writing(root)) + len(pages) + len(folders)


def original(kept):
    """Where a put-away page used to be."""
    return kept[len(DELETED) + 1:]


def _plain_name(name):
    return bool(name) and not re.search(r"[/\\]|\.\.", name)


def _is_kept(root, kept):
    return (bool(kept) and kept.startswith(DELETED + "/")
            and ".." not in kept and "\\" not in kept
            and (root / kept).is_file())


def _tidy(root, folder):
    """Take away folders in _deleted left empty by bringing something back."""
    stop = (root / DELETED).resolve()
    folder = folder.resolve()
    while folder != stop and stop in folder.parents:
        try:
            folder.rmdir()
        except OSError:
            return
        folder = folder.parent


def bring_page(root, kept, to, read, write):
    """Put a page back. Returns (its address, trouble).

    Its old address is always allowed. Any other has to be an ordinary
    page address. If it lands somewhere new, the addresses inside it are
    rewritten for there, and so is the hidden field naming its own file.
    """
    if not _is_kept(root, kept) or not kept.lower().endswith((".html", ".htm")):
        return "", "That is not a page that was put away."
    was = original(kept)
    to = (to or "").strip().strip("/")
    if not to:
        return "", "No address was given to bring it back to."
    if not to.lower().endswith((".html", ".htm")):
        to += ".html"
    if to != was and (to.startswith("_") or "/_" in to or ".." in to
                      or "\\" in to):
        return "", "That is not an address a page can be brought back to."
    if (root / to).exists():
        return "", ("There is already a page at " + to + ". Type another "
                    "address to bring it back to.")
    text = read(root / kept)
    if text is None:
        return "", "That could not be read, so nothing was brought back."
    if to != was:
        text = links.retarget(text, was, None, None, moved_page=to)
        text = links.TO_RE.sub(
            lambda m: m.group(1) + (html.escape(to, quote=True)
                                    if html.unescape(m.group(2)) == was
                                    else m.group(2)) + m.group(3), text)
    (root / to).parent.mkdir(parents=True, exist_ok=True)
    if not write(root / to, text):
        return "", ("It could not be written to " + to
                    + ", so nothing was brought back.")
    try:
        (root / kept).unlink()
    except OSError:
        return to, ("It is back at " + to + ", but the put-away copy could "
                    "not be removed, so both exist right now.")
    _tidy(root, (root / kept).parent)
    return to, ""


def bring_folder(root, name):
    """Put a whole folder back under its own name. Returns trouble or "".

    Only under its own name, because the pages in it name each other and
    the folders around them by where they are, and a folder brought back
    somewhere else would break all of that at once. Its pages can still
    come back one at a time, anywhere.
    """
    if (not _plain_name(name) or name == "pieces"
            or not (root / DELETED / name).is_dir()):
        return "That is not a folder that was put away."
    if (root / name).exists():
        return ("There is already something called " + name + " at the top, "
                "so the folder was not brought back. Its pages can still come "
                "back one at a time.")
    try:
        shutil.move(str(root / DELETED / name), str(root / name))
    except OSError:
        return "That folder could not be moved back."
    return ""


def bring_writing(root, kept, target, read, write):
    """Put writing back at the bottom of a page. Returns trouble or ""."""
    found = [w for w in writing(root) if w["kept"] == kept]
    if not found:
        return "That writing is not put away any more."
    other = read(root / target)
    if other is None:
        return "There is no page at " + target + "."
    if not write(root / (target + ".bak"), other):
        return ("The previous version of that page could not be kept, so "
                "nothing was brought back.")
    back = moving.put(other, moving.rebase(found[0]["text"], kept, target),
                      "bottom")
    if not write(root / target, back):
        return target + " could not be written to, so nothing was brought back."
    try:
        (root / kept).unlink()
    except OSError:
        return ("It is back on " + target + ", but the put-away copy could not "
                "be removed, so both exist right now.")
    return ""
