#!/usr/bin/env python3
"""Checks for kinds.py, and a guard against a corruption that has now
happened twice.

options_of could not read a fixed-list question's options for as long
as anyone knows. Its patterns had a literal backspace character where a
word boundary was meant - the two look identical in most editors, and a
pattern demanding a control character in the middle of ordinary HTML
simply never matches. It failed by returning an empty list, which reads
exactly like a question that has no options yet, so nothing ever looked
wrong.

It got there the way these things do: a shell heredoc that swallowed one
backslash while a file was being edited. That is not a thing a person
can be careful enough about, so it is checked for instead.

    python tests/test_kinds.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kinds  # noqa: E402

PASS, FAIL = [], []


def check(name, got, want):
    (PASS if got == want else FAIL).append(name)
    if got != want:
        print("  FAIL %s\n       got  %r\n       want %r" % (name, got, want))


# --- a fixed-list question can be read back ---------------------------
for key in ("drop", "checks", "choice"):
    tpl = kinds.field_block("f-mood", "Mood", key, options=["Calm", "Loud"])
    check("options come back for a '%s' question" % key,
          kinds.options_of(tpl, "f-mood"), ["Calm", "Loud"])

check("a question with no options gives an empty list",
      kinds.options_of(kinds.field_block("f-said", "Said", "long"), "f-said"),
      [])

# --- no source file may carry a stray control character ---------------
# Tab, newline and carriage return are ordinary. Anything else in a
# source file arrived by accident, and a backspace inside a regular
# expression is invisible and fatal.
ALLOWED = {9, 10, 13}
for f in sorted(pathlib.Path(__file__).resolve().parent.glob("*.py")):
    text = f.read_text(encoding="utf-8")
    stray = sorted({ord(c) for c in text if ord(c) < 32 and ord(c) not in ALLOWED})
    check("%s has no stray control characters" % f.name, stray, [])

print()
print("\n".join("  ok   " + n for n in PASS))
print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
