"""
Step 2: Ad Metrics
Computes per-ad performance rates from raw spend/impression/purchase columns.

Metrics calculated:
  roas              = revenue_inr / spend_inr
  cost_per_purchase = spend_inr / purchases
  hook_rate         = video_3s_views / impressions
  hold_rate         = thruplays / video_3s_views
  ctr               = link_clicks / impressions
  conversion_rate   = purchases / link_clicks

Rules:
  - Any division where the denominator is 0 gives NaN (not an error).
  - Ads below MIN_SPEND_INR are kept in the file but flagged as low_spend=True.
    They are excluded from pattern analysis in Step 3.

Run from the repo root:  python src/step2_ad_metrics.py

Output:  intermediate/ad_metrics.csv
"""

import os
import pandas as pd
import numpy as np

# ── config ─────────────────────────────────────────────────────────────────────
# Minimum spend to be included in pattern analysis.
# Rationale: 10th percentile of spend is ~₹5,053 (from Step 1 audit).
# Ads below this threshold have too few events to give stable rates.
MIN_SPEND_INR = 5_000

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_DIR   = os.path.join(BASE, "data")
INTER_DIR  = os.path.join(BASE, "intermediate")
os.makedirs(INTER_DIR, exist_ok=True)

# ── load ───────────────────────────────────────────────────────────────────────
ads = pd.read_csv(os.path.join(DATA_DIR, "ads.csv"))

# ── safe division helper ───────────────────────────────────────────────────────
def safe_div(numerator, denominator):
    """Divide two series. Returns NaN wherever denominator is 0 or NaN."""
    return numerator / denominator.replace(0, np.nan)

# ── compute metrics ────────────────────────────────────────────────────────────

# ROAS: how many rupees of revenue did we get per rupee spent?
# e.g. 2.5 means ₹2.50 back for every ₹1 spent
ads["roas"] = safe_div(ads["revenue_inr"], ads["spend_inr"]).round(4)

# Cost per purchase: how much did we spend to get one purchase?
# Undefined (NaN) when purchases = 0
ads["cost_per_purchase"] = safe_div(ads["spend_inr"], ads["purchases"]).round(2)

# Hook rate: of everyone who saw the ad, how many watched at least 3 seconds?
# Measures how well the opening grabs attention
ads["hook_rate"] = safe_div(ads["video_3s_views"], ads["impressions"]).round(4)

# Hold rate: of people who watched 3s, how many watched all the way through?
# Measures how well the rest of the video holds attention
ads["hold_rate"] = safe_div(ads["thruplays"], ads["video_3s_views"]).round(4)

# CTR: of everyone who saw the ad, how many clicked the link?
ads["ctr"] = safe_div(ads["link_clicks"], ads["impressions"]).round(6)

# Conversion rate: of people who clicked, how many actually bought?
# Undefined (NaN) when link_clicks = 0
ads["conversion_rate"] = safe_div(ads["purchases"], ads["link_clicks"]).round(4)

# ── low spend flag ─────────────────────────────────────────────────────────────
# These ads are NOT removed — just flagged so Step 3 can exclude them
ads["low_spend"] = ads["spend_inr"] < MIN_SPEND_INR

# ── quick sanity check ─────────────────────────────────────────────────────────
# Print a few ads by hand so you can verify the numbers are right
print("=" * 60)
print("SANITY CHECK — verify 3 ads by hand")
print("=" * 60)
check_cols = ["ad_id", "spend_inr", "revenue_inr", "roas",
              "purchases", "cost_per_purchase",
              "impressions", "video_3s_views", "hook_rate",
              "thruplays", "hold_rate",
              "link_clicks", "ctr", "conversion_rate", "low_spend"]
print(ads[check_cols].head(3).to_string(index=False))
print()

# ── summary stats ──────────────────────────────────────────────────────────────
metric_cols = ["roas", "cost_per_purchase", "hook_rate", "hold_rate", "ctr", "conversion_rate"]
above_threshold = ads[~ads["low_spend"]]

print(f"Total ads: {len(ads)}")
print(f"Low spend (< INR {MIN_SPEND_INR:,}): {ads['low_spend'].sum()}")
print(f"Ads above threshold (used in Step 3): {len(above_threshold)}")
print(f"Ads with zero purchases (ROAS and cost_per_purchase = NaN): {(ads['purchases'] == 0).sum()}")
print()
print("Metric summary (ads above spend threshold):")
print(above_threshold[metric_cols].describe().round(4).to_string())
print()

# ── save ───────────────────────────────────────────────────────────────────────
out_path = os.path.join(INTER_DIR, "ad_metrics.csv")
ads.to_csv(out_path, index=False)
print(f"Saved to {out_path}  ({len(ads)} rows, {len(ads.columns)} columns)")

