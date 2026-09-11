#!/usr/bin/env python3
"""Checks for markup.py - what typing turns into."""

import sys

import markup

PASS = []
FAIL = []


def check(name, got, want):
    if got == want:
        PASS.append(name)
    else:
        FAIL.append(name + "\n     wanted: " + repr(want)
                    + "\n        got: " + repr(got))


def h(text, top=2):
    return markup.to_html(text, top)


# --- paragraphs and line breaks -----------------------------------------

check("one line is one paragraph", h("Just words."), "<p>Just words.</p>")
check("a blank line starts a new paragraph",
      h("First thing.\n\nSecond thing."),
      "<p>First thing.</p>\n<p>Second thing.</p>")
check("a single line break stays a line break",
      h("First line\nsecond line"), "<p>First line<br>\nsecond line</p>")
check("a Windows line break is one line break, not two",
      h("First line\r\nsecond line"), "<p>First line<br>\nsecond line</p>")
check("nothing typed is nothing written", h(""), "")
check("only blank lines is nothing written", h("\n\n  \n"), "")


# --- headings: the number of #s is the level ----------------------------

check("a single hash is level two, because the page title is level one",
      h("# Origin"), "<h2>Origin</h2>")
check("two hashes are level two", h("## Later"), "<h2>Later</h2>")
check("three hashes are level three",
      h("### Second Section"), "<h3>Second Section</h3>")
check("six hashes are level six", h("###### Deep"), "<h6>Deep</h6>")
check("where it lands no longer changes the level",
      h("### Second Section", top=4), "<h3>Second Section</h3>")
check("seven hashes are not a heading", h("####### x"), "<p>####### x</p>")
check("a heading and its words",
      h("# Origin\nIt arrived in the first year."),
      "<h2>Origin</h2>\n<p>It arrived in the first year.</p>")
check("a hash with no space is not a heading",
      h("#notaheading"), "<p>#notaheading</p>")


# --- lists and quotes --------------------------------------------------

check("a dash starts a list",
      h("- one\n- two"), "<ul>\n<li>one</li>\n<li>two</li>\n</ul>")
check("a number starts a numbered list",
      h("1. one\n2. two"), "<ol>\n<li>one</li>\n<li>two</li>\n</ol>")
check("an angle bracket is a quote",
      h("> said a thing"),
      "<blockquote>\n<p>said a thing</p>\n</blockquote>")
check("a quote keeps its line breaks",
      h("> one\n> two"),
      "<blockquote>\n<p>one<br>\ntwo</p>\n</blockquote>")
check("three dashes are a dividing line", h("---"), "<hr>")


# --- inside a line -----------------------------------------------------

check("two stars are bold", h("a **very** thing"),
      "<p>a <strong>very</strong> thing</p>")
check("one star is italic", h("a *very* thing"),
      "<p>a <em>very</em> thing</p>")
check("underscores are left completely alone",
      h("the file_name_like_this one"),
      "<p>the file_name_like_this one</p>")
check("backticks are code", h("type `--folder` there"),
      "<p>type <code>--folder</code> there</p>")
check("marks inside code are not marks",
      h("`**not bold**`"), "<p><code>**not bold**</code></p>")
check("a link", h("see [First Place](first-place.html) there"),
      '<p>see <a href="first-place.html">First Place</a> there</p>')
check("a lone star is just a star", h("2 * 3 = 6"), "<p>2 * 3 = 6</p>")
check("stars around nothing are left alone", h("a ** b"), "<p>a ** b</p>")


# --- HTML you type is real HTML ----------------------------------------

check("a typed heading is a real heading",
      h("<h2>First Section</h2>"), "<h2>First Section</h2>")
check("a typed heading and the words under it are two pieces",
      h("<h2>First Section</h2>\nSome words."),
      "<h2>First Section</h2>\n<p>Some words.</p>")
check("a heading typed mid-paragraph is lifted out of the paragraph",
      h("the end. <h2>Third Section</h2> more words"),
      "<p>the end.</p>\n<h2>Third Section</h2>\n<p>more words</p>")
check("a typed paragraph is not wrapped in another one",
      h("<p>Hello</p>"), "<p>Hello</p>")
check("a typed list stays one piece",
      h("<ul>\n<li>one</li>\n<li>two</li>\n</ul>"),
      "<ul>\n<li>one</li>\n<li>two</li>\n</ul>")
check("a typed list on one line stays one piece",
      h("<ul><li>one</li><li>two</li></ul>"),
      "<ul><li>one</li><li>two</li></ul>")
check("typed bold and a typed link work inside a line",
      h('a <b>bold</b> and <a href="x.html">link</a> here'),
      '<p>a <b>bold</b> and <a href="x.html">link</a> here</p>')
check("a typed line break works",
      h("one<br>two"), "<p>one<br>two</p>")
check("a typed h1 becomes h2, so the page title stays the only level one",
      h("<h1>Big</h1>"), "<h2>Big</h2>")
check("capital letters in a tag are fine",
      h("<H3>Loud</H3>"), "<h3>Loud</h3>")
check("a class on a typed tag is kept",
      h('<p class="aside">side note</p>'), '<p class="aside">side note</p>')
check("markdown and html mix",
      h("## Section\n<b>bold</b> words"),
      "<h2>Section</h2>\n<p><b>bold</b> words</p>")


# --- the things that must not break ------------------------------------

check("a flag passes through untouched",
      h("went to [[the second place]] once"),
      "<p>went to [[the second place]] once</p>")
check("a flag next to a real link still survives",
      h("[[unnamed]] and [named](x.html)"),
      '<p>[[unnamed]] and <a href="x.html">named</a></p>')
check("a typed script cannot become a tag",
      h("I typed <script>alert(1)</script> at it"),
      "<p>I typed &lt;script&gt;alert(1)&lt;/script&gt; at it</p>")
check("a typed style block cannot become a tag",
      h("<style>p{}</style>"), "<p>&lt;style&gt;p{}&lt;/style&gt;</p>")
onclick = h('<b onclick="x()">hi</b>')
check("a tag carrying an onclick is shown as text, not run",
      "<b onclick" not in onclick and "&lt;b onclick=" in onclick, True)
script_link = h('<a href="javascript:alert(1)">x</a>')
check("a typed script link is shown as text",
      '<a href="javascript' not in script_link
      and "&lt;a href=&quot;javascript" in script_link, True)
check("a script link with a tab hidden in it is still caught",
      '<a href="java' not in h('<a href="java\tscript:alert(1)">x</a>'), True)
check("a script link hidden behind an entity is still caught",
      "<a href=" not in h('<a href="&#106;avascript:x">y</a>'), True)
check("a typed comment cannot become a marker",
      h("<!-- here -->"), "<p>&lt;!-- here --&gt;</p>")
check("a tag inside backticks stays text",
      h("type `<h2>` there"), "<p>type <code>&lt;h2&gt;</code> there</p>")
check("a lone angle bracket is just a character",
      h("3 < 4 and 5 > 2"), "<p>3 &lt; 4 and 5 &gt; 2</p>")
check("an ampersand is escaped once, not twice",
      h("this & that"), "<p>this &amp; that</p>")
check("a quote character survives", h('he said "no"'),
      "<p>he said &quot;no&quot;</p>")
check("a link target cannot carry a quote out",
      h('[x](a"b.html)'), '<p>[x](a&quot;b.html)</p>')
check("a markdown script target is refused and left as text",
      h("[x](javascript:alert)"), "<p>[x](javascript:alert)</p>")
check("a markdown data target is refused",
      h("[x](data:text/html;base64,AAA)"),
      "<p>[x](data:text/html;base64,AAA)</p>")
check("an ordinary page target still works",
      h("[x](../b/y.html)"), '<p><a href="../b/y.html">x</a></p>')


# --- which level sits above a spot in a page ---------------------------

ENTRY = ('<h1>Second Entry</h1><h2>Origin</h2><p>x</p><h2>Notes</h2>'
         '<!-- here -->\n<h2>Add a note</h2>')
PLAIN = '<h1>Second Place</h1>\n<!-- here -->\n<h2>Add to this page</h2>'

check("under Notes on an entry page, the next level down is 3",
      markup.level_at(ENTRY, "<!-- here -->"), 3)
check("straight under the title on a plain page, it is 2",
      markup.level_at(PLAIN, "<!-- here -->"), 2)
check("a page with no headings at all starts at two",
      markup.level_at("<p>nothing</p><!-- here -->", "<!-- here -->"), 2)
check("headings after the marker do not count",
      markup.level_at("<!-- here --><h4>later</h4>", "<!-- here -->"), 2)


print("\n".join("  ok   " + n for n in PASS))
if FAIL:
    print("\n".join("  FAIL " + n for n in FAIL))
print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
