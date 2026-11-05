"""
Step 3: Winning Patterns
For each ad label (hook_type, ad_format, child_on_screen, etc.) compare the
performance of ads that have that label vs ads that don't.

Rules (from the brief):
  - Only use ads above the spend threshold (low_spend == False).
  - Always control for product_form: run analysis on ALL ads, then gummies only,
    then milk_mix_powder only.
  - Report n (number of ads) alongside every finding.
  - Use bootstrap confidence intervals so we know how reliable each finding is.
  - Only keep patterns that hold on MORE THAN ONE metric and have enough ads (MIN_N).
    Mark the rest "weak_signal".
  - Multi-value labels (e.g. "storytelling; identity_appeal") are split and each
    value is counted individually.

Run from the repo root:  python src/step3_winning_patterns.py

Outputs:
  intermediate/winning_patterns.csv    one row per label value, all metrics
  intermediate/winning_patterns_summary.md    plain-English summary of kept findings
"""

import os
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── config ─────────────────────────────────────────────────────────────────────
MIN_N          = 5      # minimum ads in a group to report a finding
BOOTSTRAP_REPS = 1000   # number of bootstrap samples for confidence intervals
RANDOM_SEED    = 42

# Labels to analyse. Multi-value columns (semicolon-separated) are listed separately.
SINGLE_LABELS = [
    "hook_type", "ad_format", "child_on_screen", "brand_first_said",
    "language", "creator_type", "production", "humour", "cta_type",
    "creator_gender", "setting", "child_in_first_3s",
]
# NOTE: product_form is deliberately NOT a creative label. It is the product
# being sold (gummies vs milk_mix_powder), used only to split the analysis into
# scopes below. Inside each product scope it has a single value, so comparing it
# as a label would be meaningless ("gummies ads vs non-gummies ads").
MULTI_LABELS = [
    "child_role", "proof_used", "persuasion",
]

# Metrics we compare across groups
METRICS = ["roas", "hook_rate", "hold_rate", "ctr", "conversion_rate"]

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INTER_DIR  = os.path.join(BASE, "intermediate")
os.makedirs(INTER_DIR, exist_ok=True)

# ── load ───────────────────────────────────────────────────────────────────────
ads = pd.read_csv(os.path.join(INTER_DIR, "ad_metrics.csv"))

# Keep only ads above the spend threshold
ads = ads[~ads["low_spend"]].copy()
print(f"Ads above spend threshold: {len(ads)}")

# ── helper: bootstrap confidence interval ─────────────────────────────────────
def bootstrap_ci(values, reps=BOOTSTRAP_REPS, ci=0.95, seed=RANDOM_SEED):
    """
    Returns (mean, lower_ci, upper_ci) for a 1-D array of values.
    Uses bootstrap resampling so we get a range, not just a point estimate.
    """
    values = np.array(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = [rng.choice(values, size=len(values), replace=True).mean()
             for _ in range(reps)]
    lower = np.percentile(means, (1 - ci) / 2 * 100)
    upper = np.percentile(means, (1 + ci) / 2 * 100)
    return round(values.mean(), 4), round(lower, 4), round(upper, 4)

# ── helper: compare one label value vs rest ───────────────────────────────────
def compare_group(df, label_col, label_val, product_scope):
    """
    For a given label value (e.g. hook_type = 'problem_statement'),
    compare that group vs all other ads on every metric.
    Returns a dict of results.
    """
    in_group  = df[df[label_col] == label_val]
    out_group = df[df[label_col] != label_val]

    n_in  = len(in_group)
    n_out = len(out_group)

    if n_in < MIN_N:
        return None

    row = {
        "product_scope": product_scope,
        "label_col":     label_col,
        "label_val":     label_val,
        "n_in_group":    n_in,
        "n_out_group":   n_out,
    }

    metrics_better = 0  # count how many metrics this group wins on

    for metric in METRICS:
        mean_in,  lo_in,  hi_in  = bootstrap_ci(in_group[metric])
        mean_out, lo_out, hi_out = bootstrap_ci(out_group[metric])

        row[f"{metric}_in"]      = mean_in
        row[f"{metric}_out"]     = mean_out
        row[f"{metric}_lo"]      = lo_in
        row[f"{metric}_hi"]      = hi_in
        row[f"{metric}_delta"]   = round(mean_in - mean_out, 4) if not (
            np.isnan(mean_in) or np.isnan(mean_out)) else np.nan

        # "better" means CI of in-group is clearly above mean of out-group
        if not np.isnan(lo_in) and not np.isnan(mean_out):
            if lo_in > mean_out:
                metrics_better += 1

    row["metrics_better"] = metrics_better

    # Signal strength:
    # strong  = beats out-group on 3+ metrics
    # moderate= beats on 2 metrics
    # weak_signal = only 1 metric or CI overlaps
    if metrics_better >= 3:
        row["signal"] = "strong"
    elif metrics_better == 2:
        row["signal"] = "moderate"
    else:
        row["signal"] = "weak_signal"

    return row

# ── helper: expand multi-value columns ────────────────────────────────────────
def expand_multi(df, col):
    """
    For columns like 'storytelling; identity_appeal; social_proof',
    create a binary column per unique value so we can treat each separately.
    Returns a copy of df with new binary columns prefixed with col + '__'.
    """
    df = df.copy()
    all_vals = (df[col].dropna()
                .str.split(";")
                .explode()
                .str.strip()
                .unique())
    for val in all_vals:
        if val:
            df[f"{col}__{val}"] = df[col].fillna("").str.contains(
                val, regex=False).astype(int)
    return df, [f"{col}__{v}" for v in all_vals if v]

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# Run for three product scopes: all, gummies only, milk_mix_powder only
# ══════════════════════════════════════════════════════════════════════════════
scopes = {
    "all":            ads,
    "gummies":        ads[ads["product_form"] == "gummies"],
    "milk_mix_powder":ads[ads["product_form"] == "milk_mix_powder"],
}

# ── context: product form (NOT a creative pattern) ────────────────────────────
# product_form is what is being sold, not a creative choice. We show its
# descriptive stats here purely for context, and analyse it as a SCOPE (above),
# never as a label in the pattern comparison.
product_context = (
    ads.groupby("product_form")
       .agg(n_ads=("ad_id", "size"),
            median_roas=("roas", "median"),
            median_cost_per_purchase=("cost_per_purchase", "median"))
       .round(2)
       .reset_index()
)
print("\nContext: product form (not a creative pattern)")
print(product_context.to_string(index=False))

all_rows = []

for scope_name, scope_df in scopes.items():
    print(f"\n--- Scope: {scope_name} ({len(scope_df)} ads) ---")

    # -- single-value labels --------------------------------------------------
    for col in SINGLE_LABELS:
        if col not in scope_df.columns:
            continue
        for val in scope_df[col].dropna().unique():
            result = compare_group(scope_df, col, val, scope_name)
            if result:
                all_rows.append(result)

    # -- multi-value labels ---------------------------------------------------
    for col in MULTI_LABELS:
        if col not in scope_df.columns:
            continue
        expanded_df, binary_cols = expand_multi(scope_df, col)
        for bcol in binary_cols:
            val_name = bcol.split("__", 1)[1]
            # treat the binary column: 1 = has this value, 0 = doesn't
            sub = expanded_df.copy()
            sub[bcol + "_label"] = sub[bcol].map({1: "yes", 0: "no"})
            result = compare_group(sub, bcol + "_label", "yes", scope_name)
            if result:
                result["label_col"] = col          # restore original col name
                result["label_val"] = val_name     # restore original val name
                all_rows.append(result)

# ── build results dataframe ───────────────────────────────────────────────────
results = pd.DataFrame(all_rows)

# Sort: strong signals first, then by number of metrics won, then by roas delta
results = results.sort_values(
    ["signal", "metrics_better", "roas_delta"],
    ascending=[True, False, False],
    key=lambda col: col.map({"strong": 0, "moderate": 1, "weak_signal": 2})
    if col.name == "signal" else col
)

# ── save full results ─────────────────────────────────────────────────────────
csv_path = os.path.join(INTER_DIR, "winning_patterns.csv")
results.to_csv(csv_path, index=False)
print(f"\nFull results saved: {csv_path}  ({len(results)} rows)")

# ── print summary to console ──────────────────────────────────────────────────
strong   = results[results["signal"] == "strong"]
moderate = results[results["signal"] == "moderate"]
weak     = results[results["signal"] == "weak_signal"]

print(f"\nSignal breakdown:")
print(f"  Strong   (3+ metrics): {len(strong)}")
print(f"  Moderate (2 metrics) : {len(moderate)}")
print(f"  Weak     (0-1 metric): {len(weak)}")

# ══════════════════════════════════════════════════════════════════════════════
# WRITE PLAIN-ENGLISH SUMMARY
# One sentence per kept finding (strong + moderate, all-ads scope only)
# ══════════════════════════════════════════════════════════════════════════════
kept = results[
    (results["signal"].isin(["strong", "moderate"])) &
    (results["product_scope"] == "all")
].copy()

lines = []
lines.append("# Winning Patterns — Summary\n")
lines.append("_Generated by src/step3_winning_patterns.py_\n")
lines.append(f"Ads analysed (above spend threshold): {len(ads)}  \n")
lines.append(f"Strong signals: {len(strong[strong['product_scope']=='all'])}  |  "
             f"Moderate signals: {len(moderate[moderate['product_scope']=='all'])}  |  "
             f"Weak (excluded): {len(weak[weak['product_scope']=='all'])}\n")

# ── context table: product form (not a creative pattern) ──────────────────────
lines.append("\n## Context: product form (not a creative pattern)\n")
lines.append("_Product form is analysed as a **scope**, not as a creative pattern, "
             "because it is a product attribute (what is being sold) rather than a "
             "creative choice. The analysis is run separately within each product "
             "form; product_form itself is never compared as a label._\n")
lines.append("| Product form | n ads | Median ROAS | Median cost per purchase |")
lines.append("|---|---|---|---|")
for _, r in product_context.iterrows():
    cpp = "n/a" if np.isnan(r["median_cost_per_purchase"]) else f"{r['median_cost_per_purchase']:.2f}"
    roas = "n/a" if np.isnan(r["median_roas"]) else f"{r['median_roas']:.2f}"
    lines.append(f"| {r['product_form']} | {int(r['n_ads'])} | {roas} | {cpp} |")

lines.append("\n## Strong and Moderate Patterns (all products)\n")
lines.append("| Label | Value | n | ROAS delta | Metrics won | Signal |")
lines.append("|---|---|---|---|---|---|")

for _, row in kept.iterrows():
    roas_d = f"{row['roas_delta']:+.3f}" if not np.isnan(row["roas_delta"]) else "n/a"
    lines.append(
        f"| {row['label_col']} | {row['label_val']} | {int(row['n_in_group'])} "
        f"| {roas_d} | {int(row['metrics_better'])} | {row['signal']} |"
    )

# Per-product breakdowns
for scope in ["gummies", "milk_mix_powder"]:
    scope_kept = results[
        (results["signal"].isin(["strong", "moderate"])) &
        (results["product_scope"] == scope)
    ]
    lines.append(f"\n## Strong and Moderate Patterns ({scope} only)\n")
    if scope_kept.empty:
        lines.append("No strong or moderate patterns with enough ads.\n")
        continue
    lines.append("| Label | Value | n | ROAS delta | Metrics won | Signal |")
    lines.append("|---|---|---|---|---|---|")
    for _, row in scope_kept.iterrows():
        roas_d = f"{row['roas_delta']:+.3f}" if not np.isnan(row["roas_delta"]) else "n/a"
        lines.append(
            f"| {row['label_col']} | {row['label_val']} | {int(row['n_in_group'])} "
            f"| {roas_d} | {int(row['metrics_better'])} | {row['signal']} |"
        )

lines.append("\n## How to read this table\n")
lines.append("- **ROAS delta**: difference between this group's average ROAS and all other ads.")
lines.append("  Positive = this label type earns more per rupee spent.")
lines.append("- **Metrics won**: how many of the 5 metrics (ROAS, hook_rate, hold_rate, CTR,")
lines.append("  conversion_rate) this group clearly beats the rest on (bootstrap CI above out-group mean).")
lines.append("- **Signal**: strong = 3+ metrics, moderate = 2 metrics, weak = 0-1 metric.")
lines.append("- **n**: number of ads in this group. Patterns with n < 5 are excluded entirely.")
lines.append("\n## Known limits\n")
lines.append("- Patterns are correlational, not causal.")
lines.append("- Ad labels come from an AI system and may contain errors (see data_audit.md section 8).")
lines.append("- Some label groups have small n — treat those findings with extra caution.")
lines.append("- Spend varies widely; the minimum threshold (INR 5,000) filters the noisiest ads")
lines.append("  but does not eliminate all noise.")

md_path = os.path.join(INTER_DIR, "winning_patterns_summary.md")
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Summary written: {md_path}")
