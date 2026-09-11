"""Kinds of thing, and the pages that are of a kind.

A kind is a folder with two files in it:

    <kind>/_kind.html   the shape a page of this kind takes
    <kind>/index.html   the list of them, and the box that makes new ones

Adding a kind makes those. Adding a question inserts into _kind.html at
markers, same trick as everything else. Making an entry copies
_kind.html and fills in its name.

There is no list of kinds anywhere in the code. The kinds ARE the
folders. Ways of answering a question are finite; kinds of thing are
not, so the answer types are built in and the kinds never are.

Page shape follows the ordinary convention for a form: one Details
form, its questions in the order they were defined, each value sitting
IN its box, and one Save. Not a list of values plus a separate pile of
change-boxes - that read backwards and put the notes box in the middle.
"""

import html
import re
import unicodedata

import ways

# The finite half. Each says how to render the box you type into.
TYPES = {
    "text":   {"label": "Short text", "rows": 2},
    "long":   {"label": "Long text",  "rows": 6},
    "number": {"label": "Number",     "input": "number"},
    "date":   {"label": "Date",       "input": "date"},
    "time":   {"label": "Time", "input": "time"},
    "yesno":  {"label": "Yes / No", "yesno": True},
    # Fixed lists of words you type. Different from pick/many, which
    # point at other things that have pages of their own.
    "choice": {"label": "One of a list (radio buttons)", "opts": "radio"},
    "drop":   {"label": "One of a list (dropdown)", "opts": "select"},
    "checks": {"label": "Several of a list (checkboxes)", "opts": "checkbox"},
    "pick":   {"label": "One of another kind", "pick": True},
    "many":   {"label": "Several of another kind", "many": True},
}
TYPE_ORDER = ["text", "long", "number", "date", "time", "yesno",
              "choice", "drop", "checks", "pick", "many"]

MARK_FIELDS = "<!-- fields -->"
MARK_HERE = "<!-- here -->"
MARK_ENTRIES = "<!-- entries -->"
MARK_KINDS = "<!-- kinds -->"
MARK_QUESTIONS = "<!-- questions -->"

KIND_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>

<h1>{name}</h1>

<nav>
<a href="index.html">Back to KINDNAME</a>
<a href="../index.html">Back to the top</a>
</nav>

<h2>Details</h2>

<form method="post" action="/save">
  <input type="hidden" name="_to" value="{to}">
<!-- fields -->
  <button type="submit">Save details</button>
</form>

<h2>What points here</h2>

<ul>
<!-- pointing here -->
</ul>

<h2>Notes</h2>

<!-- here -->

<h2>Add a note</h2>

<form method="post" action="/save">
  <input type="hidden" name="_to" value="{to}">
  <label for="note-box">What do you want to add?</label>
  <textarea id="note-box" name="note" rows="4"></textarea>
  <button type="submit">Add note</button>
</form>

<template>
<div class="addition">
<p class="when">{when}</p>
<p>{note}</p>
</div>
</template>

</body>
</html>
"""

# Bumped whenever the kind index page changes shape. Any page without
# the current marker gets rebuilt on startup, so an improvement reaches
# the kinds you already have instead of only the ones made afterwards.
# Guessing from the page's wording did not work: the old page contained
# "Add a question", so a check for "Add a " thought it was current.
INDEX_VERSION = "<!-- kind index 3 -->"

KIND_INDEX = """<!doctype html>
<!-- kind index 3 -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KINDNAME</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>

<h1>KINDNAME</h1>

<nav>
<a href="../index.html">Back to the top</a>
</nav>

<h2>Add a KINDNAME</h2>

<form method="post" action="/new">
  <input type="hidden" name="_kind" value="KINDSLUG">
  <label for="newname">What is this one called?</label>
  <input type="text" id="newname" name="name">
  <button type="submit">Add it</button>
</form>

<h2>Every KINDNAME</h2>

<ul>
<!-- entries -->
</ul>

<h2>Questions this kind asks</h2>

<ol>
<!-- questions -->
</ol>

<h2>Add a question</h2>

<form method="post" action="/newfield">
  <input type="hidden" name="_kind" value="KINDSLUG">
  <label for="q">The question</label>
  <input type="text" id="q" name="question">
  <label for="qtype">What kind of answer</label>
  <select id="qtype" name="type">
TYPEOPTIONS
  </select>

  <label for="qtarget">If the answer is one of another kind, which kind</label>
  <select id="qtarget" name="target" data-kinds="all">
  </select>

  <label for="qnewtarget">or a new kind called</label>
  <input type="text" id="qnewtarget" name="newtarget" value="">

  <label for="qopts">If the answer is one of a list, the choices, one per line</label>
  <textarea id="qopts" name="options" rows="4"></textarea>

  <button type="submit">Add the question</button>
</form>

</body>
</html>
"""


def slug(text, fallback=""):
    s = unicodedata.normalize("NFKD", text)
    s = s.encode("ascii", "ignore").decode("ascii").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or fallback


def type_options(selected="", extra=None):
    """The ways of answering: the built-in ones, then the ones you added.

    Yours are read from _ways.html each time this is asked for, so one
    pasted a minute ago is already in the list, with no rebuild.
    """
    rows = ['    <option value="%s"%s>%s</option>'
            % (k, " selected" if k == selected else "", TYPES[k]["label"])
            for k in TYPE_ORDER]
    for key, spec in sorted((extra or {}).items()):
        rows.append('    <option value="%s"%s>%s</option>'
                    % (html.escape(key, quote=True),
                       " selected" if key == selected else "",
                       html.escape(spec["name"])))
    return "\n".join(rows)


def field_block(field_id, question, type_key, target_kind="",
                options=None, extra=None):
    """One question inside the Details form: a label and its box.

    The box is named set-<id>, which is what tells the program to
    overwrite that field rather than append. Its id is <id>-box so the
    program can keep it in step after a save.

    A "pick" question gets three things: a combo box of that kind's
    entries, a box to name a new one instead, and a paragraph holding a
    real <a href> to whatever is currently chosen. The combo box is
    empty on disk and filled when the page is served, so a thing you
    added a minute ago is already in it. The LINK is what makes the
    file still a real linked page when nothing is running.
    """
    # A way you pasted in wins, because it was added deliberately and
    # by hand. Nothing in the code needs to know it exists.
    yours = (extra or {}).get(type_key)
    if yours:
        return ways.build(yours["paste"], field_id, question)

    spec = TYPES.get(type_key, TYPES["text"])
    box_id = html.escape(field_id + "-box", quote=True)
    fid = html.escape(field_id, quote=True)
    q = html.escape(question)

    if spec.get("opts"):
        how = spec["opts"]
        opts = [o.strip() for o in (options or []) if o.strip()]
        if how == "select":
            rows = ['  <select id="%s" name="set-%s">' % (box_id, fid),
                    '    <option value="">(none)</option>']
            rows += ['    <option value="%s">%s</option>'
                     % (html.escape(o, quote=True), html.escape(o))
                     for o in opts]
            rows.append("  </select>")
            return ('  <label for="%s">%s</label>\n' % (box_id, q)
                    + "\n".join(rows)
                    + '\n  <p id="%s">Not yet recorded.</p>' % fid)
        # radio buttons and checkboxes: a real fieldset, which is the
        # thing a screen reader handles best - the legend is announced
        # with each option so you always know which question you are in.
        rows = ['  <fieldset data-options="%s">' % fid,
                "  <legend>%s</legend>" % q]
        for i, o in enumerate(opts):
            oid = "%s--%d" % (field_id, i)
            rows.append(
                '    <label><input type="%s" id="%s" name="set-%s" '
                'value="%s"> %s</label>'
                % (how, html.escape(oid, quote=True), fid,
                   html.escape(o, quote=True), html.escape(o)))
        if not opts:
            rows.append("    <p>No choices set for this question yet.</p>")
        rows.append("  </fieldset>")
        return "\n".join(rows) + '\n  <p id="%s">Not yet recorded.</p>' % fid

    if spec.get("yesno"):
        return (
            '  <label for="%s">%s</label>\n'
            '  <input type="checkbox" id="%s" name="set-%s" value="Yes">\n'
            '  <p id="%s">No</p>' % (box_id, q, box_id, fid, fid))

    if spec.get("many"):
        k = html.escape(target_kind, quote=True)
        return (
            '  <fieldset data-kind="%s" data-for="%s">\n'
            '  <legend>%s</legend>\n'
            '  </fieldset>\n'
            '  <label for="%s-new">or a new one called</label>\n'
            '  <input type="text" id="%s-new" name="new-%s" value="">\n'
            '  <p id="%s" class="picked">Nothing chosen yet.</p>'
            % (k, fid, q, box_id, box_id, fid, fid))

    if spec.get("pick"):
        k = html.escape(target_kind, quote=True)
        return (
            '  <label for="%s">%s</label>\n'
            '  <select id="%s" name="set-%s" data-kind="%s">\n'
            '  </select>\n'
            '  <label for="%s-new">or a new one called</label>\n'
            '  <input type="text" id="%s-new" name="new-%s" value="">\n'
            '  <p id="%s" class="picked">Nothing chosen yet.</p>'
            % (box_id, q, box_id, fid, k, box_id, box_id, fid, fid))

    if "input" in spec:
        box = ('<input type="%s" id="%s" name="set-%s" value="">'
               % (spec["input"], box_id, fid))
        return ('  <label for="%s">%s</label>\n  %s' % (box_id, q, box))

    box = ('<textarea id="%s" name="set-%s" rows="%d"></textarea>'
           % (box_id, fid, spec["rows"]))
    # A written answer gets somewhere to BE, not only somewhere to be
    # typed. A "pick" question has had this all along - the paragraph
    # holding a real link to whatever is chosen - and a written one never
    # did, so its words lived only inside the box.
    #
    # A box is not prose, and two things step around it for good reasons:
    # searching drops forms, or every page matches on the words in its
    # own Save button, and flags are not hunted inside a box because a
    # box cannot hold a link. Together those meant a definition could be
    # found by its name and never by a word of what it said - in a
    # dictionary - and a flag typed into one was not merely unresolvable
    # but invisible, on no list anywhere.
    #
    # Nothing else had to be built for this. set_field already writes
    # both halves, and already declines to overwrite the shown one when
    # it says the same thing in a richer way, so a link made here
    # survives every later Save. Only the emitting was missing.
    #
    # Before the label rather than after it, unlike "picked": a chosen
    # entry is two words and reads the same either way, a written answer
    # is a paragraph, and putting it after the box means hearing the
    # whole thing twice.
    return ('  <p id="%s"></p>\n  <label for="%s">%s</label>\n  %s'
            % (fid, box_id, q, box))


def fill_selects(page_text, entries_for_kind, up="../"):
    """Fill every <select data-kind="..."> from what is on disk NOW.

    Done when the page is served, never baked into the file - so adding
    a thing puts it in every box that could point at it, immediately,
    with no rebuild. This is the one place a served page differs from
    the file, and it is safe because a form does nothing without the
    program running anyway.
    """
    def one(m):
        head, kind = m.group(1), m.group(2)
        chosen = ""
        pid = re.search(r'\bname="set-([^"]+)"', head)
        if pid:
            link = re.search(
                r'<p[^>]*\bid="%s"[^>]*>\s*<a href="([^"]+)"'
                % re.escape(pid.group(1)), page_text)
            if link:
                chosen = link.group(1)
        opts = ['<option value="">(none)</option>']
        for filename, title in entries_for_kind(kind):
            href = up + kind + "/" + filename
            sel = " selected" if href == chosen else ""
            opts.append('<option value="%s"%s>%s</option>'
                        % (html.escape(href, quote=True), sel,
                           html.escape(title)))
        return head + "\n" + "\n".join(opts) + "\n</select>"

    return re.sub(r'(<select[^>]*\bdata-kind="([^"]*)"[^>]*>).*?</select>',
                  one, page_text, flags=re.S | re.I)


def fill_checkboxes(page_text, entries_for_kind, up="../"):
    """Fill every <fieldset data-kind="..."> with one checkbox per entry.

    Same rule as the combo boxes: read off disk when the page loads.
    Which ones are already ticked is worked out from the real links
    stored in that field's paragraph, so the file stays the record.
    """
    def one(m):
        head, kind, fid = m.group(1), m.group(2), m.group(3)
        legend = m.group(4) or ""
        chosen = set()
        block = re.search(r'<p[^>]*\bid="%s"[^>]*>(.*?)</p>'
                          % re.escape(fid), page_text, re.S)
        if block:
            chosen = set(re.findall(r'<a href="([^"]+)"', block.group(1)))
        rows = [legend]
        for filename, title in entries_for_kind(kind):
            href = up + kind + "/" + filename
            box = "%s--%s" % (fid, re.sub(r"[^a-z0-9]+", "-",
                                          filename.lower()))
            tick = " checked" if href in chosen else ""
            rows.append(
                '  <label><input type="checkbox" id="%s" name="set-%s" '
                'value="%s"%s> %s</label>'
                % (html.escape(box, quote=True), html.escape(fid, quote=True),
                   html.escape(href, quote=True), tick, html.escape(title)))
        if len(rows) == 1:
            rows.append("  <p>None yet.</p>")
        return head + "\n" + "\n".join(rows) + "\n</fieldset>"

    return re.sub(
        r'(<fieldset[^>]*\bdata-kind="([^"]*)"[^>]*\bdata-for="([^"]*)"[^>]*>)'
        r'\s*(<legend>.*?</legend>)?.*?</fieldset>',
        one, page_text, flags=re.S | re.I)


def hide_empty_details(page_text):
    """A kind with no questions yet should not show an empty form.

    Left alone it renders as a lone Save button with nothing above it,
    which reads as broken rather than as not-set-up-yet.
    """
    def one(m):
        form = m.group(0)
        if 'name="set-' in form or "data-kind=" in form:
            return form
        return ('<p>This kind has no questions yet. '
                '<a href="index.html">Add one</a>.</p>')

    return re.sub(r'<form[^>]*action="/save"[^>]*>(?:(?!</form>).)*?'
                  r'Save details.*?</form>',
                  one, page_text, count=1, flags=re.S | re.I)


def fill_backlinks(page_text, pointing_at):
    """List everything that points at this page.

    Worked out when the page is served, by looking at the real links in
    the other files - never stored here. So it cannot go stale, and
    nothing quietly accumulates in a file you did not write.

    The relationship itself IS in a real file: it lives on the side that
    made the link, which is the side you typed it on. This end is a
    convenience, so a hub page like a period is not a dead end.
    """
    def one(m):
        rows = []
        for href, title, kind in pointing_at():
            rows.append('<li><a href="%s">%s</a> '
                        '<span class="count">(%s)</span></li>'
                        % (html.escape(href, quote=True),
                           html.escape(title), html.escape(kind)))
        if not rows:
            rows.append("<li>Nothing points here yet.</li>")
        return m.group(1) + "\n" + "\n".join(rows)

    return re.sub(r"(<!-- pointing here -->)", one, page_text, count=1)


def fill_kind_list(page_text, all_kinds):
    """Fill <select data-kinds="all"> with every kind there is.

    Same rule as the entry lists: read off disk when the page loads, so
    a kind you made a minute ago is already offered.
    """
    def one(m):
        opts = ['<option value="">(none)</option>']
        for slug_, name in all_kinds():
            opts.append('<option value="%s">%s</option>'
                        % (html.escape(slug_, quote=True), html.escape(name)))
        return m.group(1) + "\n" + "\n".join(opts) + "\n</select>"

    return re.sub(r'(<select[^>]*\bdata-kinds="all"[^>]*>).*?</select>',
                  one, page_text, flags=re.S | re.I)


def questions_in(template_text):
    """[(field_id, question, type_key), ...] read out of a kind's shape.

    Read from the template rather than kept in a second list, so there
    is nothing to fall out of step. Editing a question changes one file
    and the listing follows.
    """
    out = []
    body = template_text.split("<h2>Details</h2>", 1)
    if len(body) < 2:
        return out
    form = body[1].split("</form>", 1)[0]

    for m in re.finditer(
            r'<fieldset[^>]*\bdata-for="([^"]+)"[^>]*>\s*<legend>(.*?)</legend>',
            form, re.S | re.I):
        out.append((m.group(1), html.unescape(m.group(2)).strip(), "many",
                    m.start()))

    for m in re.finditer(
            r'<label for="([^"]+)-box">(.*?)</label>\s*(<[a-z]+[^>]*>)',
            form, re.S | re.I):
        fid, q, ctl = m.group(1), html.unescape(m.group(2)).strip(), m.group(3)
        if fid.endswith("-box"):
            continue
        if ctl.lower().startswith("<textarea"):
            rows = re.search(r'rows="(\d+)"', ctl)
            key = "long" if rows and int(rows.group(1)) > 3 else "text"
        elif ctl.lower().startswith("<select"):
            key = "pick"
        elif 'type="checkbox"' in ctl.lower():
            key = "yesno"
        elif 'type="number"' in ctl.lower():
            key = "number"
        elif 'type="date"' in ctl.lower():
            key = "date"
        else:
            key = "text"
        out.append((fid, q, key, m.start()))

    out.sort(key=lambda r: r[3])
    return [(a, b, c) for a, b, c, _ in out]


def question_form(kind_slug, field_id, question, type_key,
                  options=None, extra=None):
    """One question in the list, with the means to change or drop it."""
    fid = html.escape(field_id, quote=True)
    q = html.escape(question)
    # Every control names its own question. Without that you get four
    # identical blocks of "Question / What kind of answer / Save / Remove"
    # and no way to tell which one you are in.
    return (
        '<li>\n'
        '<h3>%s</h3>\n'
        '<form method="post" action="/editfield">\n'
        '  <input type="hidden" name="_kind" value="%s">\n'
        '  <input type="hidden" name="field" value="%s">\n'
        '  <label for="q-%s">Wording of "%s"</label>\n'
        '  <input type="text" id="q-%s" name="question" value="%s">\n'
        '  <label for="t-%s">Answer type for "%s"</label>\n'
        '  <select id="t-%s" name="type">\n%s\n  </select>\n'
        '  <label for="o-%s">Choices for "%s", one per line</label>\n'
        '  <textarea id="o-%s" name="options" rows="3">%s</textarea>\n'
        '  <button type="submit" name="do" value="save">Save "%s"</button>\n'
        '  <button type="submit" name="do" value="remove">Remove "%s"'
        '</button>\n'
        '</form>\n</li>'
        % (q, html.escape(kind_slug, quote=True), fid, fid, q, fid,
           html.escape(question, quote=True), fid, q, fid,
           type_options(type_key, extra), fid, q, fid,
           html.escape("\n".join(options or [])), q, q))


def find_block(template_text, field_id):
    """(start, end) of one question's markup inside a kind's shape."""
    esc = re.escape(field_id)
    fs = re.search(r'[ \t]*<fieldset[^>]*\bdata-for="%s".*?</fieldset>\n?'
                   r'(?:[ \t]*<label[^>]*>.*?</label>\n?)?'
                   r'(?:[ \t]*<input[^>]*name="new-%s"[^>]*>\n?)?'
                   r'(?:[ \t]*<p[^>]*\bid="%s"[^>]*>.*?</p>\n?)?'
                   % (esc, esc, esc), template_text, re.S | re.I)
    if fs:
        return fs.start(), fs.end()

    lbl = re.search(r'[ \t]*<label for="%s-box">.*?</label>\n?'
                    r'[ \t]*(?:<textarea[^>]*>.*?</textarea>'
                    r'|<select[^>]*>.*?</select>|<input[^>]*>)\n?'
                    r'(?:[ \t]*<label[^>]*for="%s-box-new">.*?</label>\n?)?'
                    r'(?:[ \t]*<input[^>]*name="new-%s"[^>]*>\n?)?'
                    r'(?:[ \t]*<p[^>]*\bid="%s"[^>]*>.*?</p>\n?)?'
                    % (esc, esc, esc, esc), template_text, re.S | re.I)
    if lbl:
        return lbl.start(), lbl.end()
    return None


def options_of(template_text, field_id):
    """The list of words a fixed-list question offers."""
    esc = re.escape(field_id)
    fs = re.search(r'<fieldset[^>]*\bdata-options="%s"[^>]*>(.*?)</fieldset>'
                   % esc, template_text, re.S | re.I)
    if fs:
        return [html.unescape(v) for v in
                re.findall(r'<input[^>]*\bvalue="([^"]*)"', fs.group(1))]
    sel = re.search(r'<select[^>]*\bname="set-%s"[^>]*>(.*?)</select>'
                    % esc, template_text, re.S | re.I)
    if sel:
        return [html.unescape(v) for v in
                re.findall(r'<option value="([^"]+)"', sel.group(1))]
    return []


def target_of(template_text, field_id):
    """Which kind a pick/many question points at, if any."""
    esc = re.escape(field_id)
    m = re.search(r'<select[^>]*\bname="set-%s"[^>]*\bdata-kind="([^"]*)"'
                  % esc, template_text, re.I)
    if m:
        return m.group(1)
    m = re.search(r'<fieldset[^>]*\bdata-kind="([^"]*)"[^>]*\bdata-for="%s"'
                  % esc, template_text, re.I)
    return m.group(1) if m else ""


def fill_questions(page_text, kind_slug, template_text, extra=None):
    """Fill <!-- questions --> from the kind's own shape, on serve."""
    def one(m):
        rows = [question_form(kind_slug, fid, q, key,
                              options_of(template_text, fid), extra)
                for fid, q, key in questions_in(template_text)]
        if not rows:
            rows = ["<li>No questions yet. Add one below.</li>"]
        return m.group(1) + "\n" + "\n".join(rows)

    return re.sub(r"(<!-- questions -->)", one, page_text, count=1)


def entry_row(filename, name):
    return ('<li><a href="%s">%s</a></li>'
            % (html.escape(filename, quote=True), html.escape(name)))


def kind_row(kind_slug, name, count):
    return ('<li><a href="%s/index.html">%s</a> '
            '<span class="count">(%d)</span></li>'
            % (html.escape(kind_slug, quote=True), html.escape(name), count))


def new_kind_files(name, kind_slug, extra=None):
    """(template_text, index_text) for a brand new kind."""
    index = (KIND_INDEX
             .replace("KINDNAME", html.escape(name))
             .replace("KINDSLUG", html.escape(kind_slug, quote=True))
             .replace("TYPEOPTIONS", type_options(extra=extra)))
    return KIND_TEMPLATE.replace("KINDNAME", html.escape(name)), index
