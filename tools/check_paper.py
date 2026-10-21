"""Static checks on the paper source.

1. Every number macro used in main.tex is defined by the pipeline.
2. Every citation key exists in references.bib (and lists uncited entries).
3. Lists every digit sequence typed directly in the prose, so each one can be
   reviewed: results must come from macros; only definitions, thresholds,
   years and labels may be typed.

Usage: python tools/check_paper.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1] / "paper"


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


REVIEWED = Path(__file__).resolve().parent / "typed_numbers_reviewed.tsv"
NUM = re.compile(r"(?<![A-Za-z\\])\d[\d.,]*")


def typed_numbers() -> list[tuple[str, str, str]]:
    """Every number typed in the manuscript body outside a macro, except four-digit years.

    Each is returned as (file, number, preceding 40 characters), which identifies it
    in typed_numbers_reviewed.tsv.
    """
    out = []
    for p in [PAPER / "main.tex", *sorted((PAPER / "sections").glob("*.tex"))]:
        t = strip_comments(p.read_text())
        if p.name == "main.tex":
            t = t.split("\\begin{document}", 1)[1]
        t = re.sub(r"\\(label|ref|cref|Cref|input|includegraphics|cite[pt]?|citealp|eqref|href|url)(\[[^\]]*\])?\{[^}]*\}",
                   " ", t)
        t = re.sub(r"\\n[A-Z][A-Za-z]*", " ", t)
        for m in NUM.finditer(t):
            num = m.group().rstrip(".,")
            if re.fullmatch(r"(18[5-9]\d|19\d\d|20\d\d|2100)", num):
                continue
            ctx = re.sub(r"\s+", " ", t[max(0, m.start() - 40):m.start()]).replace("\t", " ")
            out.append((p.name, num, ctx))
    return out


def main() -> int:
    sources = [PAPER / "main.tex", *sorted((PAPER / "sections").glob("*.tex"))]
    tex = "\n".join(strip_comments(p.read_text()) for p in sources)
    tables = "".join(strip_comments(p.read_text()) for p in (PAPER.parent / "results" / "tables").glob("*.tex"))
    defined = set(re.findall(r"\\newcommand\{\\(n[A-Z][A-Za-z]*)\}", (PAPER / "numbers.tex").read_text()))
    used = set(re.findall(r"\\(n[A-Z][A-Za-z]*)", tex))
    missing = sorted(used - defined)
    unused = sorted(defined - used)

    bib = (PAPER / "references.bib").read_text()
    keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    cited = set()
    for group in re.findall(r"\\cite[a-z]*\*?(?:\[[^\]]*\])?\{([^}]+)\}", tex + tables):
        cited |= {k.strip() for k in group.split(",")}
    bad_cites = sorted(cited - keys)
    uncited = sorted(keys - cited)

    # typed numbers in the body (exclude preamble, labels, refs, includes, math macros)
    body = tex.split("\\begin{document}", 1)[1] if "\\begin{document}" in tex else tex
    body = re.sub(r"\\(label|ref|cref|Cref|input|includegraphics|cite[pt]?|eqref|href|url)(\[[^\]]*\])?\{[^}]*\}",
                  " ", body)
    body = re.sub(r"\\n[A-Z][A-Za-z]*", " ", body)
    flagged = typed_numbers()

    print(f"macros used: {len(used)}, defined: {len(defined)}")
    print("MISSING macros:", missing or "none")
    print("unused macros:", ", ".join(unused) or "none")
    print("UNKNOWN citation keys:", bad_cites or "none")
    print("uncited bib entries:", ", ".join(uncited) or "none")
    reviewed = {}
    for ln in REVIEWED.read_text().splitlines():
        if ln.strip() and not ln.startswith("#"):
            f, num, ctx, cat = ln.split("\t")
            reviewed[(f, num, ctx)] = cat
    unreviewed = [k for k in flagged if k not in reviewed]
    stale = [k for k in reviewed if k not in set(flagged)]
    cats: dict[str, int] = {}
    for k in flagged:
        if k in reviewed:
            cats[reviewed[k]] = cats.get(reviewed[k], 0) + 1
    print(f"\ntyped numbers outside macros (years excluded): {len(flagged)}")
    for c, n in sorted(cats.items()):
        print(f"  reviewed, {c}: {n}")
    print("UNREVIEWED typed numbers:", len(unreviewed))
    for f, num, ctx in unreviewed:
        print(f"  {f}  [{num}]  ...{ctx}")
    print("stale review entries:", len(stale))
    bad = missing or bad_cites or unused or uncited or unreviewed or stale
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
