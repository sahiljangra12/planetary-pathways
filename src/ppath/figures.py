"""Publication figures (vector PDF + PNG preview). All inputs are pipeline outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from . import config  # noqa: E402

QCOL = {
    "Shortfall, within boundary": "#7B97C2",
    "Shortfall and overshoot": "#E09A4F",
    "Foundation met, overshoot": "#B5474F",
    "Safe and just": "#3E9C6E",
}
CONT_COL = {"Africa": "#D08C3A", "America": "#4C8C6E", "Asia": "#B5474F", "Europe": "#4F6FA8", "Oceania": "#8A6BB0"}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 8.5,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "lines.linewidth": 1.2,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)

TONNES = FuncFormatter(lambda v, _: f"{v:g}")


def _save(fig, name: str) -> Path:
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    path = config.FIGURES / f"{name}.pdf"
    fig.savefig(path)
    fig.savefig(config.FIGURES / f"{name}.png", dpi=200)
    plt.close(fig)
    return path


def fig_space(period_scored: pd.DataFrame, period: str, labels: list[str]) -> Path:
    """Social attainment (lowest capped ratio) against consumption CO2 per capita."""
    from adjustText import adjust_text

    d = period_scored[(period_scored["period"] == period)].dropna(
        subset=["co2_cons_pc", "social_min_ratio", "quadrant"]
    )
    fig, ax = plt.subplots(figsize=(6.6, 4.3))
    b = config.CO2_BOUNDARY.value
    cut = config.FOUNDATION_CUTOFF
    xmin, xmax = 0.08, 60
    ax.fill_between([xmin, b], cut, 1.04, color=QCOL["Safe and just"], alpha=0.15, lw=0, zorder=0)
    ax.axvline(b, color="#333", lw=0.8, ls="--", zorder=1)
    ax.axhline(cut, color="#333", lw=0.8, ls=":", zorder=1)
    sizes = 10 + 160 * np.sqrt(d["population"] / d["population"].max())
    for q in config.QUADRANT_ORDER:
        g = d[d["quadrant"] == q]
        if len(g):
            ax.scatter(
                g["co2_cons_pc"],
                g["social_min_ratio"],
                s=sizes.loc[g.index],
                c=QCOL[q],
                alpha=0.85,
                edgecolor="white",
                linewidth=0.4,
                label=f"{q} ({len(g)})",
                zorder=3,
            )
    texts = []
    for iso in labels:
        r = d[d["iso3"] == iso]
        if len(r):
            r = r.iloc[0]
            texts.append(
                ax.text(r["co2_cons_pc"], r["social_min_ratio"], r["country"], fontsize=6.3, color="#222", zorder=4)
            )
    ax.set_xscale("log")
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(0.15, 1.06)
    ax.xaxis.set_major_formatter(TONNES)
    ax.set_xlabel("Consumption-based CO$_2$ emissions (t per person per year, log scale)")
    ax.set_ylabel("Social attainment\n(weakest indicator as a share of its threshold)")
    ax.text(b * 1.05, 0.17, f"Climate boundary\n{b:g} t per person", fontsize=6.5, color="#333", va="bottom")
    ax.text(xmin * 1.1, 1.012, "Safe and just space (empty)", fontsize=6.5, color="#2b6e4d", va="bottom")
    ax.text(xmin * 1.1, cut - 0.012, "Social foundation", fontsize=6.5, color="#333", va="top")
    adjust_text(texts, ax=ax, expand=(1.15, 1.4), arrowprops=dict(arrowstyle="-", color="#888", lw=0.4))
    ax.legend(loc="lower right", frameon=False, markerscale=0.7, bbox_to_anchor=(1.0, 0.04))
    lo, hi = config.PERIODS[period]
    ax.set_title(f"Period means {lo}–{hi}; marker area proportional to population", loc="left")
    return _save(fig, "fig1_space")


def fig_shares(shares: pd.DataFrame, shares_pop: pd.DataFrame, n_countries: int) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.8), sharey=True)
    for ax, s, title in [
        (axes[0], shares, f"a  Countries (n = {n_countries})"),
        (axes[1], shares_pop, "b  Population-weighted"),
    ]:
        s = s[config.QUADRANT_ORDER].fillna(0)
        ax.stackplot(
            s.index,
            s.T.values * 100,
            colors=[QCOL[q] for q in config.QUADRANT_ORDER],
            alpha=0.9,
            labels=config.QUADRANT_ORDER,
            lw=0,
        )
        ax.set_xlim(s.index.min(), s.index.max())
        ax.set_ylim(0, 100)
        ax.set_title(title, loc="left")
        ax.set_xlabel("Year")
    axes[0].set_ylabel("%")
    handles, lab = axes[0].get_legend_handles_labels()
    fig.legend(handles, lab, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.12))
    fig.subplots_adjust(wspace=0.12)
    return _save(fig, "fig2_shares")


def fig_requirement(annual: dict, pooled: dict, years: list[int]) -> Path:
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    spec = [
        ("main", "Social foundation (four indicators), consumption CO$_2$", "#B5474F", "-", True),
        ("production", "Social foundation, production CO$_2$", "#4F6FA8", "--", False),
        ("health", "Health thresholds only, consumption CO$_2$", "#3E9C6E", "-.", True),
    ]
    for key, lab, col, ls, points in spec:
        p = pooled[key]
        est = [p[f"req_{t}"] for t in years]
        lo = [p[f"req_{t}_lo"] for t in years]
        hi = [p[f"req_{t}_hi"] for t in years]
        ax.plot(years, est, color=col, ls=ls, label=lab, zorder=3)
        ax.fill_between(years, lo, hi, color=col, alpha=0.13, lw=0)
        if points:
            d = annual[key].dropna(subset=["requirement"])
            ax.scatter(d["year"], d["requirement"], s=7, color=col, alpha=0.55, lw=0, zorder=2)
    b, b15 = config.CO2_BOUNDARY.value, config.CO2_BOUNDARY_15.value
    ax.axhline(b, color="#333", lw=0.8, ls=":")
    ax.text(years[0] + 0.2, b * 1.07, f"Climate boundary {b:g} t (2 °C)", fontsize=6.5)
    ax.axhline(b15, color="#777", lw=0.6, ls=":")
    ax.text(years[0] + 0.2, b15 * 1.07, f"{b15:g} t (1.5 °C)", fontsize=6.5, color="#555")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(TONNES)
    ax.set_ylim(0.6, 60)
    ax.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    ax.set_ylabel("CO$_2$ per person at which half of\ncountries meet the thresholds (t, log)")
    ax.set_xlabel("Year")
    ax.legend(frameon=False, loc="upper right")
    return _save(fig, "fig3_requirement")


def fig_decoupling(dec: pd.DataFrame) -> Path:
    d = dec[(dec["class"] == "Absolute") & dec["above_boundary"]].sort_values("co2_growth")
    fig, ax = plt.subplots(figsize=(6.4, 0.16 * len(d) + 0.9))
    y = np.arange(len(d))
    ax.hlines(y, d["required_growth"], d["co2_growth"], color="#bbb", lw=0.8, zorder=1)
    ax.errorbar(
        d["co2_growth"],
        y,
        xerr=[d["co2_growth"] - d["co2_growth_lo"], d["co2_growth_hi"] - d["co2_growth"]],
        fmt="o",
        ms=3.2,
        color="#B5474F",
        elinewidth=0.6,
        capsize=0,
        label="Achieved, 2011–2022 (95% CI)",
        zorder=3,
    )
    ax.scatter(
        d["required_growth"], y, marker="|", s=40, color="#222", label="Required to reach 1.61 t by 2050", zorder=3
    )
    ax.set_yticks(y, d["country"])
    ax.axvline(0, color="#999", lw=0.6)
    ax.invert_yaxis()
    ax.set_xlabel("Annual change in consumption-based CO$_2$ per person (%)")
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    return _save(fig, "fig4_decoupling")


def fig_transitions(mats: dict[str, pd.DataFrame]) -> Path:
    short = ["Shortfall,\nwithin", "Shortfall,\novershoot", "Met,\novershoot", "Safe and\njust"]
    fig, axes = plt.subplots(1, len(mats), figsize=(6.6, 2.7))
    for k, (ax, (title, m)) in enumerate(zip(axes, mats.items(), strict=True)):
        title = f"{'abcdef'[k]}  {title}"
        v = m.to_numpy()
        rows = v.sum(axis=1, keepdims=True)
        share = np.divide(v, rows, out=np.zeros_like(v, dtype=float), where=rows > 0)
        ax.imshow(share, cmap="Greys", vmin=0, vmax=1.4)
        for i in range(4):
            for j in range(4):
                if v[i, j]:
                    ax.text(
                        j,
                        i,
                        f"{v[i, j]}",
                        ha="center",
                        va="center",
                        fontsize=7,
                        color="white" if share[i, j] > 0.7 else "#111",
                    )
        ax.set_xticks(range(4), short, fontsize=6)
        ax.set_yticks(range(4), short, fontsize=6)
        ax.set_title(title, loc="left")
        ax.set_xlabel("To")
        ax.spines[:].set_visible(False)
    axes[0].set_ylabel("From")
    return _save(fig, "fig5_transitions")


def fig_gmm(bic: dict) -> Path:
    fig, ax = plt.subplots(figsize=(3.2, 2.2))
    ks = list(bic)
    ax.plot(ks, [bic[k] for k in ks], "o-", color="#4F6FA8", ms=3)
    ax.set_xlabel("Number of mixture components")
    ax.set_ylabel("BIC")
    return _save(fig, "figA2_gmm_bic")


def fig_framework() -> Path:
    """Conceptual diagram of the four configurations."""
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    cells = [
        (0, 0, "Shortfall, within boundary", "Basic needs unmet; emissions\nwithin the per-capita share"),
        (1, 0, "Shortfall and overshoot", "Basic needs unmet despite\nemissions above the share"),
        (1, 1, "Foundation met, overshoot", "Basic needs met, but with\nemissions above the share"),
        (0, 1, "Safe and just", "Basic needs met with emissions\nwithin the per-capita share"),
    ]
    for x, y, title, desc in cells:
        ax.add_patch(plt.Rectangle((x + 0.03, y + 0.03), 0.94, 0.94, color=QCOL[title], alpha=0.25, lw=0))
        ax.text(x + 0.5, y + 0.62, title, ha="center", va="center", fontsize=8.5, weight="bold", color="#222")
        ax.text(x + 0.5, y + 0.36, desc, ha="center", va="center", fontsize=7, color="#333")
    ax.axvline(1, color="#333", lw=1.0, ls="--")
    ax.axhline(1, color="#333", lw=1.0, ls=":")
    ax.set_xticks(
        [0.5, 1.5], ["Within boundary\n(CO$_2$ ≤ 1.61 t per person)", "Overshoot\n(CO$_2$ > 1.61 t per person)"]
    )
    ax.set_yticks([0.5, 1.5], ["Shortfall\n(any threshold missed)", "Foundation met\n(all thresholds met)"])
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.annotate(
        "",
        xy=(1.55, 1.25),
        xytext=(0.45, 0.75),
        arrowprops=dict(arrowstyle="->", color="#555", lw=1.0, connectionstyle="arc3,rad=-0.25"),
    )
    ax.text(
        0.98,
        0.98,
        "typical historical\npath",
        fontsize=6.5,
        color="#555",
        ha="center",
        va="center",
        bbox=dict(fc="white", ec="none", pad=1),
    )
    return _save(fig, "fig0_framework")


def fig_coverage(panel: pd.DataFrame, cols: dict[str, str]) -> Path:
    """Share of countries with an observed value, by indicator and year."""
    share = pd.DataFrame({lab: panel.groupby("year")[c].apply(lambda s: s.notna().mean()) for c, lab in cols.items()}).T
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    im = ax.imshow(share.to_numpy() * 100, aspect="auto", cmap="Blues", vmin=0, vmax=100)
    ax.set_yticks(range(len(share)), share.index)
    years = share.columns.to_numpy()
    ticks = [i for i, y in enumerate(years) if y % 5 == 0]
    ax.set_xticks(ticks, years[ticks])
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("% of countries observed", fontsize=7)
    return _save(fig, "figA_coverage")


def fig_trends(panel: pd.DataFrame, series: dict[str, tuple[str, float | None, bool]]) -> Path:
    """Median and interquartile range across countries for each indicator, by year."""
    n = len(series)
    fig, axes = plt.subplots(2, (n + 1) // 2, figsize=(6.8, 4.2))
    axes = axes.ravel()
    for ax, (col, (lab, thr, logy)) in zip(axes, series.items(), strict=False):
        g = panel.groupby("year")[col]
        q = g.quantile([0.25, 0.5, 0.75]).unstack()
        ax.fill_between(q.index, q[0.25], q[0.75], color="#4F6FA8", alpha=0.2, lw=0)
        ax.plot(q.index, q[0.5], color="#4F6FA8")
        if thr is not None:
            ax.axhline(thr, color="#B5474F", ls="--", lw=0.8)
        if logy:
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(TONNES)
        ax.set_title(lab, loc="left", fontsize=7.5)
        ax.tick_params(labelsize=6.5)
    for ax in axes[n:]:
        ax.set_visible(False)
    fig.tight_layout()
    return _save(fig, "fig_trends")
