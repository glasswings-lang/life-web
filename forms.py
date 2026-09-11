#!/usr/bin/env python3
"""Makes forms on your own HTML pages actually save something.

HTML cannot write files. A form only sends what you typed to an address -
something has to be listening at that address to catch it. This is that
something, and it is the only part you cannot write in HTML yourself.

What it does: takes what the form sent and writes it into your HTML file,
at a spot you marked. Your words end up in the page. Open the file in
Notepad and they are there. No database, nothing in the browser.

Three things go in your page:

  1.  <!-- here -->        a comment, marking where new things go
  2.  a form whose action is /save, with a hidden field _to naming
      the file to write into
  3.  optionally a <template>, saying what shape each saved thing takes

Everything else in the page is yours and is never touched.

Run it, open http://127.0.0.1:8787/, and your forms work.
Stop it with Ctrl+C, or by closing the window.
"""

import argparse
import html
import os
import re
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import kinds
import links
import editing
import markup
import ways
import wiki

DEFAULT_PORT = 8787

# Frozen into an exe, __file__ points inside a temp folder Windows
# deletes on exit. Your pages must be found next to the exe instead.
HERE = (Path(sys.executable) if getattr(sys, "frozen", False)
        else Path(__file__)).resolve().parent

STAMP = "%Y-%m-%d %H:%M"

TEMPLATE_RE = re.compile(r"<template[^>]*>(.*?)</template>", re.S | re.I)

# Comments are stripped before looking for the template. Without this, a
# comment that MENTIONS the template element gets found instead of the
# real one, and the note lands in the middle of your own notes-to-self.
# Only ever stripped from a copy - your file keeps its comments.
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)

# The <p> a template wraps a note in. Replaced whole, not filled,
# because what goes in is now block-level HTML.
NOTE_P_RE = re.compile(r"<p>\s*\{note\}\s*</p>", re.I)

TYPES = {
    ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".txt": "text/plain; charset=utf-8", ".md": "text/plain; charset=utf-8",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
    ".ico": "image/x-icon",
}


def folder():
    HERE.mkdir(parents=True, exist_ok=True)
    return HERE


LOG_NAME = "Life_Web.log"


def log(line):
    """Write one line to Life_Web.log, next to the exe.

    Because a program that has stopped and a program that has crashed
    look exactly the same from a browser: every link dead, no message,
    nothing to read. Without this there is no way to tell them apart
    afterwards, which is guessing rather than answering.

    Never raises. A logger that can take the program down is worse than
    no logger.
    """
    try:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(HERE / LOG_NAME, "a", encoding="utf-8",
                  newline="\n") as fh:
            fh.write(stamp + "  " + str(line).rstrip() + "\n")
    except Exception:
        pass


def read_text(path):
    """Read without ever raising on odd encodings."""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return None
    for enc in ("utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def write_text(path, text):
    """Write to a temp file, then swap it in.

    Your page is the only copy of what you have written. A half-written
    file is worse than a failed write, so the real one is only replaced
    once the new one is complete on disk.
    """
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


def ways_file():
    """The ways-to-answer file, made the first time it is looked for."""
    path = folder() / ways.WAYS_FILE
    if not path.is_file():
        write_text(path, ways.STARTER)
    return path


def your_ways():
    """Whatever is in it right now. Read every time, never cached."""
    return ways.load(read_text(ways_file()) or "")


def safe(name):
    """A path inside your folder, or None if it points outside it."""
    if not name or "\\" in name or name.startswith("/"):
        return None
    try:
        p = (folder() / name).resolve()
        p.relative_to(folder().resolve())
    except (ValueError, OSError):
        return None
    return p


def shape_from(page_text, values, top=2):
    """Build the block to insert.

    Uses the <template> in your own page if there is one, so the shape is
    something you wrote and can change. {when} and {yourfieldname} are
    filled in. Plain str.replace, so a stray brace never breaks anything;
    a {blank} you invented with no matching field stays visible, which is
    how you find out it is not a real one.

    With no template you get a plain block, one line per field. That is a
    fallback, not a design - write a template and it is yours.
    """
    m = TEMPLATE_RE.search(COMMENT_RE.sub("", page_text or ""))
    if m:
        block = m.group(1).strip()

        # What you typed in the note box is turned into real HTML -
        # paragraphs, headings, lists. That is block-level markup, so it
        # cannot go inside the template's <p>: the <p>{note}</p> is
        # replaced entirely rather than filled. Templates that were
        # written before any of this keep working, which is why it is
        # done by swapping the wrapper instead of asking every page to
        # be edited.
        if "note" in values:
            body = markup.to_html(values["note"], top)
            if NOTE_P_RE.search(block):
                block = NOTE_P_RE.sub(lambda _m: body, block, count=1)
            else:
                block = block.replace("{note}", body)

        for key in sorted(values, key=len, reverse=True):
            block = block.replace("{" + key + "}", html.escape(values[key]))
        return block

    lines = ['<div class="entry">',
             '<p class="when">' + html.escape(values["when"]) + "</p>"]
    for key, value in values.items():
        if key == "when":
            continue
        lines.append("<p>" + html.escape(key) + ": "
                     + html.escape(value) + "</p>")
    lines.append("</div>")
    return "\n".join(lines)


def insert(path, marker, block, before=False):
    """Put the block next to the marker. Nothing else changes.

    After the marker (the default) means newest first, which is right
    for a log of notes. Before it means newest last, which is right for
    anything with an order to keep - a form's fields have to read back
    in the order they were defined, not in reverse.
    """
    text = read_text(path)
    if text is None:
        return "That file could not be read."
    if marker not in text:
        return ("That page has no " + marker + " in it, so there is nowhere "
                "to put this. Add that comment line where you want things "
                "to appear.")
    block = block.strip("\n")
    if before:
        at = text.index(marker)
        new = text[:at] + block + "\n" + text[at:]
    else:
        at = text.index(marker) + len(marker)
        new = text[:at] + "\n" + block + text[at:]
    if not write_text(path, new):
        return "That file could not be written to."
    return ""


def set_field(path, field_id, value):
    """Replace what is inside one element, found by its id.

    This is the only thing here that OVERWRITES rather than adds, so it
    is deliberately narrow: it will only touch an element you gave an id
    to, it replaces the contents and not the tag, and it leaves every
    other byte of the file alone.
    """
    text = read_text(path)
    if text is None:
        return "That file could not be read."

    # A field can show up on a page in up to three ways, and any of them
    # on its own is enough. Requiring the first one is what broke this:
    # a form-shaped page has only the box, no separate display element,
    # so nothing could ever be saved into it.
    esc = re.escape(field_id)
    new_text, hits = text, 0

    def swap(pattern, group, replacement):
        nonlocal new_text, hits
        m = re.search(pattern, new_text, re.S | re.I)
        if m:
            new_text = (new_text[:m.start(group)] + replacement
                        + new_text[m.end(group):])
            hits += 1

    # A tickbox has to be spotted FIRST, because its state is an
    # attribute being present or not, and because an unticked box sends
    # nothing at all - so the value arrives empty and has to be read as
    # "No" rather than written into the page as a blank.
    tick = re.search(r'<input[^>]*\btype="checkbox"[^>]*\bid="%s-box"[^>]*>'
                     % esc, new_text, re.I)
    if tick:
        on = value.strip().lower() in ("yes", "on", "true", "1")
        tag = re.sub(r"\s+checked\b", "", tick.group(0), flags=re.I)
        if on:
            tag = tag[:-1].rstrip() + " checked>"
        new_text = new_text[:tick.start()] + tag + new_text[tick.end():]
        hits += 1
        value = "Yes" if on else "No"

    # 1. an element that displays it - UNLESS what it already shows says
    # the same thing in a richer way. The box can only hold flat text, so
    # copying it over a paragraph containing links would throw the links
    # away every time Save was pressed, without anything being edited.
    # Same words means nothing was changed, so nothing needs writing.
    shown = re.search(r'<(\w+)[^>]*\bid="%s"[^>]*>(.*?)</\1>' % esc,
                      new_text, re.S | re.I)
    if shown and links.plain(shown.group(2)) == " ".join(value.split()):
        hits += 1                      # found, deliberately left as it is
    else:
        swap(r'<(\w+)[^>]*\bid="%s"[^>]*>(.*?)</\1>' % esc, 2,
             html.escape(value))
    # 2. the textarea you edit it in
    swap(r'<textarea[^>]*\bid="%s-box"[^>]*>(.*?)</textarea>' % esc, 1,
         html.escape(value))
    # 3. or an ordinary <input>, which carries its value in an attribute
    if not tick:
        swap(r'<input[^>]*\bid="%s-box"[^>]*\bvalue="([^"]*)"' % esc, 1,
             html.escape(value, quote=True))

    if not hits:
        return ("This page has nothing with the id " + field_id
                + " in it, so there is no field of that name to change.")
    if not write_text(path, new_text):
        return "That file could not be written to."
    return ""


def kind_entries(kind_slug):
    """[(filename, title), ...] of one kind, read off disk right now."""
    d = safe(kind_slug)
    if d is None or not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("*.html")):
        if f.name == "index.html" or f.name.startswith("_"):
            continue
        t = read_text(f) or ""
        m = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S | re.I)
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() \
            if m else f.stem
        out.append((f.name, title or f.stem))
    return out


FORM_RE = r'<form\b[^>]*action="%s".*?</form>'


def swap_form(page_text, fresh_text, action):
    """Replace one form with the current version of that same form.

    Nothing else in the page is looked at, let alone written.
    """
    want = FORM_RE % re.escape(action)
    new = re.search(want, fresh_text, re.S | re.I)
    if not new:
        return page_text
    if not re.search(want, page_text, re.S | re.I):
        return page_text
    return re.sub(want, lambda _m: new.group(0), page_text, count=1,
                  flags=re.S | re.I)


def refresh_kind_indexes():
    """Bring every kind's index page up to the current shape.

    ONLY the two forms this program put there are replaced - the one
    that adds an entry and the one that adds a question - plus the
    version stamp. Every other byte of the page is left exactly as it
    is.

    It used to rebuild the whole file, on the reasoning that the page
    was entirely made here so nothing of yours could be lost. That is
    only true while you never write on it. Write a paragraph at the top
    of a kind's index and the next version bump would eat it, silently,
    at startup. The page is yours; this touches its machinery and
    nothing else.
    """
    rebuilt = []
    for d in sorted(folder().iterdir()):
        if not (d.is_dir() and (d / "_kind.html").is_file()):
            continue
        idx = d / "index.html"
        old = read_text(idx)
        if old is None or kinds.INDEX_VERSION in old:
            continue                      # missing, or already current
        m = re.search(r"<h1[^>]*>(.*?)</h1>", old, re.S | re.I)
        name = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() \
            if m else d.name
        _tpl, fresh = kinds.new_kind_files(name or d.name, d.name,
                                           your_ways())

        new = swap_form(old, fresh, "/new")
        new = swap_form(new, fresh, "/newfield")
        stamp = re.search(r"<!-- kind index \d+ -->", new)
        if stamp:
            new = new.replace(stamp.group(0), kinds.INDEX_VERSION, 1)
        else:
            new = new.replace("<!doctype html>",
                              "<!doctype html>\n" + kinds.INDEX_VERSION, 1)
        if new != old and write_text(idx, new):
            rebuilt.append(d.name)
    return rebuilt


def all_kinds():
    """Every kind on disk. There is no list of these in the code."""
    out = []
    for d in sorted(folder().iterdir()):
        if d.is_dir() and (d / "_kind.html").is_file():
            t = read_text(d / "index.html") or ""
            m = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S | re.I)
            name = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() \
                if m else d.name
            out.append((d.name, name or d.name))
    return out


def is_option_field(path, field_id):
    """Is this question a fixed list of words rather than links?"""
    text = read_text(path) or ""
    esc = re.escape(field_id)
    if re.search(r'<fieldset[^>]*\bdata-options="%s"' % esc, text, re.I):
        return True
    sel = re.search(r'<select[^>]*\bname="set-%s"[^>]*>' % esc, text, re.I)
    return bool(sel and "data-kind=" not in sel.group(0))


def pick_kind_of(path, field_id):
    """Which kind a question points at.

    Two places to look, because picking ONE is a combo box and picking
    SEVERAL is a group of checkboxes in a fieldset. Only checking the
    combo box meant "or a new one called" silently did nothing on every
    checkbox question.
    """
    text = read_text(path) or ""
    esc = re.escape(field_id)
    m = re.search(r'<select[^>]*\bname="set-%s"[^>]*\bdata-kind="([^"]*)"'
                  % esc, text, re.I)
    if m:
        return m.group(1)
    m = re.search(r'<fieldset[^>]*\bdata-kind="([^"]*)"[^>]*\bdata-for="%s"'
                  % esc, text, re.I)
    return m.group(1) if m else ""


def set_choices(path, field_id, values):
    """Record which words of a fixed list were chosen.

    Radio buttons and checkboxes carry their state as an attribute being
    present, and a dropdown as `selected`, so each option has to be
    ticked or cleared individually - there is no single value to write.
    The paragraph beside them holds the answer in words, which is what
    keeps the file readable with nothing running.
    """
    text = read_text(path)
    if text is None:
        return "That file could not be read."
    chosen = {v for v in values if v.strip()}
    esc = re.escape(field_id)

    def tickbox(m):
        tag = re.sub(r"\s+checked\b", "", m.group(0), flags=re.I)
        val = re.search(r'\bvalue="([^"]*)"', tag)
        if val and html.unescape(val.group(1)) in chosen:
            tag = tag[:-1].rstrip() + " checked>"
        return tag

    def option(m):
        tag = re.sub(r"\s+selected\b", "", m.group(0), flags=re.I)
        val = re.search(r'\bvalue="([^"]*)"', tag)
        if val and html.unescape(val.group(1)) in chosen:
            tag = tag[:-1].rstrip() + " selected>"
        return tag

    new = re.sub(r'<input[^>]*\bname="set-%s"[^>]*>' % esc, tickbox, text,
                 flags=re.I)
    sel = re.search(r'<select[^>]*\bname="set-%s"[^>]*>.*?</select>' % esc,
                    new, re.S | re.I)
    if sel:
        block = re.sub(r"<option[^>]*>", option, sel.group(0), flags=re.I)
        new = new[:sel.start()] + block + new[sel.end():]

    body = html.escape(", ".join(sorted(chosen))) or "Not yet recorded."
    pat = re.compile(r'(<(\w+)[^>]*\bid="%s"[^>]*>)(.*?)(</\2>)' % esc,
                     re.S | re.I)
    m = pat.search(new)
    if m:
        new = new[:m.start(3)] + body + new[m.end(3):]
    if not write_text(path, new):
        return "That file could not be written to."
    return ""


def link_to(href):
    """A real <a href> to a page, with that page's own title as its text."""
    target = safe(re.sub(r"^(\.\./)+", "", href))
    if target is None or not target.is_file():
        return None
    t = read_text(target) or ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S | re.I)
    title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() \
        if m else target.stem
    return '<a href="%s">%s</a>' % (html.escape(href, quote=True),
                                    html.escape(title or target.stem))


def set_links(path, field_id, hrefs):
    """Put several real links into the field's paragraph.

    Several, because a thing can be part of more than one thing at once
    - which is the whole point of a category that cuts across kinds. It
    is still ordinary links in an ordinary page, not rows in a table.
    """
    links = [link_to(h) for h in hrefs if h.strip()]
    bad = [h for h, l in zip([h for h in hrefs if h.strip()], links)
           if l is None]
    if bad:
        return "Some of those point at pages that are not there."
    body = ", ".join(l for l in links if l) or "Nothing chosen yet."
    text = read_text(path)
    if text is None:
        return "That file could not be read."
    pat = re.compile(r'(<(\w+)[^>]*\bid="%s"[^>]*>)(.*?)(</\2>)'
                     % re.escape(field_id), re.S | re.I)
    m = pat.search(text)
    if not m:
        return "This page has nothing with the id " + field_id + " in it."
    if not write_text(path, text[:m.start(3)] + body + text[m.end(3):]):
        return "That file could not be written to."
    return ""


def set_link(path, field_id, href):
    """Put a real <a href> into the field's paragraph.

    A pick stores an ordinary link, not an id into a table. That is what
    keeps the file a real page: open it with nothing running and the
    link still goes where it says.
    """
    href = href.strip()
    target = safe(re.sub(r"^\.\./", "", href))
    if not href:
        return set_field(path, field_id, "Nothing chosen yet.")
    if target is None or not target.is_file():
        return "That points at a page that is not there."
    t = read_text(target) or ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S | re.I)
    title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() \
        if m else target.stem
    link = '<a href="%s">%s</a>' % (html.escape(href, quote=True),
                                    html.escape(title or target.stem))
    text = read_text(path)
    if text is None:
        return "That file could not be read."
    pat = re.compile(r'(<(\w+)[^>]*\bid="%s"[^>]*>)(.*?)(</\2>)'
                     % re.escape(field_id), re.S | re.I)
    m2 = pat.search(text)
    if not m2:
        return ("This page has nothing with the id " + field_id + " in it.")
    new = text[:m2.start(3)] + link + text[m2.end(3):]
    if not write_text(path, new):
        return "That file could not be written to."
    return ""


def points_at(rel_path):
    """[(href, title, kind), ...] - every page whose links reach this one.

    Reads the other files each time it is asked. Nothing is indexed and
    nothing is cached, so it is right the moment after you change
    something, and there is no list anywhere that can rot.
    """
    target = rel_path.replace("\\", "/")
    tail = "/" + target.rsplit("/", 1)[-1]
    out = []
    for kind_slug, kind_name in all_kinds():
        for filename, title in kind_entries(kind_slug):
            here = kind_slug + "/" + filename
            if here == target:
                continue
            text = read_text(safe(here)) or ""
            for href in re.findall(r'<a href="([^"]+)"', text):
                cleaned = re.sub(r"^(\.\./)+", "", href)
                if cleaned == target or href.endswith(tail) and cleaned == target:
                    depth = target.count("/")
                    out.append(("../" * depth + here, title, kind_name))
                    break
    out.sort(key=lambda r: (r[2].lower(), r[1].lower()))
    return out


def make_kind(name):
    """A new kind: a folder, the shape its pages take, and its index."""
    name = name.strip()
    s = kinds.slug(name)
    if not s:
        return None, "That name had no letters or numbers in it."
    d = safe(s)
    if d is None:
        return None, "That name cannot be used for a folder."
    if d.exists():
        return s, "There is already a kind called that."
    template, index = kinds.new_kind_files(name, s, your_ways())
    try:
        d.mkdir(parents=True)
    except OSError:
        return None, "That folder could not be made."
    if not (write_text(d / "_kind.html", template)
            and write_text(d / "index.html", index)):
        return None, "Those files could not be written."
    insert(folder() / "index.html", kinds.MARK_KINDS,
           kinds.kind_row(s, name, 0))
    return s, ""


def add_field(kind_slug, question, type_key, target_kind="",
              options=None):
    """Add a question to a kind. Every page made after this has it."""
    question = question.strip()
    if not question:
        return "The question was empty."
    fid = "f-" + kinds.slug(question)
    if fid == "f-":
        return "That question had no letters or numbers in it."
    tpl = safe(kind_slug + "/_kind.html")
    if tpl is None or not tpl.is_file():
        return "There is no kind called " + kind_slug + "."
    if 'name="set-%s"' % fid in (read_text(tpl) or ""):
        return "That kind already asks that question."
    # before=True so questions read back in the order they were added.
    trouble = insert(tpl, kinds.MARK_FIELDS,
                     kinds.field_block(fid, question, type_key, target_kind,
                                       options, your_ways()),
                     before=True)
    return trouble


def edit_field(kind_slug, field_id, question, type_key,
               remove=False, options=None):
    """Reword a question, change its answer type, or drop it.

    Changes the kind's shape, so it affects pages made from here on.
    Pages that already exist keep the fields they were made with -
    nothing already written gets rewritten underneath you.
    """
    tpl = safe(kind_slug + "/_kind.html")
    if tpl is None or not tpl.is_file():
        return "There is no kind called " + kind_slug + "."
    text = read_text(tpl) or ""
    found = [q for q in kinds.questions_in(text) if q[0] == field_id]
    if not found:
        return "That kind has no question with that id."

    block = kinds.find_block(text, field_id)
    if block is None:
        return "Could not find that question in the kind's shape."
    start, end = block

    if remove:
        new = text[:start].rstrip("\n") + "\n" + text[end:].lstrip("\n")
    else:
        question = question.strip() or found[0][1]
        target = kinds.target_of(text, field_id)
        opts = (options if options is not None
                else kinds.options_of(text, field_id))
        fresh = kinds.field_block(field_id, question, type_key,
                                  target, opts, your_ways())
        new = text[:start] + fresh + "\n" + text[end:].lstrip("\n")

    if not write_text(tpl, new):
        return "That file could not be written to."
    return ""


def new_entry(kind_slug, name):
    """A page of a kind, from that kind's shape."""
    name = name.strip()
    s = kinds.slug(name)
    if not s:
        return None, "That name had no letters or numbers in it."
    tpl = safe(kind_slug + "/_kind.html")
    if tpl is None or not tpl.is_file():
        return None, "There is no kind called " + kind_slug + "."
    rel = kind_slug + "/" + s + ".html"
    dest = safe(rel)
    if dest is None:
        return None, "That name cannot be used for a file."
    if dest.exists():
        return rel, "There is already one called that."
    body = read_text(tpl) or ""
    # {name} and {to} are filled now; {when} and {note} are left alone,
    # because those belong to the <template> and get filled at save time.
    body = body.replace("{name}", html.escape(name))
    body = body.replace("{to}", html.escape(rel, quote=True))
    if not write_text(dest, body):
        return None, "That page could not be written."
    insert(safe(kind_slug + "/index.html"), kinds.MARK_ENTRIES,
           kinds.entry_row(s + ".html", name))
    return rel, ""


def problem_page(message, back):
    return ('<!doctype html>\n<html lang="en">\n<head>'
            '<meta charset="utf-8"><title>Not saved</title></head>\n<body>\n'
            "<h1>Not saved</h1>\n<p>" + html.escape(message) + "</p>\n"
            '<p><a href="' + html.escape(back, quote=True) + '">Go back</a>'
            "</p>\n</body>\n</html>\n").encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "Life_Web/1.0"

    def log_message(self, fmt, *args):
        pass

    def handle_one_request(self):
        """Every request passes through here.

        Anything that goes wrong is written down rather than vanishing,
        because from a browser a crashed program and a stopped one look
        identical.
        """
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except Exception:
            import traceback
            log("ERROR handling " + str(getattr(self, "path", "?")))
            for line in traceback.format_exc().splitlines():
                log("  " + line)
            raise

    def log_error(self, fmt, *args):
        try:
            log("request problem: " + (fmt % args))
        except Exception:
            pass

    def send(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def go(self, where):
        self.send_response(303)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def missing(self, name):
        """Not found, with a way out of it.

        A dead end used to be the end: the page said the file was not
        there and left you standing on it. That is fine if you write
        HTML and will go and make one. It is the end of the road if you
        do not, and the people this is for are people who want to write
        about their lives, not people who want to hand-write a page that
        will load in a browser. An empty folder was the worst of it -
        the program started, said Not found, and there was nothing
        anywhere to press.

        So the offer sits at the dead end, with the truth beside it:
        this makes a NEW page. If something used to be here that is a
        different problem, and the ways to chase it are listed rather
        than hinted at.
        """
        rel = (name or "index.html").strip("/")
        top = rel == "index.html"
        title = rel.rsplit("/", 1)[-1]
        for end in (".html", ".htm"):
            if title.lower().endswith(end):
                title = title[:-len(end)]
        title = title.replace("-", " ").replace("_", " ").strip() or "Everything"

        if top:
            offer = ("<p>There is no front page in this folder yet, so there "
                     "is nothing to show. Pressing this makes one, and puts "
                     "the stylesheet every page asks for beside it. It is an "
                     "ordinary HTML file afterwards: change it, rewrite it, "
                     "throw it away and write your own.</p>")
            button = "Make me a starting page"
        else:
            offer = ("<p>Pressing this makes a page at that address, with "
                     "somewhere to write on it. The link that brought you "
                     "here will work afterwards.</p>")
            button = "Make this page"

        body = (
            "<p>There is no page at <strong>" + html.escape(rel)
            + "</strong>.</p>\n" + offer
            + '\n<form method="post" action="/makepage">\n'
            '<input type="hidden" name="rel" value="'
            + html.escape(rel, quote=True) + '">\n'
            '<input type="hidden" name="title" value="'
            + html.escape(title, quote=True) + '">\n'
            "<button type=\"submit\">" + button + "</button>\n</form>\n"
            "<h2>If there used to be a page here</h2>\n"
            "<p>Making one now will not bring the old words back; it will be "
            "a new, empty page. If you had something here, one of these will "
            "find it:</p>\n<ul>\n"
            '<li>If you moved or renamed it, <a href="/repairs">Repairs</a> '
            "can move it back, or point whatever was linking at it somewhere "
            "else.</li>\n"
            '<li>If you remember any of the words in it, '
            '<a href="/search">Find something</a> reads every page each time '
            "you ask.</li>\n"
            "<li>If you put it away, it is in the <code>_deleted</code> "
            "folder beside your pages. Nothing is destroyed; getting it back "
            "is moving the file out again.</li>\n"
            "<li>If you moved it by hand outside the program, putting it back "
            "where it was is enough - this page will simply be here "
            "again.</li>\n"
            "</ul>\n")
        self.send(wiki.frame("Not found", body).encode("utf-8"),
                  TYPES[".html"], 404)

    def do_GET(self):
        route = urlparse(self.path).path
        if route in ("/repairs", "/repairs/"):
            said = parse_qs(urlparse(self.path).query).get("said", [""])[0]
            self.send(links.repairs_page(folder().resolve(),
                                         said).encode("utf-8"),
                      TYPES[".html"])
            return

        if route in ("/search", "/search/"):
            q = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            self.send(wiki.search_page(folder().resolve(), q).encode("utf-8"),
                      TYPES[".html"])
            return

        if route in ("/here", "/here/", "/remove", "/remove/"):
            q = parse_qs(urlparse(self.path).query)
            rel = q.get("page", [""])[0]
            said = q.get("said", [""])[0]
            if safe(rel) is None or not safe(rel).is_file():
                self.missing(rel)
                return
            root = folder().resolve()
            page = (wiki.here_page(root, rel, said)
                    if route.startswith("/here")
                    else wiki.remove_page(root, rel, said))
            self.send(page.encode("utf-8"), TYPES[".html"])
            return

        if route in ("/edit", "/edit/", "/add", "/add/"):
            q = parse_qs(urlparse(self.path).query)
            rel = q.get("page", [""])[0]
            said = q.get("said", [""])[0]
            if safe(rel) is None or not safe(rel).is_file():
                self.missing(rel)
                return
            root = folder().resolve()
            if route.startswith("/add"):
                after = q.get("after", [""])[0]
                page = wiki.add_page(root, rel, said,
                                     int(after) if after.isdigit() else None)
            elif q.get("raw", [""])[0]:
                page = wiki.edit_page(root, rel, said)
            else:
                page = wiki.pieces_page(root, rel, said)
            self.send(page.encode("utf-8"), TYPES[".html"])
            return

        if route in ("/ways", "/ways/"):
            said = parse_qs(urlparse(self.path).query).get("said", [""])[0]
            body = wiki.frame("Ways to answer",
                              ('<p id="said">' + html.escape(said) + "</p>"
                               if said else "")
                              + ways.page(your_ways()))
            self.send(body.encode("utf-8"), TYPES[".html"])
            return

        if route in ("/flags", "/flags/"):
            said = parse_qs(urlparse(self.path).query).get("said", [""])[0]
            self.send(wiki.flags_page(folder().resolve(),
                                      said).encode("utf-8"), TYPES[".html"])
            return

        name = route.lstrip("/") or "index.html"
        path = safe(name)
        if path is None or not path.is_file():
            self.missing(name)
            return
        try:
            raw = path.read_bytes()
        except OSError:
            self.missing(name)
            return

        # Handed over exactly as it is on disk - EXCEPT that a combo box
        # pointing at a kind gets its options filled from what is on
        # disk right now, so a thing you added a minute ago is already
        # in it. Nothing else is rewritten and nothing is written back.
        if path.suffix.lower() in (".html", ".htm") and (
                b"data-kind" in raw or b"<!-- pointing here -->" in raw
                or b'id="qtype"' in raw
                or b'id="tidy"' in raw
                or b"<!-- questions -->" in raw):
            rel = path.relative_to(folder().resolve()).as_posix()
            depth = len(path.relative_to(folder().resolve()).parts) - 1
            text = kinds.fill_selects(read_text(path) or "", kind_entries,
                                      up="../" * depth)
            text = kinds.fill_checkboxes(text, kind_entries,
                                         up="../" * depth)
            text = kinds.fill_kind_list(text, all_kinds)
            # What is waiting, counted as the page is served. Same rule
            # as everything else here: read off disk now, stored
            # nowhere, so it cannot be out of date and there is nothing
            # to rebuild.
            text = wiki.fill_tidy(text, folder().resolve())
            # The list of ways to answer is refilled here rather than
            # trusted as it sits in the file. A way pasted in after a
            # kind was made would otherwise never appear in that kind's
            # list until the page happened to be rebuilt.
            # The ways to answer are refilled here rather than trusted
            # as they sit in the file. One pasted in after a kind was
            # made would otherwise never show up in that kind's list.
            spot = re.search(
                r'(<select[^>]*id="qtype"[^>]*>)(.*?)(</select>)',
                text, re.S | re.I)
            if spot:
                text = (text[:spot.start(2)]
                        + chr(10) + kinds.type_options(extra=your_ways())
                        + chr(10) + "  " + text[spot.end(2):])

            if "<!-- questions -->" in text:
                kind_slug = path.parent.name
                shape = read_text(path.parent / "_kind.html") or ""
                text = kinds.fill_questions(text, kind_slug, shape,
                                            your_ways())
            text = kinds.hide_empty_details(text)
            raw = kinds.fill_backlinks(
                text, lambda: points_at(rel)).encode("utf-8")

        # The tool links go on here, on the way out, for every page -
        # including ones this program has never written to. Nothing is
        # written back, so the file on disk stays a page that works on
        # its own.
        if path.suffix.lower() in (".html", ".htm"):
            here = path.relative_to(folder().resolve()).as_posix()
            raw = wiki.with_tools(
                raw.decode("utf-8", "replace"), here).encode("utf-8")

        self.send(raw, TYPES.get(path.suffix.lower(),
                                 "application/octet-stream"))

    def form_fields(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 5_000_000:
            return {}
        return {k: v[0] for k, v in parse_qs(
            self.rfile.read(length).decode("utf-8", "replace"),
            keep_blank_values=True).items()}

    def do_POST(self):
        route = urlparse(self.path).path

        if route == "/newkind":
            f = self.form_fields()
            s, trouble = make_kind(f.get("name", ""))
            if s and not trouble:
                self.go("/" + s + "/index.html")
            elif s:
                self.send(problem_page(trouble, "/" + s + "/index.html"),
                          TYPES[".html"])
            else:
                self.send(problem_page(trouble, "/"), TYPES[".html"])
            return

        if route == "/newfield":
            f = self.form_fields()
            k = f.get("_kind", "")
            target = f.get("target", "")
            fresh = f.get("newtarget", "").strip()
            if fresh:
                made, why = make_kind(fresh)
                if made and not why:
                    target = made
                elif made:
                    target = made
            opts = [o for o in f.get("options", "").splitlines()]
            trouble = add_field(k, f.get("question", ""),
                                f.get("type", "text"), target,
                                opts)
            back = "/" + k + "/index.html"
            if trouble:
                self.send(problem_page(trouble, back), TYPES[".html"])
            else:
                self.go(back)
            return

        if route == "/editfield":
            f = self.form_fields()
            k = f.get("_kind", "")
            trouble = edit_field(k, f.get("field", ""),
                                 f.get("question", ""),
                                 f.get("type", "text"),
                                 remove=f.get("do", "") == "remove",
                                 options=f.get("options", "").splitlines())
            back = "/" + k + "/index.html"
            if trouble:
                self.send(problem_page(trouble, back), TYPES[".html"])
            else:
                self.go(back)
            return

        if route == "/new":
            f = self.form_fields()
            k = f.get("_kind", "")
            rel, trouble = new_entry(k, f.get("name", ""))
            if rel and not trouble:
                self.go("/" + rel)
            else:
                self.send(problem_page(trouble or "Could not make it.",
                                       "/" + k + "/index.html"),
                          TYPES[".html"])
            return

        if route == "/relink":
            f = self.form_fields()
            rel, addr = f.get("page", ""), f.get("addr", "")
            words = f.get("words", "")
            if safe(rel) is None:
                self.send(problem_page("That is not a page in your folder.",
                                       "/"), TYPES[".html"])
                return
            root = folder().resolve()
            if f.get("do", "") == "unlink":
                trouble = links.unlink(root, rel, addr, words,
                                       read_text, write_text)
                said = trouble or ("The link is off. " + words
                                   + " is still there as words.")
            elif not f.get("target", ""):
                said = "Nothing was chosen, so that link was left alone."
            else:
                target = f["target"]
                trouble = links.repoint_any(root, rel, addr, words, target,
                                            read_text, write_text)
                said = trouble or (words + " now goes to " + target + ".")
            self.go("/here?page=" + quote(rel) + "&said=" + quote(said))
            return

        if route == "/removepage":
            f = self.form_fields()
            rel = f.get("page", "")
            if safe(rel) is None:
                self.send(problem_page("That is not a page in your folder.",
                                       "/"), TYPES[".html"])
                return
            trouble = links.remove(folder().resolve(), rel,
                                   read_text, write_text)
            if trouble:
                self.go("/remove?page=" + quote(rel) + "&said="
                        + quote(trouble))
            else:
                self.go("/repairs?said=" + quote(
                    rel + " was put away in _deleted. Anything that pointed "
                    "at it is on this page now."))
            return

        if route == "/addafter":
            f = self.form_fields()
            rel = f.get("page", "")
            path = safe(rel)
            if path is None or not path.is_file():
                self.send(problem_page("That is not a page in your folder.",
                                       "/"), TYPES[".html"])
                return
            try:
                n = int(f.get("n", "-1"))
            except ValueError:
                n = -1
            was = read_text(path)
            new, trouble = editing.insert_after(
                was, n, f.get("note", ""),
                markup.level_at(was, "<!-- here -->"))
            if not trouble and not write_text(path, new):
                trouble = "That page could not be written to."
            if trouble:
                self.go("/add?page=" + quote(rel) + "&after=" + str(n)
                        + "&said=" + quote(trouble))
            else:
                self.go("/" + rel)
            return

        if route == "/editpiece":
            f = self.form_fields()
            rel = f.get("page", "")
            path = safe(rel)
            if path is None or not path.is_file():
                self.send(problem_page("That is not a page in your folder.",
                                       "/"), TYPES[".html"])
                return
            try:
                n = int(f.get("n", "-1"))
            except ValueError:
                n = -1
            was = read_text(path)
            new, trouble = editing.rewrite(
                was, n, f.get("words", ""),
                markup.level_at(was, "<!-- here -->"))
            if not trouble:
                if not write_text(path, new):
                    trouble = "That page could not be written to."
            self.go("/edit?page=" + quote(rel) + "&said="
                    + quote(trouble or "That piece was saved."))
            return

        if route == "/makewritable":
            f = self.form_fields()
            rel = f.get("page", "")
            if safe(rel) is None:
                self.send(problem_page("That is not a page in your folder.",
                                       "/"), TYPES[".html"])
                return
            trouble = wiki.make_writable(folder().resolve(), rel,
                                         read_text, write_text)
            self.go("/add?page=" + quote(rel) + "&said="
                    + quote(trouble or "This page can take writing now."))
            return

        if route == "/editsave":
            f = self.form_fields()
            rel = f.get("page", "")
            if safe(rel) is None:
                self.send(problem_page("That is not a page in your folder.",
                                       "/"), TYPES[".html"])
                return
            trouble = wiki.save_edit(folder().resolve(), rel,
                                     f.get("text", ""), read_text, write_text)
            self.go("/edit?page=" + quote(rel) + "&said="
                    + quote(trouble or (rel + " was saved.")))
            return

        if route == "/editundo":
            f = self.form_fields()
            rel = f.get("page", "")
            if safe(rel) is None:
                self.send(problem_page("That is not a page in your folder.",
                                       "/"), TYPES[".html"])
                return
            trouble = wiki.undo_edit(folder().resolve(), rel,
                                     read_text, write_text)
            self.go("/edit?page=" + quote(rel) + "&said="
                    + quote(trouble or ("Put back. The version you just "
                                        "replaced is now the kept one, so "
                                        "pressing it again swaps them "
                                        "round.")))
            return

        if route == "/newway":
            f = self.form_fields()
            path = ways_file()
            new, _key, trouble = ways.add(read_text(path) or ways.STARTER,
                                          f.get("name", ""),
                                          f.get("reads", ""),
                                          f.get("paste", ""))
            if not trouble and not write_text(path, new):
                trouble = "That file could not be written to."
            self.go("/ways?said=" + quote(
                trouble or ("Added. It is in the list of ways to answer "
                            "now, and in _ways.html.")))
            return

        if route == "/makepage":
            # From the dead end. The address is the one that was asked
            # for, not one worked out from a name, so the link that led
            # there works afterwards rather than landing somewhere close.
            f = self.form_fields()
            rel = f.get("rel", "").strip("/")
            if safe(rel) is None:
                self.send(problem_page(
                    "That is not an address inside your folder.", "/"),
                    TYPES[".html"])
                return
            trouble = wiki.make_page_at(folder().resolve(), rel,
                                        f.get("title", ""), write_text)
            if trouble:
                self.send(problem_page(trouble, "/" + rel), TYPES[".html"])
            else:
                self.go("/" + rel)
            return

        if route == "/newpage":
            f = self.form_fields()
            rel, trouble = wiki.make_page(folder().resolve(),
                                          f.get("name", ""),
                                          f.get("where", ""), kinds.slug,
                                          write_text)
            if rel and not trouble:
                self.go("/" + rel)
            else:
                self.send(problem_page(trouble or "Could not make it.",
                                       "/search"), TYPES[".html"])
            return

        if route == "/resolveflag":
            f = self.form_fields()
            root = folder().resolve()
            page_rel, words = f.get("page", ""), f.get("words", "")
            target = f.get("target", "")
            fresh = f.get("newpage", "").strip()

            # A chosen page wins. Otherwise the typed name makes one, in
            # the same folder as the page that flagged it - so nothing
            # has to be decided mid-thought about where things live.
            if not target and fresh:
                where = page_rel.rsplit("/", 1)[0] if "/" in page_rel else ""
                target, trouble = wiki.make_page(root, fresh, where,
                                                 kinds.slug, write_text)
                if trouble and not target:
                    self.go("/flags?said=" + quote(trouble))
                    return
            if not target:
                self.go("/flags?said=" + quote(
                    "Nothing was chosen and no new page was named, so "
                    "that flag was left alone."))
                return
            trouble = wiki.resolve(root, page_rel, words, target,
                                   read_text, write_text)
            self.go("/flags?said=" + quote(
                trouble or (words + " now links to " + target + ".")))
            return

        if route == "/repoint":
            f = self.form_fields()
            root = folder().resolve()
            target = f.get("target", "")
            # "Take it off" is checked before the missing-target
            # complaint, because it deliberately has no target: the page
            # this link named is gone on purpose and there is nothing it
            # should point at instead. Same links.unlink the per-page
            # view has always used; it only stops being reachable from
            # here, which is where you land when a link goes dead.
            if f.get("do", "") == "unlink":
                words = f.get("words", "")
                trouble = links.unlink(root, f.get("page", ""),
                                       f.get("addr", ""), words,
                                       read_text, write_text)
                self.go("/repairs?said=" + quote(
                    trouble or ("The link is off. " + (words or "The words")
                                + " is still there as words, and /edit can "
                                "change or remove the line now.")))
                return
            if not target:
                self.send(problem_page("No page was chosen to point it at.",
                                       "/repairs"), TYPES[".html"])
                return
            trouble = links.repoint(root, f.get("page", ""), f.get("addr", ""),
                                    target, read_text, write_text)
            self.go("/repairs?said=" + quote(
                trouble or ("That link now points at " + target + ".")))
            return

        if route == "/move":
            f = self.form_fields()
            root = folder().resolve()
            was = f.get("page", "")
            if not was:
                self.send(problem_page("No page was chosen to move.",
                                       "/repairs"), TYPES[".html"])
                return
            where = (f.get("newfolder", "").strip()
                     or f.get("folder", "").strip())
            where = kinds.slug(where) if f.get("newfolder", "").strip() \
                else where.strip("/")
            called = f.get("name", "").strip() or was.rsplit("/", 1)[-1]
            if not called.lower().endswith((".html", ".htm")):
                called = kinds.slug(called) + ".html"
            now = (where + "/" + called) if where else called
            trouble = links.move(root, was, now, read_text, write_text,
                                 called=f.get("name", "").strip())
            self.go("/repairs?said=" + quote(
                trouble or (was + " is now at " + now
                            + ", and every address to and from it was "
                              "rewritten.")))
            return

        if route != "/save":
            self.missing(self.path)
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 5_000_000:
            self.send(problem_page("Nothing arrived.", "/"), TYPES[".html"])
            return
        form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"),
                        keep_blank_values=True)
        # Single values for the plain fields, but the FULL list is kept:
        # a checkbox group sends its name once per tick, and taking only
        # the first would silently drop everything but one.
        fields = {k: v[0] for k, v in form.items()}
        multi = form

        to = fields.pop("_to", "")
        marker = "<!-- " + (fields.pop("_at", "") or "here") + " -->"
        back = fields.pop("_back", "") or ("/" + to)
        # Read before the loop below strips every underscore field, or
        # this would be thrown away before anything could act on it.
        field_id = fields.pop("_set", "")
        for key in list(fields):
            if key.startswith("_"):
                fields.pop(key)

        path = safe(to)
        if path is None or not path.is_file():
            self.send(problem_page(
                "The form did not say which file to write into, or named one "
                "that is not here. That is the hidden _to field.",
                self.headers.get("Referer") or "/"), TYPES[".html"])
            return

        # A form can carry several fields at once: anything named
        # set-<id> overwrites the element with that id. That is what
        # lets one Save button do a whole form, the way a form is
        # normally expected to behave.
        setters = [(k[4:], v) for k, v in list(fields.items())
                   if k.startswith("set-")]
        news = {k[4:]: v for k, v in list(fields.items())
                if k.startswith("new-")}
        if setters:
            for key, _ in setters:
                fields.pop("set-" + key, None)
            for key in news:
                fields.pop("new-" + key, None)
            trouble = ""
            for key, value in setters:
                # A pick question: "or a new one called" wins over the
                # combo box, so wanting something that does not exist
                # yet never stops you part-way through an entry.
                wanted = news.get(key + "-box", "").strip()
                if wanted:
                    kind_slug = pick_kind_of(path, key)
                    rel, why = new_entry(kind_slug, wanted)
                    if rel:
                        value = "../" + rel
                    elif why:
                        trouble = trouble or why
                        continue
                chosen = [v for v in multi.get("set-" + key, [value])
                          if v.strip()]
                if wanted and value:
                    chosen = chosen + [value] if value not in chosen else chosen

                # A fixed list of words is not a list of pages, so it
                # cannot be turned into links. Told apart by asking the
                # page which one this question is, rather than guessing
                # from what the value looks like.
                if is_option_field(path, key):
                    t = set_choices(path, key, chosen)
                elif len(chosen) > 1:
                    t = set_links(path, key, chosen)
                elif value.startswith("../") or "/" in value:
                    t = set_link(path, key, value)
                else:
                    t = set_field(path, key,
                                  value.replace("\r\n", "\n").strip())
                trouble = trouble or t
            if trouble:
                self.send(problem_page(trouble,
                                       self.headers.get("Referer") or "/"),
                          TYPES[".html"])
            else:
                self.go(back)
            return

        # _set names a single field to overwrite. Everything else appends.
        if field_id:
            value = next(iter(fields.values()), "")
            tidy = value.replace("\r\n", "\n").strip()
            trouble = set_field(path, field_id, tidy)
            if trouble:
                self.send(problem_page(trouble,
                                       self.headers.get("Referer") or "/"),
                          TYPES[".html"])
            else:
                self.go(back)
            return

        if not any(v.strip() for v in fields.values()):
            self.go(back)
            return

        values = {"when": datetime.now().strftime(STAMP)}
        values.update({k: v.replace("\r\n", "\n").strip()
                       for k, v in fields.items()})

        page = read_text(path)
        trouble = insert(path, marker,
                         shape_from(page, values,
                                    markup.level_at(page, marker)))
        if trouble:
            self.send(problem_page(trouble,
                                   self.headers.get("Referer") or "/"),
                      TYPES[".html"])
            return
        self.go(back)


def main():
    global HERE
    ap = argparse.ArgumentParser(description="Makes your HTML forms save.")
    ap.add_argument("--folder", help="where your pages are")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    if args.folder:
        HERE = Path(args.folder).expanduser().resolve()

    where = folder()
    url = "http://127.0.0.1:" + str(args.port) + "/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        print("Could not start: " + str(exc), flush=True)
        print("It may already be running. Try opening " + url, flush=True)
        return 1

    # Flushed: when this is the exe these lines are the only thing saying
    # it started and how to stop it. A silent console reads like a program
    # that did not run.
    # The program used to be called Forms, and so did its log. The old
    # log is carried over once, so its history is not stranded under a
    # name nothing writes to any more.
    old_log = where / "Forms.log"
    if old_log.is_file() and not (where / LOG_NAME).exists():
        try:
            old_log.rename(where / LOG_NAME)
        except OSError:
            pass

    for line in ("The life web is running. Your forms will save now.",
                 "  Open:   " + url,
                 "  Folder: " + str(where),
                 "  Stop:   Ctrl+C, or close this window",
                 "  Log:    " + str(where / LOG_NAME)):
        print(line, flush=True)

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    brought_forward = refresh_kind_indexes()
    if brought_forward:
        print("  Note:   brought up to date - "
              + ", ".join(brought_forward), flush=True)
        log("rebuilt kind pages: " + ", ".join(brought_forward))

    log("started on port %d, serving %s" % (args.port, where))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
        log("stopped with Ctrl+C")
    except Exception as exc:
        # A crash and a clean stop look identical from a browser: every
        # link dead, nothing to read. Written down so they can be told
        # apart afterwards.
        log("CRASHED: %r" % (exc,))
        import traceback
        for tb in traceback.format_exc().splitlines():
            log("  " + tb)
        raise
    finally:
        server.server_close()
        log("shut down")
    return 0


if __name__ == "__main__":
    sys.exit(main())
