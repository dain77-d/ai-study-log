"""Catch math that GitHub renders wrongly.

GitHub applies Markdown backslash escapes BEFORE MathJax sees the math, so inside $...$ and $$...$$
every backslash followed by ASCII punctuation loses its backslash:
  \\{ \\}  -> braces vanish, \\Big\\{ fails ("Missing or unrecognized delimiter")
  \\|      -> norm bars become a single |
  \\, \\; \\! -> spacing commands turn into visible , ; !
  \\\\     -> line breaks in cases/aligned collapse into one row
  \\&      -> raw & inside inline math is HTML-escaped and fails ("Unable to render expression")
Also a bare & inside inline $...$ fails the same way (& is fine in $$...$$ display blocks).

Inline math must be written as $`...`$ (GitHub passes it to MathJax verbatim, no Markdown parsing).
Plain $...$ also loses underscores to emphasis (_ pairs across two formulas) and is not rendered inside
*italic* text such as figure captions. --fix converts $...$ to $`...`$ automatically.
Write money as \$ (e.g. \$294K) so it is never mistaken for math.

Usage: python .github/scripts/math_lint.py [--fix] [files...]   (default: every *.md)
--fix rewrites the mechanical cases; & in inline math must be fixed by hand (move it out of the math).
"""
import glob
import re
import sys

REPLACE = {
    "\\{": "\\lbrace", "\\}": "\\rbrace", "\\|": "\\Vert",
    "\\,": "\\thinspace", "\\;": "\\thickspace", "\\!": "\\negthinspace", "\\\\": "\\cr",
}
ESCAPE = re.compile(r"\\[!-/:-@\[-`{-~]")  # backslash + ASCII punctuation
MATH = re.compile(r"(?<!\\)\$\$.+?\$\$|(?<!\\)\$[^$\n]+?(?<!\\)\$", re.S)  # \$ = literal dollar (currency)
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)


def needs_backticks(span):
    """Every inline math goes in $`...`$. Plain $...$ breaks in two ways on GitHub: _ or * pairs with
    another span's _ / * and becomes emphasis (e.g. $\\mathsf{Linear}_D(x)$ ... $\\tau_\\Delta$), and
    math inside *italic* figure captions is not rendered at all. $`...`$ is never parsed as Markdown."""
    return not span.startswith("$$")


def fix_span(span):
    def sub(m):
        rep = REPLACE.get(m.group(0))
        if rep is None:
            return m.group(0)
        nxt = span[m.end():m.end() + 1]
        return rep + (" " if nxt.isalpha() else "")
    span = ESCAPE.sub(sub, span)
    return "$`" + span[1:-1] + "`$" if needs_backticks(span) else span


def check(path, fix):
    text = open(path, encoding="utf-8").read()
    problems, out, pos = [], [], 0
    masked = CODE.sub(lambda m: " " * len(m.group(0)), text)  # keep offsets, ignore code
    for m in MATH.finditer(masked):
        span = text[m.start():m.end()]
        line = text.count("\n", 0, m.start()) + 1
        if span.startswith("$`"):  # $`...`$ is passed to MathJax verbatim: nothing to check
            out.append(text[pos:m.end()])
            pos = m.end()
            continue
        if needs_backticks(span):
            problems.append(f"{path}:{line}: inline math must be written as $`...`$ (run with --fix)")
        for e in ESCAPE.finditer(span):
            hint = REPLACE.get(e.group(0), "move it out of the math or rewrite")
            problems.append(f"{path}:{line}: '{e.group(0)}' in math -> use '{hint}'")
        if not span.startswith("$$") and "&" in span:
            problems.append(f"{path}:{line}: '&' inside inline math -> move it out of $...$")
        out.append(text[pos:m.start()])
        out.append(fix_span(span) if fix else span)
        pos = m.end()
    out.append(text[pos:])
    if fix:
        new = "".join(out)
        if new != text:
            open(path, "w", encoding="utf-8", newline="\n").write(new)
    return problems


def main(argv):
    fix = "--fix" in argv
    files = [a for a in argv if not a.startswith("--")] or glob.glob("**/*.md", recursive=True)
    problems = [p for f in files for p in check(f, fix)]
    if fix:
        problems = [p for f in files for p in check(f, False)]
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
