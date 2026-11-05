"""
Step 5: Score, Pick 5, Stress Test
Scores all 20 creators against the winning patterns from Step 3,
applies risk penalties, picks the top 5 with variety, then stress-tests
the selection by varying weights to see how stable the picks are.

Scoring dimensions (weights in CONFIG — visible and justified):
  1. child_on_camera_pct    : strongest signal from Step 3 (child_led, child_presenter)
  2. median_plays_score     : reach — creator must actually be seen
  3. sponsored_experience   : has done brand deals before (lower execution risk)
  4. pattern_score          : overall Step 3 pattern match (0..MAX_PATTERN_SCORE)
  5. reshare_rate_score     : shareability — proxy for content that travels

Risk penalty:
  - Each risk flag subtracts RISK_PENALTY from the final score.
  - Flags with higher severity get a bigger deduction (see RISK_WEIGHTS).

Variety rules (applied after scoring — enforced in pick_top5()):
  - No more than 2 creators with the same persona type
  - At least 1 Hindi/regional-language creator
  - Mix of follower tiers where possible

Stress test tracks TWO stability metrics per creator:
  - raw_top5_rate  : how often a creator lands in the top 5 by score alone
  - final_pick_rate: how often a creator survives the variety rules and is
                     selected in the final 5 (this is what actually matters)
  A creator with high final_pick_rate but low raw_top5_rate is a VARIETY PICK —
  they are selected because of the rules, not purely because of their score.

Run from the repo root:  python src/step5_scoring.py

Outputs:
  intermediate/ranking.csv       all 20 creators with scores and ranks
  intermediate/stability.csv     stress test — raw_top5_rate and final_pick_rate per creator
"""

import os
import sys
import numpy as np
import pandas as pd

# pick_logic lives in the same src/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pick_logic import is_regional, pick_top5  # noqa: E402

# ── config: weights (change here to stress-test manually) ─────────────────────
CONFIG = {
    # --- scoring weights (must sum to 1.0) ---
    "w_child_on_camera":     0.35,   # strongest Step 3 signal: child_led / child_presenter
    "w_median_plays":        0.25,   # reach: creator must be seen to drive sales
    "w_sponsored_exp":       0.15,   # brand deal experience reduces execution risk
    "w_pattern_score":       0.15,   # overall pattern match from Step 3
    "w_reshare_rate":        0.10,   # shareability proxy

    # --- risk penalties (subtracted from final score) ---
    "risk_already_worked":   0.20,   # brand has already worked with them — less new value
    "risk_child_creator":    0.10,   # child managed by parent — extra sensitivity
    "risk_medical":          0.05,   # health claim care needed — manageable, small penalty
    "risk_audience_mismatch":0.15,   # audience not aligned with brand's India target
    "risk_few_posts":        0.10,   # limited data to evaluate
    "risk_missing_plays":    0.05,   # some posts missing plays — data gap
}

# Stress test: vary each weight by +/- this fraction
STRESS_DELTA = 0.10
STRESS_REPS  = 500
RANDOM_SEED  = 42

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INTER_DIR  = os.path.join(BASE, "intermediate")
os.makedirs(INTER_DIR, exist_ok=True)

# ── load ───────────────────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(INTER_DIR, "creator_profiles.csv"))

# ══════════════════════════════════════════════════════════════════════════════
# 1. NORMALISE EACH DIMENSION TO 0–1
#    So different-scale columns can be combined fairly.
# ══════════════════════════════════════════════════════════════════════════════

def min_max(series):
    """Scale a series to 0–1. All-same values → 0.5."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    return (series - mn) / (mx - mn)

# child_on_camera_pct is already 0–1
df["score_child_on_camera"] = df["child_on_camera_pct"]

# median_plays: normalise across all 20 creators
df["score_median_plays"] = min_max(df["median_plays"].fillna(0))

# sponsored experience: cap at 10 posts (diminishing returns above that)
df["score_sponsored_exp"] = min_max(df["n_sponsored_posts"].clip(upper=10))

# pattern_score: 0..MAX_PATTERN_SCORE (set by Step 4 from the number of mapped
# Step 3 patterns — no longer a fixed 4). Normalise by the actual maximum so the
# weighting stays on a 0–1 scale regardless of how many patterns are mapped.
_pattern_max = df["pattern_score"].max()
df["score_pattern"] = df["pattern_score"] / _pattern_max if _pattern_max > 0 else 0.0

# reshare_rate: normalise
df["score_reshare_rate"] = min_max(df["median_reshare_rate"].fillna(0))

# ══════════════════════════════════════════════════════════════════════════════
# 2. RISK PENALTY
# ══════════════════════════════════════════════════════════════════════════════

def compute_risk_penalty(row, cfg):
    penalty = 0.0
    flags   = str(row.get("risk_flags", ""))
    if "already_worked_little_joys"          in flags: penalty += cfg["risk_already_worked"]
    if "child_creator_parent_managed"        in flags: penalty += cfg["risk_child_creator"]
    if "medical_professional_claims_care"    in flags: penalty += cfg["risk_medical"]
    if "audience_mismatch"                   in flags: penalty += cfg["risk_audience_mismatch"]
    if "few_posts"                           in flags: penalty += cfg["risk_few_posts"]
    if "high_missing_plays"                  in flags: penalty += cfg["risk_missing_plays"]
    return round(penalty, 3)

df["risk_penalty"] = df.apply(lambda r: compute_risk_penalty(r, CONFIG), axis=1)

# ══════════════════════════════════════════════════════════════════════════════
# 3. WEIGHTED SCORE
# ══════════════════════════════════════════════════════════════════════════════

def weighted_score(row, cfg):
    """
    Weighted fit score for one creator.

    The score is in the range 0 to 1: the five normalised dimensions are each
    in [0, 1] and the weights sum to 1, so the weighted sum (raw) is at most 1;
    the risk penalty only lowers it. The result is clamped to [0.0, 1.0] as a
    defensive guarantee.

    Risk penalties are FIXED at their CONFIG values and are NOT changed in the
    stress test — only the scoring weights (and the ad threshold) are varied.
    """
    raw = (
        cfg["w_child_on_camera"] * row["score_child_on_camera"] +
        cfg["w_median_plays"]    * row["score_median_plays"]    +
        cfg["w_sponsored_exp"]   * row["score_sponsored_exp"]   +
        cfg["w_pattern_score"]   * row["score_pattern"]         +
        cfg["w_reshare_rate"]    * row["score_reshare_rate"]
    )
    return round(min(1.0, max(0.0, raw - row["risk_penalty"])), 4)

df["fit_score"] = df.apply(lambda r: weighted_score(r, CONFIG), axis=1)
df["rank"]      = df["fit_score"].rank(ascending=False, method="min").astype(int)
df = df.sort_values("rank")

# ══════════════════════════════════════════════════════════════════════════════
# 4. PRINT FULL RANKING
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("FULL RANKING")
print("=" * 80)
show_cols = ["rank", "creator_id", "handle", "followers", "follower_tier",
             "fit_score", "risk_penalty", "child_on_camera_pct",
             "median_plays", "n_sponsored_posts", "pattern_score",
             "dominant_language", "risk_flags"]
print(df[show_cols].to_string(index=False))

# ══════════════════════════════════════════════════════════════════════════════
# 5. SELECTION LOGIC
#    pick_top5(scores, meta) and is_regional(lang) are defined in
#    src/pick_logic.py (imported at the top of this file) so they can be
#    unit-tested without triggering this script's module-level CSV load.
#    See tests/test_pick_top5.py.
#
#    pick_top5 is THE single source of truth for selection — it is used for
#    the main picks AND inside every stress-test iteration. The variety rules
#    (persona cap of 2, at least 1 regional-language creator) live in exactly
#    one place.
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# 6. MAIN PICKS (uses pick_top5 — same function as stress test)
# ══════════════════════════════════════════════════════════════════════════════
meta_cols    = ["creator_id", "persona", "dominant_language"]
pick_ids     = pick_top5(df["fit_score"], df[meta_cols])
picks_df     = df[df["creator_id"].isin(pick_ids)].copy()
# Preserve selection order (pick_top5 returns them highest-score first)
picks_df["_order"] = picks_df["creator_id"].map({cid: i for i, cid in enumerate(pick_ids)})
picks_df     = picks_df.sort_values("_order").drop(columns=["_order"])

runners_up_df = df[~df["creator_id"].isin(pick_ids)].copy()

# Did a variety swap fire? Log it.
raw_top5_ids = df["fit_score"].nlargest(5).index
raw_top5_creator_ids = df.loc[raw_top5_ids, "creator_id"].tolist()
for cid in pick_ids:
    if cid not in raw_top5_creator_ids:
        bumped = [c for c in raw_top5_creator_ids if c not in pick_ids][0]
        bumped_handle = df.loc[df["creator_id"] == bumped, "handle"].values[0]
        swap_handle   = df.loc[df["creator_id"] == cid, "handle"].values[0]
        print(f"\nVariety swap: replaced {bumped_handle} with {swap_handle} "
              f"to include a regional-language creator.")

print("\n" + "=" * 80)
print("TOP 5 PICKS")
print("=" * 80)
pick_display = ["rank", "creator_id", "handle", "followers", "follower_tier",
                "fit_score", "dominant_language", "child_on_camera_pct",
                "median_plays", "n_sponsored_posts", "risk_flags"]
print(picks_df[pick_display].to_string(index=False))

print("\n" + "=" * 80)
print("RUNNERS-UP (next 5)")
print("=" * 80)
print(runners_up_df.head(5)[pick_display].to_string(index=False))

# ══════════════════════════════════════════════════════════════════════════════
# 7. STRESS TEST
#    Randomly vary all weights within +/- STRESS_DELTA, with a fixed seed so
#    results are reproducible.
#
#    For each weight variation we record TWO things per creator:
#      raw_top5_count   — how many times they appear in the top 5 by score alone
#      final_pick_count — how many times they appear in the final 5 after the
#                         variety rules are applied via pick_top5()
#
#    raw_top5_rate  = raw_top5_count  / STRESS_REPS * 100
#    final_pick_rate = final_pick_count / STRESS_REPS * 100
#
#    A creator with high final_pick_rate but low raw_top5_rate is a VARIETY
#    PICK: they survive the rules more often than they score into the top 5 on
#    their own. A creator with high raw_top5_rate and high final_pick_rate is
#    a SCORE PICK: the rules do not change their inclusion.
# ══════════════════════════════════════════════════════════════════════════════
print("\nRunning stress test...")
rng = np.random.default_rng(RANDOM_SEED)

raw_top5_count   = {cid: 0 for cid in df["creator_id"]}
final_pick_count = {cid: 0 for cid in df["creator_id"]}

weight_keys = ["w_child_on_camera", "w_median_plays", "w_sponsored_exp",
               "w_pattern_score", "w_reshare_rate"]

for _ in range(STRESS_REPS):
    # perturb weights randomly
    cfg = CONFIG.copy()
    raw_weights = {k: max(0.01, cfg[k] + rng.uniform(-STRESS_DELTA, STRESS_DELTA))
                   for k in weight_keys}
    total = sum(raw_weights.values())
    # renormalise so weights still sum to 1
    for k in weight_keys:
        cfg[k] = raw_weights[k] / total

    # recompute scores for this weight variation
    stress_scores = df.apply(lambda r: weighted_score(r, cfg), axis=1)

    # raw top-5 by score alone (no variety rules)
    raw_ids = df.loc[stress_scores.nlargest(5).index, "creator_id"].tolist()
    for cid in raw_ids:
        raw_top5_count[cid] += 1

    # final picks with variety rules applied — uses the same pick_top5 function
    final_ids = pick_top5(stress_scores, df[meta_cols])
    for cid in final_ids:
        final_pick_count[cid] += 1

# ── build stability table ─────────────────────────────────────────────────────
stability_rows = []
for cid in df["creator_id"]:
    handle = df.loc[df["creator_id"] == cid, "handle"].values[0]
    raw_cnt   = raw_top5_count[cid]
    final_cnt = final_pick_count[cid]
    stability_rows.append({
        "creator_id":      cid,
        "handle":          handle,
        "raw_top5_count":  raw_cnt,
        "final_pick_count":final_cnt,
        "raw_top5_rate":   round(raw_cnt   / STRESS_REPS * 100, 1),
        "final_pick_rate": round(final_cnt / STRESS_REPS * 100, 1),
    })

stability = (pd.DataFrame(stability_rows)
             .sort_values("final_pick_count", ascending=False)
             .reset_index(drop=True))

stability["is_our_pick"] = stability["creator_id"].isin(pick_ids)

# label each creator as score pick, variety pick, or not picked
def pick_type(row):
    if not row["is_our_pick"]:
        return "not_picked"
    # variety pick: final_pick_rate is notably higher than raw_top5_rate
    # (the rules are doing meaningful work for this creator)
    if row["final_pick_rate"] > row["raw_top5_rate"] + 5:
        return "variety_pick"
    return "score_pick"

stability["pick_type"] = stability.apply(pick_type, axis=1)

print("\nStress test results (out of", STRESS_REPS, "weight variations):")
print(stability.to_string(index=False))

# ══════════════════════════════════════════════════════════════════════════════
# 8. CONFIDENCE LEVEL PER PICK
#    Based on final_pick_rate (the variety-adjusted metric), not raw_top5_rate.
# ══════════════════════════════════════════════════════════════════════════════
def confidence(final_pick_rate, risk_flags):
    if final_pick_rate >= 80 and risk_flags == "none":
        return "high"
    if final_pick_rate >= 50:
        return "medium"
    return "low"

picks_df = picks_df.merge(
    stability[["creator_id", "raw_top5_rate", "final_pick_rate", "pick_type"]],
    on="creator_id", how="left")
picks_df["confidence"] = picks_df.apply(
    lambda r: confidence(r["final_pick_rate"], str(r["risk_flags"])), axis=1)

print("\n" + "=" * 80)
print("FINAL 5 WITH CONFIDENCE")
print("=" * 80)
print(picks_df[["rank", "creator_id", "handle", "fit_score",
                "raw_top5_rate", "final_pick_rate", "pick_type",
                "confidence", "risk_flags"]].to_string(index=False))

# ── explain variety picks in the report ──────────────────────────────────────
print("\n" + "=" * 80)
print("STABILITY EXPLANATION")
print("=" * 80)
print(
    "raw_top5_rate  = % of 500 weight variations where this creator is in the\n"
    "                 top 5 by score alone, before variety rules are applied.\n"
    "final_pick_rate = % of 500 variations where this creator appears in the\n"
    "                 final 5 AFTER variety rules (persona cap + regional\n"
    "                 language requirement). This is what actually matters.\n"
    "\n"
    "The stress test varies the scoring weights. The ad spend threshold and the\n"
    "risk penalties are held fixed.\n"
)
for _, row in picks_df.iterrows():
    if row["pick_type"] == "variety_pick":
        print(
            f"  {row['handle']} ({row['creator_id']}) is a VARIETY PICK.\n"
            f"  raw_top5_rate={row['raw_top5_rate']}%  final_pick_rate={row['final_pick_rate']}%\n"
            f"  They are selected more often after the rules than their score alone\n"
            f"  would suggest. Their inclusion reflects the diversity requirement,\n"
            f"  not score dominance. Treat their confidence as pick_type=variety_pick.\n"
        )
    else:
        print(
            f"  {row['handle']} ({row['creator_id']}) is a SCORE PICK.\n"
            f"  raw_top5_rate={row['raw_top5_rate']}%  final_pick_rate={row['final_pick_rate']}%\n"
            f"  The variety rules do not materially change their inclusion.\n"
        )

# ══════════════════════════════════════════════════════════════════════════════
# 9. SAVE
# ══════════════════════════════════════════════════════════════════════════════

# full ranking — attach final_pick_rate for downstream use in step6
df_out = df.merge(
    stability[["creator_id", "raw_top5_rate", "final_pick_rate", "pick_type"]],
    on="creator_id", how="left")
df_out["is_pick"] = df_out["creator_id"].isin(pick_ids)
df_out.to_csv(os.path.join(INTER_DIR, "ranking.csv"), index=False)

# stability — both metrics
stability.to_csv(os.path.join(INTER_DIR, "stability.csv"), index=False)

print(f"\nSaved: intermediate/ranking.csv  ({len(df_out)} rows)")
print(f"Saved: intermediate/stability.csv  ({len(stability)} rows)")

# ── weight summary ────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("WEIGHT SUMMARY (justify these in your interview)")
print("=" * 80)
print(f"  child_on_camera  : {CONFIG['w_child_on_camera']:.0%}  "
      "— strongest Step 3 signal (child_led ROAS +1.02)")
print(f"  median_plays     : {CONFIG['w_median_plays']:.0%}  "
      "— creator must have reach to drive conversions")
print(f"  sponsored_exp    : {CONFIG['w_sponsored_exp']:.0%}  "
      "— reduces execution risk; experienced creators deliver on brief")
print(f"  pattern_score    : {CONFIG['w_pattern_score']:.0%}  "
      "— overall fit with all Step 3 winning patterns")
print(f"  reshare_rate     : {CONFIG['w_reshare_rate']:.0%}  "
      "— shareability amplifies organic reach beyond paid")
