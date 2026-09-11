"""Checks forms.py works. Run it any time:

    python test_forms.py

Works in a throwaway folder, so your own pages are never touched.
Prints a line per check and ends with ALL PASSED or what broke.
"""
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = HERE / ".test-run"
PORT = 8788
BASE = "http://127.0.0.1:%d" % PORT
fails = []


def check(label, ok, detail=""):
    label = str(label).encode("ascii", "backslashreplace").decode("ascii")
    print(("  ok   " if ok else "  FAIL ") + label
          + (("\n         " + str(detail)[:300]) if detail and not ok else ""))
    if not ok:
        fails.append(label)


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.status, r.read()


def save(pairs):
    data = urllib.parse.urlencode(pairs).encode()
    with urllib.request.urlopen(BASE + "/save", data=data, timeout=10) as r:
        return r.read().decode()


def page(name="index.html"):
    return (T / name).read_text(encoding="utf-8")


PLAIN = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Plain</title></head>
<body>
<h1>Plain</h1>
<p>my own paragraph</p>
<!-- here -->
</body></html>
"""

TRAP = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Trap</title></head>
<body>
<h1>Trap</h1>
<!-- a note to myself mentioning <template> and </template> literally -->
<template><div class="real">{thing}</div></template>
<!-- here -->
</body></html>
"""

TWOSPOTS = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Two</title></head>
<body>
<h1>Two</h1>
<template><b>{thing}</b></template>
<h2>A</h2>
<!-- here -->
<h2>B</h2>
<!-- other -->
</body></html>
"""

# Its own fixture, NOT a copy of the real index.html. Copying the live
# page meant that the moment anything was saved into it for real, the
# test started failing on content it had no business knowing about. A
# check whose result depends on what someone happened to do that day
# guards nothing.
FIXTURE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Notes</title></head>
<body>
<h1>Notes</h1>
<form method="post" action="/save">
  <label for="note">Note</label>
  <textarea id="note" name="note" rows="4"></textarea>
  <input type="hidden" name="_to" value="index.html">
  <button type="submit">Save it</button>
</form>
<template>
  <div class="note">
    <h3>{when}</h3>
    <p>{note}</p>
  </div>
</template>
<h2>Saved notes</h2>
<p id="origin">Origin not yet recorded.</p>
<textarea id="origin-box" name="value" rows="2">Origin not yet recorded.</textarea>
<!-- here -->
</body></html>
"""

shutil.rmtree(T, ignore_errors=True)
T.mkdir(parents=True)
(T / "index.html").write_text(FIXTURE, encoding="utf-8")
(T / "plain.html").write_text(PLAIN, encoding="utf-8")
(T / "trap.html").write_text(TRAP, encoding="utf-8")
(T / "two.html").write_text(TWOSPOTS, encoding="utf-8")

proc = subprocess.Popen(
    [sys.executable, str(HERE / "forms.py"), "--folder", str(T),
     "--port", str(PORT), "--no-browser"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for _ in range(60):
    time.sleep(0.25)
    try:
        get("/")
        break
    except Exception:
        if proc.poll() is not None:
            print("DIED:\n" + proc.stdout.read())
            sys.exit(1)
else:
    proc.kill()
    print("never started")
    sys.exit(1)

try:
    print("\n-- your pages are handed over as they are on disk --")
    code, body = get("/index.html")
    on_disk = (T / "index.html").read_bytes()
    check("served", code == 200)
    # The tool links are added on the way out, and they are the ONLY
    # thing added. Everything else must match, and the file itself must
    # not be written to at all - that is the part that matters, because
    # it is what lets a page still work with nothing running.
    bare = body.replace(b'<a href="/search">Find something</a>', b"")
    bare = bare.replace(b'<a href="/flags">Loose ends</a>', b"")
    bare = re.sub(rb'<a href="/(edit|add|here)\?page=[^"]*">[^<]*</a>\s*', b"", bare)
    bare = re.sub(rb"<nav>\s*</nav>\s*", b"", bare)
    check("nothing but the tool links was added",
          b"".join(bare.split()) == b"".join(on_disk.split()))
    check("the tool links are there", b'href="/search"' in body)
    check("the file on disk was not written to",
          (T / "index.html").read_bytes() == on_disk)
    check("your comments survive the trip", b"<!--" in body)
    check("bare / gives index.html", get("/")[1] == body)

    print("\n-- saving, using the template in your own page --")
    before = page()
    save({"note": "a thing worth keeping", "_to": "index.html"})
    after = page()
    check("your words are in the file", "a thing worth keeping" in after)
    check("it used YOUR template's shape",
          '<div class="note">' in after and "<h3>" in after)
    check("it went in right after the marker",
          after.split("<!-- here -->")[1].lstrip().startswith('<div class="note">'))
    check("the marker survived for next time", "<!-- here -->" in after)
    delta = after
    for m in re.findall(r'\n<div class="note">.*?</div>', after, re.S):
        delta = delta.replace(m, "", 1)
    check("EVERY other byte of your page is untouched", delta == before)

    save({"note": "a second one", "_to": "index.html"})
    check("newest goes on top",
          page().index("a second one") < page().index("a thing worth keeping"))

    print("\n-- a comment that mentions a template must not win --")
    save({"thing": "landed", "_to": "trap.html"})
    t = page("trap.html")
    check("the real element was used, not the note-to-self",
          '<div class="real">landed</div>' in t, t)
    check("and nothing landed inside the comment",
          t.split("<!--")[1].split("-->")[0].count("landed") == 0)

    print("\n-- no template: a plain block, and your page still intact --")
    before = page("plain.html")
    save({"note": "no template here", "_to": "plain.html"})
    p = page("plain.html")
    check("saved anyway", "no template here" in p)
    check("as a plain block", '<div class="entry">' in p)
    check("your own paragraph untouched", "<p>my own paragraph</p>" in p)

    print("\n-- more than one field, and more than one spot --")
    save({"thing": "to A", "_to": "two.html"})
    save({"thing": "to B", "_to": "two.html", "_at": "other"})
    two = page("two.html")
    check("_at picks which marker",
          two.split("<!-- here -->")[1].split("<h2>B</h2>")[0].strip()
          == "<b>to A</b>"
          and two.split("<!-- other -->")[1].strip().startswith("<b>to B</b>"),
          two)
    save({"note": "n", "who": "w", "_to": "plain.html"})
    p = page("plain.html")
    check("every field gets written", ">note: n</p>" in p and ">who: w</p>" in p)

    print("\n-- what you type is shown, never run --")
    save({"note": '<script>alert(1)</script> & "quotes"', "_to": "plain.html"})
    p = page("plain.html")
    check("html you typed is escaped",
          "&lt;script&gt;alert(1)&lt;/script&gt;" in p
          and "<script>alert(1)" not in p)
    save({"note": "café naïve — ❤", "_to": "plain.html"})
    check("accents and emoji survive",
          "café naïve — ❤" in page("plain.html"))

    print("\n-- changing a field, rather than adding under it --")
    before = page()
    check("the field starts as the placeholder",
          '<p id="origin">Origin not yet recorded.</p>' in before)
    save({"value": "somewhere specific", "_to": "index.html",
          "_set": "origin"})
    after = page()
    check("the field was replaced, not appended to",
          '<p id="origin">somewhere specific</p>' in after)
    check("the old value is gone", "Origin not yet recorded" not in after)
    check("nothing else on the page changed",
          after.replace("somewhere specific", "Origin not yet recorded.")
          == before)
    check("the edit box was updated too, so it is not left stale",
          '<textarea id="origin-box" name="value" rows="2">somewhere '
          'specific</textarea>' in after, after[after.find("<textarea"):][:120])
    save({"value": "changed again", "_to": "index.html", "_set": "origin"})
    check("and it can be changed again",
          '<p id="origin">changed again</p>' in page())
    check("what you type is still escaped",
          (save({"value": "<b>x</b>", "_to": "index.html", "_set": "origin"})
           or True) and "&lt;b&gt;x&lt;/b&gt;" in page())

    before = page()
    out = save({"value": "x", "_to": "index.html", "_set": "nosuchfield"})
    check("a field that does not exist is explained",
          "nothing with the id" in re.sub(r"<[^>]+>", " ", out))
    check("and the page is untouched", page() == before)

    print("\n-- a form-shaped page: only boxes, no display elements --")
    # The fixture above has both a <p> and a box for its field, which is
    # more generous than a real page. A page built as a form has ONLY
    # the boxes, and requiring the display element meant nothing could
    # ever be saved into one.
    (T / "formshaped.html").write_text("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Form</title></head>
<body>
<h1>Form</h1>
<form method="post" action="/save">
  <input type="hidden" name="_to" value="formshaped.html">
  <label for="f-where-box">Where</label>
  <textarea id="f-where-box" name="set-f-where" rows="2"></textarea>
  <label for="f-when-box">When</label>
  <input type="date" id="f-when-box" name="set-f-when" value="">
  <button type="submit">Save details</button>
</form>
<!-- here -->
</body></html>
""", encoding="utf-8")
    save({"_to": "formshaped.html", "set-f-where": "Second Place",
          "set-f-when": "2026-03-04"})
    f = page("formshaped.html")
    check("both fields saved in ONE press",
          ">Second Place</textarea>" in f and 'value="2026-03-04"' in f, f)
    save({"_to": "formshaped.html", "set-f-where": "changed"})
    f = page("formshaped.html")
    check("one field can be changed without clearing the other",
          ">changed</textarea>" in f and 'value="2026-03-04"' in f, f)

    print("\n-- a yes/no tickbox --")
    (T / "tick.html").write_text("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Tick</title></head>
<body>
<h1>Tick</h1>
<form method="post" action="/save">
  <input type="hidden" name="_to" value="tick.html">
  <label for="f-good-box">Was it good</label>
  <input type="checkbox" id="f-good-box" name="set-f-good" value="Yes">
  <p id="f-good">No</p>
  <button type="submit">Save</button>
</form>
<!-- here -->
</body></html>
""", encoding="utf-8")
    save({"_to": "tick.html", "set-f-good": "Yes"})
    t = page("tick.html")
    check("the paragraph says Yes", '<p id="f-good">Yes</p>' in t)
    check("and the box is actually ticked", "checked>" in t, t)
    # untick: an unticked checkbox sends nothing at all, so the form
    # carries the field with an empty value instead.
    save({"_to": "tick.html", "set-f-good": ""})
    t = page("tick.html")
    check("unticking says No", '<p id="f-good">No</p>' in t)
    check("and clears the tick", "checked" not in t, t)

    print("\n-- when it cannot save, it says why and changes nothing --")
    (T / "nomark.html").write_text(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>x</title></head><body><h1>x</h1></body></html>",
        encoding="utf-8")
    before = page("nomark.html")
    out = save({"note": "nowhere", "_to": "nomark.html"})
    # The marker is escaped in the page, as it must be, so read the words
    # the way a person would rather than looking for raw markup.
    said = re.sub(r"<[^>]+>", " ", out)
    said = __import__("html").unescape(re.sub(r"\s+", " ", said)).strip()
    check("says the marker is missing", "has no <!-- here --> in it" in said,
          said[:200])
    check("and tells you what to do", "Add that comment line" in said)
    check("your page is untouched", page("nomark.html") == before)

    out = save({"note": "x", "_to": "does-not-exist.html"})
    check("a file that is not there is explained",
          "not say which file" in out or "not here" in out, out[:300])
    out = save({"note": "x"})
    check("a form with no _to is explained", "_to" in out, out[:300])

    print("\n-- an empty box saves nothing --")
    before = page("plain.html")
    save({"note": "   ", "_to": "plain.html"})
    check("really nothing", page("plain.html") == before)

    print("\n-- it cannot write outside your folder --")
    before = (HERE / "forms.py").read_bytes()
    save({"note": "x", "_to": "../forms.py"})
    check("refused", (HERE / "forms.py").read_bytes() == before)
    for bad in ("/../forms.py", "/nope.html"):
        try:
            get(bad)
            check("refused: " + bad, False)
        except urllib.error.HTTPError as e:
            check("refused: " + bad, e.code == 404)

    print("\n-- every page is still valid standalone HTML --")
    for f in sorted(T.glob("*.html")):
        t = f.read_text(encoding="utf-8")
        check("well formed: " + f.name,
              t.lstrip().lower().startswith("<!doctype html>")
              and t.count("<html") == 1 and t.count("</html>") == 1
              and t.count("<body") == 1 and t.count("</body>") == 1)

finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    shutil.rmtree(T, ignore_errors=True)

print("\n" + ("ALL PASSED" if not fails else "FAILURES: " + repr(fails)))
sys.exit(1 if fails else 0)
