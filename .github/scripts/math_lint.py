"""Catch math that GitHub renders wrongly, and convert it to the two forms GitHub never mangles.

GitHub runs Markdown BEFORE MathJax. Plain $...$ and $$...$$ therefore break in many ways:
  - _ and * inside one formula pair with _ / * in the next formula (or text) and become emphasis,
    e.g. $\\mathsf{Linear}_D(x)$ ... $\\tau_\\Delta$, or $$\\epsilon^*(z)...\\epsilon^*(z)$$ in a paragraph
  - math inside *italic* text (figure captions) is not rendered at all
  - every backslash + ASCII punctuation loses its backslash: \\{ \\} \\| \\, \\; \\! \\\\ \\&
  - & inside inline math is HTML-escaped and fails ("Unable to render expression")

The only safe forms are the ones GitHub hands to MathJax verbatim:
  inline   $`...`$
  display  a fenced block:
           ```math
           ...
           ```
--fix converts plain $...$ to $`...`$ and every $$...$$ to a ```math block (a $$...$$ sharing its line
with text becomes inline $`...`$). It also rewrites the escapes above (\\lbrace \\rbrace \\Vert \\thinspace
\\thickspace \\negthinspace \\cr) so the formulas stay correct either way.
& inside inline math must be fixed by hand (keep the & in the text).
Write money as \\$ (e.g. \\$294K) so it is never mistaken for math.

Usage: python .github/scripts/math_lint.py [--fix] [files...]   (default: every *.md)
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


def clean(formula):
    def sub(m):
        rep = REPLACE.get(m.group(0))
        if rep is None:
            return m.group(0)
        nxt = formula[m.end():m.end() + 1]
        return rep + (" " if nxt.isalpha() else "")
    return ESCAPE.sub(sub, formula)


def check(path, fix):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    problems, out, pos = [], [], 0
    masked = CODE.sub(lambda m: " " * len(m.group(0)), text)  # keep offsets, ignore code and $`...`$
    for m in MATH.finditer(masked):
        span = text[m.start():m.end()]
        line = text.count("\n", 0, m.start()) + 1
        if span.startswith("$`"):  # already safe
            continue
        display = span.startswith("$$")
        inner = span[2:-2] if display else span[1:-1]
        if "&" in inner and not display:
            problems.append(f"{path}:{line}: '&' inside inline math -> keep the & in the text")
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        line_end = len(text) if line_end < 0 else line_end
        alone = display and not text[line_start:m.start()].strip() and not text[m.end():line_end].strip()
        if alone:
            problems.append(f"{path}:{line}: display math must be a ```math block (run with --fix)")
            out.append(text[pos:line_start])
            out.append("```math\n" + clean(inner.strip()) + "\n```")
            pos = line_end
        else:
            problems.append(f"{path}:{line}: inline math must be written as $`...`$ (run with --fix)")
            out.append(text[pos:m.start()])
            out.append("$`" + clean(inner.strip()) + "`$")
            pos = m.end()
    out.append(text[pos:])
    if fix:
        new = "".join(out)
        if new != text:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)
    return problems


def main(argv):
    fix = "--fix" in argv
    files = [a for a in argv if not a.startswith("--")] or glob.glob("**/*.md", recursive=True)
    problems = [p for f in files for p in check(f, fix)]
    if fix:  # re-check: only what --fix cannot repair is left (& in inline math)
        problems = [p for f in files for p in check(f, False)]
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
