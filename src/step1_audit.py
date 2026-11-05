"""
Step 1: Data Audit
Checks shapes, types, missing values, duplicates, distributions,
hidden likes, missing plays, transcript coverage, cross-file mismatches,
and a manual label check.

Run from the repo root:  python src/step1_audit.py

Outputs:
  intermediate/data_audit.md        the audit report
  intermediate/label_check.csv      15 ads to review by hand (fill in 'reviewed' and 'error_noted')

Re-run after filling label_check.csv: the report then shows the real error rate.
"""

import os
import pandas as pd

# ── settings ───────────────────────────────────────────────────────────────────
HIDDEN_LIKES_MAX = 5      # likes <= this are treated as hidden (the data shows hidden likes as exactly 3)
LABEL_SAMPLE_N   = 15
LABEL_COLS       = ["hook_type", "child_on_screen", "brand_first_said"]  # labels you check by hand

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_DIR   = os.path.join(BASE, "data")
INTER_DIR  = os.path.join(BASE, "intermediate")
os.makedirs(INTER_DIR, exist_ok=True)

# ── load data ─────────────────────────────────────────────────────────────────
ads      = pd.read_csv(os.path.join(DATA_DIR, "ads.csv"))
creators = pd.read_csv(os.path.join(DATA_DIR, "creators.csv"))
posts    = pd.read_csv(os.path.join(DATA_DIR, "creator_posts.csv"))
audience = pd.read_csv(os.path.join(DATA_DIR, "creator_audience.csv"))

# ── helpers to build the markdown report ──────────────────────────────────────
lines = []

def h(text):
    lines.append(f"\n## {text}\n")

def h3(text):
    lines.append(f"\n### {text}\n")

def p(text=""):
    lines.append(text)

def table(df, max_rows=30, index=False):
    lines.append(df.head(max_rows).to_markdown(index=index))
    p()

frames = [("ads", ads), ("creators", creators), ("posts", posts), ("audience", audience)]

# ══════════════════════════════════════════════════════════════════════════════
# 1. SHAPES
# How many rows and columns does each file have?
# ══════════════════════════════════════════════════════════════════════════════
h("1. Shapes")
for name, df in frames:
    p(f"**{name}**: {df.shape[0]} rows x {df.shape[1]} columns  ")

# ══════════════════════════════════════════════════════════════════════════════
# 2. COLUMN TYPES
# Is each column the right data type? (e.g. dates as strings, numbers as objects?)
# ══════════════════════════════════════════════════════════════════════════════
h("2. Column types")
for name, df in frames:
    h3(name)
    t = df.dtypes.astype(str).reset_index()
    t.columns = ["column", "dtype"]
    table(t, max_rows=len(t))

# ══════════════════════════════════════════════════════════════════════════════
# 3. MISSING VALUES
# Which columns have blanks, and how many?
# ══════════════════════════════════════════════════════════════════════════════
h("3. Missing values")
for name, df in frames:
    h3(name)
    miss = df.isnull().sum()
    miss = miss[miss > 0].reset_index()
    if miss.empty:
        p("No missing values.")
    else:
        miss.columns = ["column", "missing_count"]
        miss["missing_pct"] = (miss["missing_count"] / len(df) * 100).round(1)
        table(miss, max_rows=len(miss))

# ══════════════════════════════════════════════════════════════════════════════
# 4. DUPLICATES
# Are there any rows or IDs that appear more than once?
# ══════════════════════════════════════════════════════════════════════════════
h("4. Duplicates")
p(f"ads duplicate rows: {ads.duplicated().sum()}  ")
p(f"ads duplicate ad_id: {ads['ad_id'].duplicated().sum()}  ")
p(f"creators duplicate rows: {creators.duplicated().sum()}  ")
p(f"creators duplicate creator_id: {creators['creator_id'].duplicated().sum()}  ")
p(f"posts duplicate rows: {posts.duplicated().sum()}  ")
p(f"audience duplicate rows: {audience.duplicated().sum()}  ")

# ══════════════════════════════════════════════════════════════════════════════
# 5. ADS: SPEND, IMPRESSIONS, DAYS_LIVE
# Get the range and spread of key performance numbers.
# Also flag zero-spend ads (useless for ROAS) and zero-purchase ads.
# ══════════════════════════════════════════════════════════════════════════════
h("5. Ads: spend, impressions, days_live")
perf_cols = ["spend_inr", "impressions", "days_live", "video_3s_views", "thruplays",
             "link_clicks", "add_to_carts", "purchases", "revenue_inr"]
perf_cols = [c for c in perf_cols if c in ads.columns]
table(ads[perf_cols].describe().round(2), index=True)

h3("Ads with zero or missing spend")
zero_spend = ads[ads["spend_inr"].fillna(0) == 0]
p(f"Count: {len(zero_spend)}")

h3("Ads with zero purchases")
zero_purch = ads[ads["purchases"].fillna(0) == 0]
p(f"Count: {len(zero_purch)} of {len(ads)}. Cost per purchase is undefined for these (handle in Step 2).")
if not zero_purch.empty:
    table(zero_purch[["ad_id", "spend_inr", "impressions", "link_clicks", "purchases"]])

h3("Spend percentiles (INR)")
p(ads["spend_inr"].quantile([0.1, 0.25, 0.5, 0.75, 0.9, 0.95]).round(2).to_string())
p()
p(f"Smallest spend: {ads['spend_inr'].min():,}  |  largest spend: {ads['spend_inr'].max():,}. "
  "Tiny-spend ads give noisy rates, so Step 2 needs a minimum-spend threshold.")

# ══════════════════════════════════════════════════════════════════════════════
# 6. CREATOR POSTS
# Posts per creator, hidden likes, missing plays, transcript coverage, comments.
# ══════════════════════════════════════════════════════════════════════════════
h("6. Creator posts")

# -- posts per creator ---------------------------------------------------------
h3("Posts per creator")
ppc = posts.groupby("creator_id").size().reset_index(name="post_count").sort_values("post_count")
table(ppc, max_rows=len(ppc))

# -- hidden likes --------------------------------------------------------------
h3(f"Hidden likes (likes <= {HIDDEN_LIKES_MAX})")
p("Hidden like counts show up as a tiny number (exactly 3 in this data), not as 0. "
  "A check for `likes == 0` would find nothing.")
p()
hidden = posts[posts["likes"] <= HIDDEN_LIKES_MAX]
p(f"Posts with hidden likes: {len(hidden)} of {len(posts)} ({len(hidden) / len(posts) * 100:.1f}%)")
p(f"Observed hidden values: {sorted(hidden['likes'].unique().tolist())}")
p()
if not hidden.empty:
    by_c = (hidden.groupby("creator_id")
            .agg(hidden_like_posts=("likes", "size"), max_plays_among_them=("plays", "max"))
            .reset_index())
    table(by_c, max_rows=len(by_c))
p("**Consequence:** do not use likes to compare creators. Use plays-based measures and treat "
  "likes on these posts as missing.")

# -- missing plays -------------------------------------------------------------
h3("Missing plays")
no_plays = posts[posts["plays"].isna()]
p(f"Posts with no plays value: {len(no_plays)} of {len(posts)}. "
  "Engagement per play cannot be computed for them.")
npc = no_plays.groupby("creator_id").size().reset_index(name="posts_missing_plays")
if not npc.empty:
    table(npc, max_rows=len(npc))

# -- transcript coverage -------------------------------------------------------
h3("Transcript coverage in posts")
has_t = posts["transcript"].notna() & (posts["transcript"].astype(str).str.strip() != "")
p(f"Posts with a transcript: {has_t.sum()} of {len(posts)} ({has_t.sum() / len(posts) * 100:.1f}%)")
tc = has_t.groupby(posts["creator_id"]).sum().reset_index(name="transcripts_count")
table(tc, max_rows=len(tc))

# -- comments ------------------------------------------------------------------
h3("Comments")
zc = (posts["comments"].fillna(0) == 0).sum()
p(f"Posts with zero or missing comments: {zc} of {len(posts)}. "
  "Comment-based fields in creators.csv (sentiment, who_replies) are empty for every creator "
  "('inert' / 'none'), so comments cannot be used for ranking.")

# ══════════════════════════════════════════════════════════════════════════════
# 7. CROSS-FILE CHECKS
# Do the same creator IDs appear across all three files?
# Does the platform in the audience file match the profile URL in creators.csv?
# ══════════════════════════════════════════════════════════════════════════════
h("7. Cross-file checks")
ids_main  = set(creators["creator_id"])
ids_posts = set(posts["creator_id"])
ids_aud   = set(audience["creator_id"])

p(f"creators.csv IDs: {len(ids_main)}  |  creator_posts.csv IDs: {len(ids_posts)}  |  "
  f"creator_audience.csv IDs: {len(ids_aud)}")
p()
p(f"In posts but not in creators.csv: {sorted(ids_posts - ids_main) or 'none'}  ")
p(f"In creators.csv but not in posts: {sorted(ids_main - ids_posts) or 'none'}  ")
p(f"In audience but not in creators.csv: {sorted(ids_aud - ids_main) or 'none'}  ")
p(f"Creators WITHOUT audience data: {len(ids_main - ids_aud)} of {len(ids_main)}  ")

h3("Platform check (creators.csv vs creator_audience.csv)")
merged = audience[["creator_id", "handle", "platform"]].merge(
    creators[["creator_id", "handle", "profile_url"]], on="creator_id", suffixes=("_audience", "_creators"))
merged["platform_in_profile_url"] = merged["profile_url"].str.extract(r"https?://(?:www\.)?([a-z]+)\.")
merged["match"] = merged["platform"].str.lower() == merged["platform_in_profile_url"].str.lower()
table(merged[["creator_id", "handle_audience", "handle_creators", "platform",
              "platform_in_profile_url", "match"]])
p("Rows with match = False are open questions to resolve or flag.")

h3("Past brand partners (from creator_audience.csv)")
brands = audience[["creator_id", "brands_in_past_year"]].fillna("none listed")
table(brands)

# ══════════════════════════════════════════════════════════════════════════════
# 8. MANUAL LABEL CHECK
# Pick 15 ads, read their transcripts, and check if the AI labels are correct.
# First run: creates label_check.csv for you to fill in.
# After filling: re-run this script to see the error rate.
# ══════════════════════════════════════════════════════════════════════════════
h("8. Manual label check")
LABEL_PATH = os.path.join(INTER_DIR, "label_check.csv")

if not os.path.exists(LABEL_PATH):
    # create the CSV for manual review
    sample = ads.sample(n=min(LABEL_SAMPLE_N, len(ads)), random_state=42)
    out = sample[["ad_id"] + LABEL_COLS].copy()
    out["hook_line"]   = sample["hook_line"]
    out["transcript"]  = sample["transcript"].astype(str).str[:400]
    out["reviewed"]    = ""   # type y when you have read the transcript
    out["error_noted"] = ""   # describe any wrong label; leave blank if all correct
    out.to_csv(LABEL_PATH, index=False)
    p(f"**Status: PENDING.** `{os.path.basename(LABEL_PATH)}` created with {len(out)} ads. "
      "Read each transcript, compare with the labels, type `y` in `reviewed`, and describe any "
      "wrong label in `error_noted`. Then re-run this script.")
else:
    # report the results of the manual review
    chk      = pd.read_csv(LABEL_PATH).fillna("")
    reviewed = chk[chk["reviewed"].astype(str).str.lower().str.strip() == "y"]
    if len(reviewed) == 0:
        p("**Status: PENDING.** label_check.csv exists but no rows are marked reviewed = y.")
    else:
        n_err = (reviewed["error_noted"].astype(str).str.strip() != "").sum()
        p(f"**Status: DONE (manually).** Reviewed {len(reviewed)} ads, "
          f"{n_err} with at least one wrong label ({n_err / len(reviewed) * 100:.0f}%). "
          f"Labels checked: {', '.join(LABEL_COLS)}.")
        if len(reviewed) < 10:
            p(f"Only {len(reviewed)} reviewed. Aim for at least 10.")
        errs = reviewed[reviewed["error_noted"].astype(str).str.strip() != ""][["ad_id", "error_noted"]]
        if not errs.empty:
            table(errs, max_rows=len(errs))

# ══════════════════════════════════════════════════════════════════════════════
# 9. KNOWN LIMITS AND RISK FLAGS
# Pre-written table of all known data issues from the brief.
# ══════════════════════════════════════════════════════════════════════════════
h("9. Known limits and risk flags")
p("| Flag | Detail |")
p("|---|---|")
p("| Ad performance numbers are synthetic | Treat as the brand's export, as the brief says |")
p("| AI labels: mostly right, not always | See section 8 for the status of the manual check |")
p(f"| Only {len(ids_aud)} of {len(ids_main)} creators have audience data | {', '.join(sorted(ids_aud))} |")
p(f"| Hidden like counts | {len(hidden)} posts at likes <= {HIDDEN_LIKES_MAX}; do not rank on likes |")
p(f"| Missing plays | {len(no_plays)} posts; engagement per play not computable for them |")
p("| Ads vary hugely in spend | Use a minimum-spend threshold in Step 2 |")
p(f"| Ads ran {int(ads['days_live'].min())} to {int(ads['days_live'].max())} days (up to 26 Oct 2026) | "
  "Compare rates, not totals |")
p("| Creator comment data missing for all creators | Do not use comments for ranking |")
p(f"| {len(zero_purch)} ads have zero purchases | Cost per purchase undefined; handle in Step 2 |")

# ══════════════════════════════════════════════════════════════════════════════
# WRITE OUTPUT
# ══════════════════════════════════════════════════════════════════════════════
out_path = os.path.join(INTER_DIR, "data_audit.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("# Data Audit\n\n_Generated by src/step1_audit.py_\n\n")
    f.write("\n".join(lines))

print(f"Audit written to {out_path}")
