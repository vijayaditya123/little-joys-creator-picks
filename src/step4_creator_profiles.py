"""
Step 4: Creator Profiles
Builds a scored profile for each of the 20 creators from their posts,
the creators.csv metadata, and the audience file (3 creators only).

What we compute per creator:
  - engagement_per_play   : (reshares) / plays  (likes excluded — hidden for some)
  - median_plays          : typical reach per post
  - sponsored_vs_organic  : do sponsored posts get more or fewer plays?
  - child_on_camera_pct   : % of posts with children on camera
  - language mix          : most common language
  - dominant tone         : most common tone
  - dominant format       : most common content_form
  - production_quality    : median production score (1–5)
  - pattern_match_score   : how well creator matches Step 3 winning patterns.
                            Driven by intermediate/winning_patterns.csv via
                            PATTERN_MAP; range is 0..MAX_PATTERN_SCORE (the
                            number of mapped kept patterns, not a fixed 4).

Risk flags (from the brief):
  - already_worked_little_joys  : CR-20 per audience file
  - child_creator               : CR-05, CR-20 (child managed by parent)
  - medical_professional        : extra care with health claims
  - audience_mismatch           : CR-14 audience mostly outside India target
  - few_posts                   : CR-18 has only 12 posts
  - missing_plays               : creators with many posts missing plays data

Run from the repo root:  python src/step4_creator_profiles.py

Output: intermediate/creator_profiles.csv
"""

import os
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_DIR   = os.path.join(BASE, "data")
INTER_DIR  = os.path.join(BASE, "intermediate")
os.makedirs(INTER_DIR, exist_ok=True)

# ── load ───────────────────────────────────────────────────────────────────────
creators = pd.read_csv(os.path.join(DATA_DIR, "creators.csv"))
posts    = pd.read_csv(os.path.join(DATA_DIR, "creator_posts.csv"))
audience = pd.read_csv(os.path.join(DATA_DIR, "creator_audience.csv"))


# ══════════════════════════════════════════════════════════════════════════════
# PATTERN -> CREATOR-SIDE MAPPING
# Connects each Step 3 pattern (label_col=label_val) to a creator-side check.
# Only patterns listed here can contribute to pattern_score. A kept Step 3
# pattern with NO entry here is NOT scored silently — it triggers a warning.
#
# Each value is (human_label, check_fn). check_fn(ctx) -> bool, where ctx is a
# dict of per-creator signals assembled in the loop below.
#
# Why only these: creator post data (creator_posts.csv) reliably shows WHO is on
# camera and WHAT LANGUAGE is used. It does NOT reliably show ad-copy mechanics
# such as CTA wording, how soon the brand is named, proof type, hook type or
# persuasion style — those are ad-creative choices, not observable creator
# habits — so those Step 3 patterns are intentionally left unmapped and warned
# about rather than guessed at.
# ══════════════════════════════════════════════════════════════════════════════
PATTERN_MAP = {
    # child on camera: the creator frequently films children (>= 40% of posts).
    # The child_led, child_presenter and all child_role patterns are the SAME
    # observable creator signal (creator_posts labels do not break out the
    # specific child role), so they share ONE human_label and count ONCE.
    ("ad_format", "child_led"):            ("children on camera (>= 40% of posts)",
                                            lambda c: c["child_pct"] >= 0.4),
    ("creator_type", "child_presenter"):   ("children on camera (>= 40% of posts)",
                                            lambda c: c["child_pct"] >= 0.4),
    ("child_role", "reacts_to_taste"):     ("children on camera (>= 40% of posts)",
                                            lambda c: c["child_pct"] >= 0.4),
    ("child_role", "speaks"):              ("children on camera (>= 40% of posts)",
                                            lambda c: c["child_pct"] >= 0.4),
    ("child_role", "consumes_product"):    ("children on camera (>= 40% of posts)",
                                            lambda c: c["child_pct"] >= 0.4),
    # regional language: creator posts in Hindi/Hinglish or an Indian regional
    # language, matching the brand's market. A genuinely separate signal.
    ("language", "hindi"):                 ("feed uses Hindi/regional language",
                                            lambda c: c["regional"]),
}

# ══════════════════════════════════════════════════════════════════════════════
# LOAD KEPT STEP 3 PATTERNS (no silent fallback)
# pattern_score is driven entirely by winning_patterns.csv. If the file is
# missing we STOP — we do not fall back to hard-coded signals.
# ══════════════════════════════════════════════════════════════════════════════
WINNING_PATTERNS_PATH = os.path.join(INTER_DIR, "winning_patterns.csv")
if not os.path.exists(WINNING_PATTERNS_PATH):
    raise SystemExit(
        f"ERROR: {WINNING_PATTERNS_PATH} not found.\n"
        "pattern_score is built from Step 3's winning patterns. "
        "Run Step 3 first:\n"
        "    python src/step3_winning_patterns.py"
    )

_wp = pd.read_csv(WINNING_PATTERNS_PATH)

# A pattern is "kept" if its signal is not weak_signal (i.e. strong or moderate).
_kept = _wp[_wp["signal"] != "weak_signal"]
# Unique (label_col, label_val) pairs that survived across any scope.
KEPT_PATTERNS = sorted(set(zip(_kept["label_col"], _kept["label_val"])))

# Which kept patterns have a creator-side mapping (these are the ones scored)?
SCORED_PATTERNS = [p for p in KEPT_PATTERNS if p in PATTERN_MAP]
UNMAPPED_KEPT   = [p for p in KEPT_PATTERNS if p not in PATTERN_MAP]

# Max score is the number of DISTINCT human-labels among scored patterns, so
# three child-on-camera patterns that share one check do not count three times.
_scored_checks = {PATTERN_MAP[p][0] for p in SCORED_PATTERNS}
MAX_PATTERN_SCORE = len(_scored_checks)

print("=" * 70)
print("PATTERN_SCORE SETUP (from Step 3 winning_patterns.csv)")
print("=" * 70)
print(f"Kept Step 3 patterns (strong/moderate): {len(KEPT_PATTERNS)}")
print(f"Of these, mapped to a creator-side check: {len(SCORED_PATTERNS)}")
print(f"Distinct checks (MAX_PATTERN_SCORE): {MAX_PATTERN_SCORE}")
print()

# Warn — loudly — about any kept pattern with no mapping.
for label_col, label_val in UNMAPPED_KEPT:
    print(f"WARNING: Pattern {label_col}={label_val} is kept in Step 3 but has no "
          f"creator-side mapping, so it is not in pattern_score.")
print()


# ══════════════════════════════════════════════════════════════════════════════
# 1. POST-LEVEL METRICS PER CREATOR
# ══════════════════════════════════════════════════════════════════════════════

profiles = []

for creator_id, grp in posts.groupby("creator_id"):

    n_posts       = len(grp)
    posts_w_plays = grp[grp["plays"].notna()]
    n_with_plays  = len(posts_w_plays)

    # ── reach ─────────────────────────────────────────────────────────────────
    median_plays = posts_w_plays["plays"].median() if n_with_plays > 0 else np.nan
    mean_plays   = posts_w_plays["plays"].mean()   if n_with_plays > 0 else np.nan

    # ── engagement per play (reshares only — likes excluded) ──────────────────
    # Only compute for posts that have plays > 0
    valid = posts_w_plays[posts_w_plays["plays"] > 0].copy()
    if len(valid) > 0:
        valid["reshare_rate"] = valid["reshares"] / valid["plays"]
        median_reshare_rate = valid["reshare_rate"].median()
    else:
        median_reshare_rate = np.nan

    # ── sponsored vs organic plays ────────────────────────────────────────────
    sponsored = posts_w_plays[posts_w_plays["is_sponsored"] == "yes"]
    organic   = posts_w_plays[posts_w_plays["is_sponsored"] == "no"]
    median_plays_sponsored = sponsored["plays"].median() if len(sponsored) > 0 else np.nan
    median_plays_organic   = organic["plays"].median()   if len(organic)   > 0 else np.nan
    n_sponsored            = len(sponsored)

    # ── children on camera ────────────────────────────────────────────────────
    child_posts    = grp[grp["children_on_camera"] == "yes"]
    child_pct      = len(child_posts) / n_posts if n_posts > 0 else 0

    # ── language ──────────────────────────────────────────────────────────────
    dominant_language = (grp["language"].dropna()
                         .value_counts().idxmax()
                         if grp["language"].notna().any() else "unknown")
    languages_used = "; ".join(
        grp["language"].dropna().value_counts().index.tolist()[:3])

    # ── tone ──────────────────────────────────────────────────────────────────
    # tone is free-text so we look for key words
    all_tones = grp["tone"].dropna().str.lower().str.cat(sep=" ")
    tone_playful      = int("playful"      in all_tones)
    tone_educational  = int("educational"  in all_tones or "informative" in all_tones)
    tone_emotional    = int("emotional"    in all_tones or "warm"        in all_tones)
    tone_clinical     = int("clinical"     in all_tones or "professional" in all_tones)

    # ── content format ────────────────────────────────────────────────────────
    dominant_format = (grp["content_form"].dropna()
                       .value_counts().idxmax()
                       if grp["content_form"].notna().any() else "unknown")

    # ── production quality ────────────────────────────────────────────────────
    median_production = grp["production_quality_1to5"].median()

    # ── transcript coverage ───────────────────────────────────────────────────
    has_t = grp["transcript"].notna() & (grp["transcript"].astype(str).str.strip() != "")
    n_transcripts = has_t.sum()

    # ── pattern match score ───────────────────────────────────────────────────
    # Driven by Step 3's kept patterns (winning_patterns.csv) via PATTERN_MAP.
    # Each DISTINCT creator-side check that a kept+mapped pattern points to adds
    # 1 point. Max = MAX_PATTERN_SCORE (computed from the file, not fixed at 4).
    lang_lower = languages_used.lower()
    regional = any(lang in lang_lower for lang in
                   ["hindi", "hinglish", "tamil", "malayalam", "kannada", "punjabi"])

    # per-creator signals the check_fns read
    ctx = {
        "child_pct": child_pct,
        "regional":  regional,
    }

    # Evaluate each DISTINCT check once; a check passes if any scored pattern
    # that maps to it passes. (Multiple child patterns share one check.)
    pattern_score = 0
    pattern_notes = []
    _checks_done = {}   # human_label -> bool, so shared checks count once
    for p in SCORED_PATTERNS:
        human_label, check_fn = PATTERN_MAP[p]
        if human_label in _checks_done:
            continue
        passed = bool(check_fn(ctx))
        _checks_done[human_label] = passed
        if passed:
            pattern_score += 1
            pattern_notes.append(human_label)

    pattern_match = "; ".join(pattern_notes) if pattern_notes else "none"

    profiles.append({
        "creator_id":               creator_id,
        "n_posts":                  n_posts,
        "n_posts_with_plays":       n_with_plays,
        "median_plays":             round(median_plays, 0) if not np.isnan(median_plays) else np.nan,
        "mean_plays":               round(mean_plays, 0)   if not np.isnan(mean_plays)   else np.nan,
        "median_reshare_rate":      round(median_reshare_rate, 5) if not np.isnan(median_reshare_rate) else np.nan,
        "n_sponsored_posts":        n_sponsored,
        "median_plays_sponsored":   round(median_plays_sponsored, 0) if not np.isnan(median_plays_sponsored) else np.nan,
        "median_plays_organic":     round(median_plays_organic, 0)   if not np.isnan(median_plays_organic)   else np.nan,
        "child_on_camera_pct":      round(child_pct, 3),
        "dominant_language":        dominant_language,
        "languages_used":           languages_used,
        "tone_playful":             tone_playful,
        "tone_educational":         tone_educational,
        "tone_emotional":           tone_emotional,
        "tone_clinical":            tone_clinical,
        "dominant_format":          dominant_format,
        "median_production_quality":median_production,
        "n_transcripts":            int(n_transcripts),
        "pattern_score":            pattern_score,
        "pattern_score_max":        MAX_PATTERN_SCORE,
        "pattern_match_notes":      pattern_match,
    })

profile_df = pd.DataFrame(profiles)

# ══════════════════════════════════════════════════════════════════════════════
# 2. MERGE CREATOR METADATA
# ══════════════════════════════════════════════════════════════════════════════
meta_cols = ["creator_id", "handle", "name", "followers", "verified",
             "persona", "language_use", "what_feels_native",
             "what_would_feel_foreign", "audience_read"]
profile_df = profile_df.merge(creators[meta_cols], on="creator_id", how="left")

# ══════════════════════════════════════════════════════════════════════════════
# 3. MERGE AUDIENCE DATA (only 3 creators)
# ══════════════════════════════════════════════════════════════════════════════
aud_cols = ["creator_id", "platform", "women_pct", "men_pct",
            "age_split", "top_countries", "brands_in_past_year"]
profile_df = profile_df.merge(audience[aud_cols], on="creator_id", how="left")
profile_df["has_audience_data"] = profile_df["platform"].notna()

# ══════════════════════════════════════════════════════════════════════════════
# 4. RISK FLAGS
# ══════════════════════════════════════════════════════════════════════════════

def risk_flags(row):
    flags = []

    # Already worked with Little Joys
    brands = str(row.get("brands_in_past_year", "")).lower()
    if "little joys" in brands:
        flags.append("already_worked_little_joys")

    # Child creator managed by parent
    if row["creator_id"] in ["CR-05", "CR-20"]:
        flags.append("child_creator_parent_managed")

    # Medical professional — health claims need extra care
    if str(row.get("persona", "")).lower() in [
            "clinical pediatric authority", "medical_professional"]:
        flags.append("medical_professional_claims_care")

    # Audience mismatch — CR-14 has 64% India but significant Pakistan/Bangladesh
    # audience that may not be the brand's target
    countries = str(row.get("top_countries", ""))
    if row["creator_id"] == "CR-14":
        flags.append("audience_mismatch_cr14_cross_border")

    # Platform mismatch — CR-14 audience data is from Facebook, profile is Instagram
    if row["creator_id"] == "CR-14":
        flags.append("platform_mismatch_audience_vs_profile")

    # Few posts
    if row["n_posts"] < 15:
        flags.append("few_posts_limited_data")

    # Many posts missing plays
    missing_plays_pct = 1 - (row["n_posts_with_plays"] / row["n_posts"]) if row["n_posts"] > 0 else 1
    if missing_plays_pct > 0.3:
        flags.append("high_missing_plays")

    return "; ".join(flags) if flags else "none"

profile_df["risk_flags"] = profile_df.apply(risk_flags, axis=1)

# ══════════════════════════════════════════════════════════════════════════════
# 5. TIER BY FOLLOWERS
# ══════════════════════════════════════════════════════════════════════════════
def follower_tier(n):
    if n >= 500_000:   return "mega (500k+)"
    if n >= 100_000:   return "macro (100k-500k)"
    if n >= 10_000:    return "mid (10k-100k)"
    return "micro (<10k)"

profile_df["follower_tier"] = profile_df["followers"].apply(follower_tier)

# ══════════════════════════════════════════════════════════════════════════════
# 6. SAVE
# ══════════════════════════════════════════════════════════════════════════════
out_path = os.path.join(INTER_DIR, "creator_profiles.csv")
profile_df.to_csv(out_path, index=False)
print(f"Saved: {out_path}  ({len(profile_df)} creators, {len(profile_df.columns)} columns)")

# ── print summary table ───────────────────────────────────────────────────────
summary_cols = ["creator_id", "handle", "followers", "follower_tier",
                "median_plays", "child_on_camera_pct", "n_sponsored_posts",
                "dominant_language", "pattern_score", "risk_flags"]
print("\nCreator profiles summary:")
print(profile_df[summary_cols].sort_values("pattern_score", ascending=False).to_string(index=False))
