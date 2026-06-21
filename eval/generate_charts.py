"""Generate recruiter-ready eval charts from eval/results/*.json."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

RESULTS_DIR = Path("eval/results")
OUTPUT_DIR = Path("docs/benchmarks")

METRIC_KEYS = [
    "faithfulness",
    "context_precision",
    "context_recall",
    "answer_relevancy",
]

METRIC_LABELS = {
    "faithfulness": "Faithfulness",
    "context_precision": "Context Precision",
    "context_recall": "Context Recall",
    "answer_relevancy": "Answer Relevancy",
}

PROFILE_ORDER = ["naive", "hybrid", "hybrid+rerank", "hybrid+rerank+hyde", "hybrid+rerank+crag"]

PROFILE_LABELS = {
    "naive": "Baseline\n(Dense)",
    "hybrid": "Hybrid\nSearch",
    "hybrid+rerank": "Hybrid +\nRerank",
    "hybrid+rerank+hyde": "HyDE\nStack",
    "hybrid+rerank+crag": "CRAG\nStack",
}

PROFILE_COLORS = {
    "naive": "#64748b",
    "hybrid": "#06b6d4",
    "hybrid+rerank": "#8b5cf6",
    "hybrid+rerank+hyde": "#f59e0b",
    "hybrid+rerank+crag": "#10b981",
}

METRIC_COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#ec4899"]

BG = "#0b1120"
PANEL = "#111827"
GRID = "#1f2937"
TEXT = "#f8fafc"
MUTED = "#94a3b8"


def _latest_by_profile(results_dir: Path) -> dict[str, dict]:
    latest: dict[str, tuple[float, dict]] = {}
    for path in sorted(results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        payload = json.loads(path.read_text())
        profile = payload["profile"]
        mtime = path.stat().st_mtime
        if profile not in latest or mtime > latest[profile][0]:
            latest[profile] = (mtime, payload)
    return {k: v[1] for k, v in latest.items()}


def _composite_score(aggregate: dict) -> float:
    vals = [aggregate[k] for k in METRIC_KEYS if aggregate.get(k) is not None]
    return mean(vals) if vals else 0.0


def _setup_matplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": PANEL,
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT,
            "text.color": TEXT,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "grid.color": GRID,
            "font.family": "sans-serif",
            "font.sans-serif": ["Inter", "Segoe UI", "Helvetica Neue", "Arial"],
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.facecolor": BG,
            "savefig.bbox": "tight",
        }
    )


def _save(fig: plt.Figure, name: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / name
    fig.savefig(out, pad_inches=0.35)
    plt.close(fig)
    return out


def chart_grouped_bars(profiles: dict[str, dict]) -> Path:
    """Full-suite absolute scores: baseline vs hybrid vs rerank."""
    full_suite = ["naive", "hybrid", "hybrid+rerank"]
    data = {p: profiles[p]["aggregate"] for p in full_suite if p in profiles}

    x = np.arange(len(METRIC_KEYS))
    width = 0.24
    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.patch.set_facecolor(BG)

    for i, profile in enumerate(full_suite):
        if profile not in data:
            continue
        vals = [data[profile][k] for k in METRIC_KEYS]
        bars = ax.bar(
            x + (i - 1) * width,
            vals,
            width,
            label=PROFILE_LABELS[profile].replace("\n", " "),
            color=PROFILE_COLORS[profile],
            edgecolor="white",
            linewidth=0.6,
            alpha=0.92,
        )
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
                color=TEXT,
                fontweight="bold",
            )

    ax.set_xticks(x)
    ax.set_xticklabels([METRIC_LABELS[k] for k in METRIC_KEYS], fontsize=11)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("RAGAS Score (0–1)", fontsize=11)
    ax.set_title(
        "RAG Pipeline Benchmark — Full Suite (31 Questions)",
        fontsize=16,
        fontweight="bold",
        pad=16,
        color=TEXT,
    )
    ax.yaxis.grid(True, linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", framealpha=0.15, facecolor=PANEL, edgecolor=GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.text(
        0.5,
        0.02,
        "Enterprise Advanced RAG  ·  Kubernetes IT-Ops Corpus  ·  RAGAS Evaluation",
        ha="center",
        fontsize=9,
        color=MUTED,
    )
    return _save(fig, "01_profile_comparison_bar.png")


def chart_improvement_delta(profiles: dict[str, dict]) -> Path:
    """Lift over baseline — unique delta view, not absolute scores."""
    if "naive" not in profiles:
        raise ValueError("Baseline (naive) results required")

    baseline = profiles["naive"]["aggregate"]
    compare = ["hybrid", "hybrid+rerank"]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.patch.set_facecolor(BG)

    y_pos = np.arange(len(METRIC_KEYS))
    bar_h = 0.32

    for i, profile in enumerate(compare):
        if profile not in profiles:
            continue
        agg = profiles[profile]["aggregate"]
        deltas = [agg[k] - baseline[k] for k in METRIC_KEYS]
        colors = ["#10b981" if d >= 0 else "#ef4444" for d in deltas]
        bars = ax.barh(
            y_pos + (i - 0.5) * bar_h,
            deltas,
            height=bar_h,
            label=PROFILE_LABELS[profile].replace("\n", " "),
            color=colors if i == 0 else [PROFILE_COLORS[profile]] * len(deltas),
            alpha=0.85 if i else 0.75,
            edgecolor="white",
            linewidth=0.4,
        )
        for bar, delta in zip(bars, deltas):
            ax.text(
                delta + (0.01 if delta >= 0 else -0.01),
                bar.get_y() + bar.get_height() / 2,
                f"{delta:+.2f}",
                ha="left" if delta >= 0 else "right",
                va="center",
                fontsize=8,
                color=TEXT,
                fontweight="bold",
            )

    ax.axvline(0, color=MUTED, linewidth=1, linestyle="-")
    ax.set_yticks(y_pos)
    ax.set_yticklabels([METRIC_LABELS[k] for k in METRIC_KEYS])
    ax.set_xlabel("Δ vs Baseline (Dense-only)", fontsize=11)
    ax.set_title(
        "Lift Over Baseline — Hybrid & Reranking Impact",
        fontsize=15,
        fontweight="bold",
        pad=14,
        color=TEXT,
    )
    ax.xaxis.grid(True, linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", framealpha=0.15, facecolor=PANEL)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return _save(fig, "02_baseline_improvement.png")


def chart_metric_pies(profiles: dict[str, dict]) -> Path:
    """Metric balance per profile — all 5 stacks including filtered evals."""
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        "Score Composition by RAGAS Metric",
        fontsize=16,
        fontweight="bold",
        color=TEXT,
        y=0.98,
    )

    axes_flat = axes.flatten()

    for ax, profile in zip(axes_flat, PROFILE_ORDER):
        ax.set_facecolor(PANEL)
        if profile not in profiles:
            ax.axis("off")
            continue

        agg = profiles[profile]["aggregate"]
        vals = np.array([agg[k] for k in METRIC_KEYS], dtype=float)
        total = vals.sum()
        shares = vals / total if total else vals

        _, _, autotexts = ax.pie(
            shares,
            labels=None,
            colors=METRIC_COLORS,
            autopct=lambda p: f"{p:.0f}%" if p > 5 else "",
            startangle=90,
            pctdistance=0.78,
            wedgeprops={"width": 0.52, "edgecolor": BG, "linewidth": 2},
        )
        for t in autotexts:
            t.set_color(TEXT)
            t.set_fontsize(8)
            t.set_fontweight("bold")

        centre = plt.Circle((0, 0), 0.35, fc=PANEL, ec=GRID, linewidth=1)
        ax.add_artist(centre)
        score = _composite_score(agg)
        ax.text(0, 0.04, f"{score:.2f}", ha="center", va="center", fontsize=14, fontweight="bold", color=TEXT)
        ax.text(0, -0.12, "avg", ha="center", va="center", fontsize=8, color=MUTED)
        ax.set_title(
            PROFILE_LABELS[profile].replace("\n", " "),
            fontsize=11,
            fontweight="bold",
            color=TEXT,
            pad=8,
        )

        rows = profiles[profile].get("rows", [])
        filt = profiles[profile].get("filter")
        note = f"{len(rows)} Q" + (f" · {filt} filter" if filt else " · full suite")
        ax.text(0, -1.25, note, ha="center", fontsize=8, color=MUTED)

    for ax in axes_flat[len(PROFILE_ORDER) :]:
        ax.axis("off")

    legend_patches = [
        mpatches.Patch(color=METRIC_COLORS[i], label=METRIC_LABELS[k])
        for i, k in enumerate(METRIC_KEYS)
    ]
    fig.legend(
        handles=legend_patches,
        loc="lower center",
        ncol=4,
        framealpha=0.15,
        facecolor=PANEL,
        edgecolor=GRID,
        bbox_to_anchor=(0.5, 0.02),
        fontsize=9,
    )
    plt.subplots_adjust(wspace=0.15, hspace=0.35, bottom=0.12, top=0.9)
    return _save(fig, "03_metric_composition_pies.png")


def chart_feature_spotlight(profiles: dict[str, dict]) -> Path:
    """HyDE & CRAG on their targeted question sets only."""
    feature_profiles = ["hybrid+rerank+hyde", "hybrid+rerank+crag"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        "Advanced Techniques — Feature-Targeted Evaluation",
        fontsize=15,
        fontweight="bold",
        color=TEXT,
        y=1.02,
    )

    for ax, profile in zip(axes, feature_profiles):
        ax.set_facecolor(PANEL)
        if profile not in profiles:
            ax.axis("off")
            continue

        agg = profiles[profile]["aggregate"]
        vals = [agg[k] for k in METRIC_KEYS]
        bars = ax.bar(
            [METRIC_LABELS[k] for k in METRIC_KEYS],
            vals,
            color=PROFILE_COLORS[profile],
            edgecolor="white",
            linewidth=0.6,
            alpha=0.9,
        )
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{val:.2f}",
                ha="center",
                fontsize=9,
                fontweight="bold",
                color=TEXT,
            )

        payload = profiles[profile]
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Score")
        ax.set_title(
            f"{PROFILE_LABELS[profile].replace(chr(10), ' ')}  ({len(payload['rows'])} questions)",
            fontweight="bold",
            pad=10,
        )
        ax.yaxis.grid(True, linestyle="--", alpha=0.35)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", rotation=15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    return _save(fig, "04_feature_spotlight.png")


def main() -> None:
    if not RESULTS_DIR.exists():
        raise SystemExit(f"No results in {RESULTS_DIR}. Run make eval-* first.")

    profiles = _latest_by_profile(RESULTS_DIR)
    if not profiles:
        raise SystemExit("No eval JSON files found.")

    _setup_matplotlib()
    outputs = [
        chart_grouped_bars(profiles),
        chart_improvement_delta(profiles),
        chart_metric_pies(profiles),
        chart_feature_spotlight(profiles),
    ]

    print("\nGenerated benchmark visuals:")
    for path in outputs:
        print(f"  {path}")


if __name__ == "__main__":
    main()
