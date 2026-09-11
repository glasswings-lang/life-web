# What this is

The one piece of a web page you cannot write in HTML.

HTML has no way to save anything. A form only *sends* what you typed to
an address — something has to be listening there to catch it. That is
all `Life_Web.exe` is.

It writes what your form sent into your HTML file. Your words end up in
the page itself. Open the file in Notepad and they are there. No
database. Nothing in the browser.

# Using it

Press Enter on **Life_Web.exe**. A window opens saying the address, and the
browser opens itself. Close the window to stop it.

Your pages are every `.html` file in this folder. It serves them exactly
as they are on disk and never rewrites them, except to put a new thing
in where you marked.

# The three things that go in your page

`index.html` is a small working example. It is yours — gut it, rename
it, start from scratch. Only these three matter.

**1. A form that points at the program.**

```html
<form method="post" action="/save">
  <label for="note">Note</label>
  <textarea id="note" name="note"></textarea>
  <input type="hidden" name="_to" value="index.html">
  <button type="submit">Save it</button>
</form>
```

`action="/save"` is what sends it somewhere instead of nowhere. The
hidden `_to` says which file to write into. Every other field is yours —
name them what you like, have as many as you want.

**2. A marker, where things should appear.**

```html
<!-- here -->
```

An ordinary comment. Browsers ignore it. New things go directly after
it, so the newest is at the top. Move it and they go to the new place.

**3. Optionally, the shape each saved thing takes.**

```html
<template>
  <div class="note">
    <h3>{when}</h3>
    <p>{note}</p>
  </div>
</template>
```

`<template>` is real HTML — browsers do not show what is inside one. The
program reads it and fills in the blanks. `{note}` is your field's name
from the form. `{when}` is always there.

Change it and the next thing you save comes out the new way. Things
already saved stay as they are, because they are already in your file.
Delete the template and you get a plain block instead.

# Two extra hidden fields, if you want them

- `_at` — use a different marker. `_at="other"` writes after
  `<!-- other -->`, so one page can have several places things go.
- `_back` — where to land afterwards. By default you land on the page it
  wrote to, so you are looking at what you just saved.

# Things worth knowing

**The note box takes plain typing, Markdown, or HTML.** Type `<b>hi</b>`
and it goes bold. `### A Section` is a level 3 heading, the way Markdown means
it. A line break you type stays a line break, and a blank line starts a
new paragraph. A heading typed in the middle of a paragraph is lifted out
of it, so the page keeps its shape.

What stays as visible text is anything that would make the page *do*
something rather than *say* something: scripts, style blocks, frames,
`onclick` and friends, and links that are really instructions. You can
see it wasn't taken, instead of it quietly vanishing.

**Do not put the literal tag inside a comment.** A comment that mentions the
template tag *with its angle brackets* gets found before the real
element below it. The
program strips comments before looking, so this is handled — but it bit
twice while building this, so it is worth knowing the shape of.

**It only listens to this computer.** Nothing is reachable from outside.

**If it cannot save, it says why and changes nothing** — a missing
marker, a file that is not there, a form with no `_to`. Your page is
never left half-written; new text goes to a temporary file first and is
swapped in only once complete.

# Files here

- `Life_Web.exe` — the program. This is the only thing you run.
- `index.html` — the example. Yours to change or delete.
- `LICENSE` — CC0. Do what you like with this, no permission needed.
- `DESIGN.md` — how it is built and, more usefully, *why*. The decisions
  in it were arrived at by using the thing, so re-deciding them tends to
  cost more than keeping them. Read it before changing how anything
  works.
- The program as source: `forms.py` is the server, `wiki.py` pages and
  links inside sentences, `links.py` addresses and repairs, `kinds.py`
  the shape a repeated thing takes, `editing.py` changing words already
  on a page, `markup.py` and `ways.py` the small pieces underneath.
- `bring_fields_forward.py` — a one-off for folders made before written
  answers had somewhere to show. Says what it would do unless you pass
  `--write`.
- `test_*.py` — seven files, 358 checks. Run one with
  `python test_wiki.py`. Each builds its own throwaway folder, so your
  pages are never touched.

# If the source changes

```
python -m PyInstaller Life_Web.spec --noconfirm
```

Needs `pip install pyinstaller`. The spec is what the build actually
uses, so prefer it over a hand-written command. **Editing your HTML
never needs any of this** — the program reads your files off disk every
time.
