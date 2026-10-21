"""Compare the WDI extract with values retrieved from the live World Bank API.

The reference files in verification/ were retrieved from api.worldbank.org on
21 October 2026 (database last updated 8 October 2026). They cover the four
social indicators for the countries whose classification is closest to a
threshold. The script reports the largest absolute difference per indicator and
whether any difference would move a value across its threshold.

    python tools/wdi_spotcheck.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppath.data import load_wdi  # noqa: E402

V = ROOT / "verification"
FILES = {
    # file: (variable in extract, threshold, higher is better)
    "wb_le.txt": ("life_expectancy", 74.0, True),
    "wb_el.txt": ("electricity_access", 95.0, True),
    "wb_ue.txt": ("unemployment", 6.0, False),
    "u5mr_wb_2026-10.txt": ("child_mortality", 25.0, False),
}


def read_ref(path: Path) -> pd.DataFrame:
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    header = [ln for ln in lines if ln.startswith("#")][-1].lstrip("# ").split()
    rows = [ln.split() for ln in lines if not ln.startswith("#") and not ln.startswith("year")]
    if header[0] != "year":  # u5mr file has an uncommented header line
        header = [ln for ln in lines if ln.startswith("year")][0].split()
    df = pd.DataFrame(rows, columns=header).astype(float)
    df["year"] = df["year"].astype(int)
    return df.set_index("year")


def main() -> int:
    wdi = load_wdi()
    total = flips = 0
    for fname, (var, thr, higher) in FILES.items():
        ref = read_ref(V / fname)
        loc = wdi[wdi["iso3"].isin(ref.columns)].pivot(index="year", columns="iso3", values=var)
        loc = loc.loc[ref.index, ref.columns]
        diff = (loc - ref).abs()
        n = int(ref.notna().sum().sum())
        total += n
        side = (lambda x: x >= thr) if higher else (lambda x: x <= thr)
        flip = side(loc) != side(ref)
        flip_list = [(c, y) for c in ref.columns for y in ref.index if flip.loc[y, c]]
        flips += len(flip_list)
        print(f"{var:20s} values={n:4d} max|diff|={diff.max().max():.2f} "
              f"differing={int((diff > 1e-9).sum().sum()):3d} threshold flips={flip_list}")
    print(f"\n{total} values compared; {flips} values on the other side of a threshold")

    # do the differences change any classification? substitute the API values and rescore
    from ppath.indicators import score

    panel = pd.read_csv(ROOT / "data" / "processed" / "panel.csv")
    panel = panel[panel["year"] >= 1991]
    alt = panel.copy().set_index(["iso3", "year"])
    for fname, (var, _, _) in FILES.items():
        ref = read_ref(V / fname).stack().rename(var)
        ref.index = ref.index.swaplevel()
        ref.index.names = ["iso3", "year"]
        common = ref.index.intersection(alt.index)
        alt.loc[common, var] = ref.loc[common].values
        if var == "unemployment":
            alt.loc[common, "employment"] = 100 - ref.loc[common].values
    a = score(panel)
    b = score(alt.reset_index())
    a = a.set_index(["iso3", "year"])["quadrant"].astype(object).fillna("unclassified")
    b = b.set_index(["iso3", "year"])["quadrant"].astype(object).fillna("unclassified").reindex(a.index)
    changed = a[a != b]
    print(f"classifications changed by substituting API values: {len(changed)}")
    for k in changed.index:
        print("  ", k, a[k], "->", b[k])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
