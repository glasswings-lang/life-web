#!/usr/bin/env python3
"""Give written answers somewhere to BE on pages that already exist.

A written answer used to be emitted as a label and a box and nothing
else, so its words lived only inside the box. Searching drops forms and
flags are not hunted inside a box, so those words could not be found and
a flag in one was invisible. field_block emits a shown paragraph now,
but only for questions made from here on: a page already on disk still
has the old shape.

This walks a folder and adds the missing paragraph, carrying the words
that are in the box into it so nothing has to be retyped and searching
finds them immediately.

It adds nothing where a display element for that id already exists, so
running it twice is the same as running it once. It touches no other
byte of any page.

    python bring_fields_forward.py <folder> [--write]

Without --write it says what it would do and changes nothing.
"""

import html
import re
import sys
from pathlib import Path

BOX = re.compile(
    r'([ \t]*)<textarea[^>]*\bid="([^"]+)-box"[^>]*\bname="set-([^"]+)"'
    r'[^>]*>(.*?)</textarea>', re.S | re.I)


def label_start(text, at):
    """Where the <label> for a box begins, so the paragraph goes above
    it rather than between the label and the thing it names."""
    m = None
    for hit in re.finditer(r'[ \t]*<label\b[^>]*>', text[:at], re.I):
        m = hit
    return m.start() if m else at


def bring_forward(text):
    """(new_text, [ids added]). Nothing else in the page is touched."""
    added = []
    while True:
        for m in BOX.finditer(text):
            fid = m.group(3)
            if fid in added:
                continue
            if re.search(r'<\w+[^>]*\bid="%s"[^>]*>' % re.escape(fid),
                         text, re.I):
                continue                      # already has somewhere to be
            words = html.unescape(m.group(4)).strip()
            para = ('%s<p id="%s">%s</p>\n'
                    % (m.group(1), html.escape(fid, quote=True),
                       html.escape(words)))
            at = label_start(text, m.start())
            text = text[:at] + para + text[at:]
            added.append(fid)
            break
        else:
            return text, added


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    root = Path(argv[0])
    write = "--write" in argv
    if not root.is_dir():
        print("Not a folder: " + str(root))
        return 2
    touched = 0
    for p in sorted(root.rglob("*.html")):
        if any(part.startswith("_deleted") for part in p.relative_to(root).parts):
            continue
        was = p.read_text(encoding="utf-8", errors="replace")
        now, added = bring_forward(was)
        if not added:
            continue
        touched += 1
        print("%-42s %s" % (p.relative_to(root).as_posix(), ", ".join(added)))
        if write:
            p.write_text(now, encoding="utf-8", newline="")
    print(("changed " if write else "would change ") + str(touched) + " page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
