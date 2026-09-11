#!/usr/bin/env python3
"""Checks for ways.py - answering methods kept in a file, not in code."""

import re
import sys

import ways

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


FILE = ways.STARTER


# --- adding one by pasting from MDN ------------------------------------

MDN_EMAIL = '<input type="email" id="email" name="email" size="30">'

text, key, trouble = ways.add(FILE, "An email address",
                              "NVDA says: edit, blank.", MDN_EMAIL)
check("adding reported no trouble", trouble, "")
check("the key comes from the name", key, "an-email-address")
have = ways.load(text)
check("it is in the file", key in have, True)
check("the name is kept", have[key]["name"], "An email address")
check("how it reads is kept", have[key]["reads"], "NVDA says: edit, blank.")
check("what was pasted is kept exactly", have[key]["paste"], MDN_EMAIL)

again, key2, _ = ways.add(text, "An email address", "", MDN_EMAIL)
check("two with the same name do not collide", key2, "an-email-address-2")
check("both are there", len(ways.load(again)), 2)


# --- what must be refused ----------------------------------------------

check("a way with no name is refused",
      ways.add(FILE, "  ", "", MDN_EMAIL)[2] != "", True)
check("pasting nothing is refused",
      ways.add(FILE, "Thing", "", "   ")[2] != "", True)
check("pasting something with no box in it is refused",
      ways.add(FILE, "Thing", "", "<p>just words</p>")[2] != "", True)
check("pasting a script is refused",
      ways.add(FILE, "Thing", "", '<input type="text">'
               '<script>alert(1)</script>')[2] != "", True)


# --- using one on a question -------------------------------------------

built = ways.build(MDN_EMAIL, "work-email", "What is their email?")
check("the question becomes the label",
      "<label for=\"work-email-box\">What is their email?</label>" in built,
      True)
check("the box is given the question's id",
      'id="work-email-box"' in built, True)
check("the box is given the name the saving side looks for",
      'name="set-work-email"' in built, True)
check("the name that was pasted in is not kept",
      'name="email"' in built, False)
check("everything else pasted is left alone", 'size="30"' in built, True)
check("the type pasted is what is used", 'type="email"' in built, True)


# --- a paste whose parts point at each other ---------------------------

MDN_DATALIST = ('<input type="text" id="ice" name="ice" list="flavours">'
                '<datalist id="flavours">'
                '<option value="Vanilla"><option value="Plum">'
                '</datalist>')
pair = ways.build(MDN_DATALIST, "flavour", "Which one?")
check("the box gets the question's id", 'id="flavour-box"' in pair, True)
check("the other part is renamed too, not left to collide",
      'id="flavour-flavours"' in pair, True)
check("and what pointed at it was repointed",
      'list="flavour-flavours"' in pair, True)
check("nothing is left pointing at the pasted id",
      'list="flavours"' in pair, False)
check("the choices pasted survive", "Vanilla" in pair and "Plum" in pair, True)

second = ways.build(MDN_DATALIST, "other", "And this one?")
check("two questions using the same way share no ids at all",
      set(re.findall(r'id="([^"]*)"', pair))
      & set(re.findall(r'id="([^"]*)"', second)), set())


# --- a textarea and a select both work ---------------------------------

ta = ways.build('<textarea rows="8"></textarea>', "notes", "Notes?")
check("a textarea gets the name too", 'name="set-notes"' in ta, True)
check("a textarea with no id pasted still gets one",
      'id="notes-box"' in ta, True)
sel = ways.build('<select><option>a</option></select>', "pickone", "Which?")
check("a select gets the name too", 'name="set-pickone"' in sel, True)



# --- the sample data in an MDN example is not a default ---------------

MDN_MOMENT = ('<input type="datetime-local" id="meeting" '
              'name="meeting-time" value="2018-06-12T19:30">')
moment = ways.build(MDN_MOMENT, "when", "When is it?")
check("the example value is not left in as a default",
      "2018-06-12" in moment, False)
check("but the control itself is unchanged",
      'type="datetime-local"' in moment, True)
check("and it still gets its name",
      'name="set-when"' in moment, True)


print("\n".join("  ok   " + n for n in PASS))
if FAIL:
    print("\n".join("  FAIL " + n for n in FAIL))
print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
