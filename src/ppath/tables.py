"""Write booktabs LaTeX tables."""

from __future__ import annotations

from pathlib import Path


def latex_table(
    path: Path,
    header: list[str],
    rows: list[list[str]],
    align: str,
    caption: str,
    label: str,
    notes: str | None = None,
    size: str = "\\small",
    colsep: str | None = None,
) -> None:
    lines = [
        "\\begin{table}[tbp]",
        "\\centering",
        size,
        *([f"\\setlength{{\\tabcolsep}}{{{colsep}}}"] if colsep else []),
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\begin{threeparttable}",
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
    ]
    lines += [" & ".join(r) + " \\\\" for r in rows]
    lines += ["\\bottomrule", "\\end{tabular}"]
    if notes:
        lines += [
            "\\begin{tablenotes}[flushleft]",
            "\\footnotesize",
            f"\\item \\textit{{Notes:}} {notes}",
            "\\end{tablenotes}",
        ]
    lines += ["\\end{threeparttable}", "\\end{table}", ""]
    path.write_text("\n".join(lines))


def latex_longtable(
    path: Path,
    header: list[str],
    rows: list[list[str]],
    align: str,
    caption: str,
    label: str,
    notes: str | None = None,
    size: str = "\\footnotesize",
    colsep: str = "4pt",
) -> None:
    """A multi-page table (requires the longtable and booktabs packages)."""
    head = " & ".join(header) + " \\\\"
    n = len(align.replace("@{}", ""))
    lines = [
        "\\begingroup",
        size,
        f"\\setlength{{\\tabcolsep}}{{{colsep}}}",
        f"\\begin{{longtable}}{{{align}}}",
        f"\\caption{{{caption}}}\\label{{{label}}}\\\\",
        "\\toprule",
        head,
        "\\midrule",
        "\\endfirsthead",
        f"\\multicolumn{{{n}}}{{l}}{{\\textit{{(continued)}}}}\\\\",
        "\\toprule",
        head,
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endfoot",
        "\\bottomrule",
    ]
    lines.append("\\endlastfoot")
    lines += [" & ".join(r) + " \\\\" for r in rows]
    lines += ["\\end{longtable}"]
    if notes:
        lines += ["\\vspace{-6pt}", f"\\noindent{{\\footnotesize\\textit{{Notes:}} {notes}\\par}}"]
    lines += ["\\endgroup", ""]
    path.write_text("\n".join(lines))
