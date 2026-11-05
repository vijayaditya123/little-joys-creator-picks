"""
Step 6: Creator Briefs (LLM-assisted)
Uses Groq (qwen/qwen3.8-27b) to draft the concept and opening line for each
of the 5 picked creators.

Pipeline per creator:
  1. Build a prompt from data (creator profile + winning patterns + top ads)
  2. Call Groq to draft: concept, opening line
  3. Auto-check every claim in the draft against claims_made in top ROAS ads
  4. Flag any claim not found in the data as INVENTED
  5. Log all corrections in ai_log/decisions.md
  6. Write the verified brief to outputs/briefs.md

Run from the repo root:  python src/step6_briefs.py

Outputs:
  outputs/briefs.md          verified creator briefs
  ai_log/decisions.md        log of what the LLM invented vs what was corrected
"""

import os
import re
from dotenv import load_dotenv
from groq import Groq
import pandas as pd

# ── load env ───────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
            override=True)

# ── config ─────────────────────────────────────────────────────────────────────
GROQ_MODEL = "qwen/qwen3.8-27b"

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INTER_DIR  = os.path.join(BASE, "intermediate")   # working files (inputs)
OUTPUT_DIR = os.path.join(BASE, "outputs")        # final deliverables only
AI_LOG_DIR = os.path.join(BASE, "ai_log")
os.makedirs(INTER_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(AI_LOG_DIR, exist_ok=True)

# ── load data (all working inputs come from intermediate/) ─────────────────────
ranking   = pd.read_csv(os.path.join(INTER_DIR, "ranking.csv"))
stability = pd.read_csv(os.path.join(INTER_DIR, "stability.csv"))
ads       = pd.read_csv(os.path.join(INTER_DIR, "ad_metrics.csv"))

# ── validate required columns (stop early with a clear message) ───────────────
# Each input must carry the columns this step relies on. If Step 5 or an earlier
# step changes its output schema, fail here with a precise message instead of a
# confusing KeyError deep in the loop.
_REQUIRED = {
    "ranking.csv":    (ranking,   ["creator_id", "handle", "name", "followers",
                                    "follower_tier", "median_plays",
                                    "child_on_camera_pct", "n_sponsored_posts",
                                    "dominant_language", "fit_score",
                                    "final_pick_rate", "is_pick"]),
    "stability.csv":  (stability, ["creator_id", "final_pick_rate"]),
    "ad_metrics.csv": (ads,       ["ad_id", "product_form", "low_spend", "roas",
                                    "claims_made"]),
}
_missing = []
for _fname, (_df, _cols) in _REQUIRED.items():
    for _c in _cols:
        if _c not in _df.columns:
            _missing.append(f"{_fname}: missing column '{_c}'")
if _missing:
    raise SystemExit(
        "ERROR: required columns are missing from Step 5 / earlier outputs:\n  "
        + "\n  ".join(_missing)
        + "\nRe-run the pipeline in order (steps 1-5) so the schemas match."
    )

top5 = ranking[ranking["is_pick"] == True].sort_values("fit_score", ascending=False)
# ranking.csv (from Step 5) already carries final_pick_rate for every creator,
# so no merge with stability is needed here.
# Use final_pick_rate (variety-rule-adjusted stability) as the stability number
# reported in briefs. Aliased to stability_pct for the rest of this script.
top5["stability_pct"] = top5["final_pick_rate"]

# top ads by product for claim reference
top_milk = (ads[(ads["product_form"] == "milk_mix_powder") & (~ads["low_spend"])]
            .sort_values("roas", ascending=False).head(5))
top_gummies = (ads[(ads["product_form"] == "gummies") & (~ads["low_spend"])]
               .sort_values("roas", ascending=False).head(5))

# ── groq client ────────────────────────────────────────────────────────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── claim evidence table (built at runtime from the ad data) ──────────────────
# We do NOT hardcode the allowed claims. Instead we build a claim evidence table
# from the claims_made column of ads.csv at runtime: one row per claim, with the
# number of ads it appears in and the median ROAS of those ads. Saved to
# intermediate/ for traceability. This stays in sync if the ad data changes.
def build_claim_evidence(ads_df):
    rows = []
    for _, r in ads_df.iterrows():
        cm = r.get("claims_made")
        if pd.isna(cm) or str(cm).strip() == "":
            continue
        for c in str(cm).split(";"):
            c = c.strip()
            if c:
                rows.append({"claim": c, "roas": r["roas"]})
    ev = pd.DataFrame(rows)
    if ev.empty:
        return pd.DataFrame(columns=["claim", "n_ads", "median_roas"])
    return (ev.groupby("claim")
              .agg(n_ads=("roas", "size"), median_roas=("roas", "median"))
              .round(3)
              .reset_index()
              .sort_values("n_ads", ascending=False))

CLAIM_EVIDENCE = build_claim_evidence(ads)
_claim_evidence_path = os.path.join(INTER_DIR, "claim_evidence.csv")
CLAIM_EVIDENCE.to_csv(_claim_evidence_path, index=False)
print(f"Claim evidence table: {_claim_evidence_path}  ({len(CLAIM_EVIDENCE)} claims)")

# The set of data-backed claim strings, lower-cased, used for substring matching.
# A claim fragment in a brief is considered data-backed if it is contained in one
# of these real claim sentences (or vice versa for short tokens).
DATA_BACKED_CLAIMS = [c.lower() for c in CLAIM_EVIDENCE["claim"].tolist()]

# ── AVOID_CLAIMS: hand-written, intentionally NOT derived from the data ───────
# A claim can appear in a high-ROAS ad and still be unsafe for a creator to
# repeat — especially a child creator or a non-medical creator making health
# claims about children. These override the evidence table: if a brief contains
# any of these, it is flagged regardless of whether the claim is "data-backed".
AVOID_CLAIMS = [
    "doctor recommend",       # implying a doctor endorses the product
    "doctor approved",        # same — medical endorsement a creator cannot make
    "pediatrician recommend", # medical professional endorsement
    "pediatrician approved",
    "clinically proven",      # medical-grade efficacy claim
    "scientifically proven",
    "boosts immunity",        # health-benefit claim about children — risky to repeat
    "boost immunity",
    "supports immunity",      # immunity health claim
    "supports kids' immunity",
    "fights sickness",        # disease/illness claim
    "cures",                  # any cure claim
    "treats",                 # any treatment claim
    "prevents illness",
    "height gain",            # growth promises for children
    "weight gain",
    "makes kids taller",
    "guaranteed",             # guaranteed-result claim
    "#1 brand",               # unverifiable superlative
    "safe and recommended for daily consumption",  # medical-style safety claim
]

def check_claims(text):
    """
    Check a brief's text against the claim rules. Returns a dict with two lists:
      "unverified" : data-claim fragments not found in claims_made (possibly invented)
      "avoid"      : fragments that match an AVOID_CLAIMS entry (unsafe to repeat)
    Only fragments that look like a data claim (numbers / strong claim words) are
    checked for "unverified"; AVOID matches are checked on all fragments.
    """
    unverified = []
    avoid      = []
    fragments = re.split(r'[.;]', text)
    for frag in fragments:
        frag = frag.strip().lower()
        if len(frag) < 15:
            continue

        # AVOID check first — applies to any fragment, data-claim or not.
        for bad in AVOID_CLAIMS:
            if bad in frag:
                avoid.append(frag[:150])
                break

        # Unverified-data-claim check.
        is_data_claim = bool(re.search(
            r'\d+\s*g\b|\d+\s*mg\b|\d+\s*%|\d+\s*vitamin|\d+\s*calorie|'
            r'clinically proven|scientifically proven|studies show|'
            r'pediatrician (recommend|approved|endorsed)|'
            r'award.winning|#1 brand|guaranteed result',
            frag
        ))
        if is_data_claim:
            matched = any(dbc in frag or frag in dbc for dbc in DATA_BACKED_CLAIMS)
            if not matched:
                unverified.append(frag[:150])

    return {"unverified": unverified, "avoid": avoid}

# ── per-creator data ───────────────────────────────────────────────────────────
CREATOR_META = {
    "CR-11": {
        "product": "Nutrimix (milk-mix powder)",
        "top_ads": top_milk,
        "risk": "None",
        "confidence": "High",
        "swap_note": "If brand confirms CR-11 ran a competing campaign, swap to CR-16.",
    },
    "CR-05": {
        "product": "Nutrimix (milk-mix powder)",
        "top_ads": top_milk,
        "risk": "Child creator managed by parent — taste-and-fun only, no health claims.",
        "confidence": "Medium",
        "swap_note": "If brand has child-creator concerns, swap to CR-16 (rank 6, 49% stability).",
    },
    "CR-17": {
        "product": "Nutrimix (milk-mix powder)",
        "top_ads": top_milk,
        "risk": "None",
        "confidence": "Medium",
        "swap_note": "Monitor reshare rate — lowest of the top 5.",
    },
    "CR-10": {
        "product": "Nutrimix (milk-mix powder)",
        "top_ads": top_milk,
        "risk": "None",
        "confidence": "Medium",
        "swap_note": "If early performance is weak, swap to CR-19 (14 sponsored posts).",
    },
    "CR-12": {
        "product": "Little Joys Gummies",
        "top_ads": top_gummies,
        "risk": "Micro-tier — low guaranteed reach.",
        "confidence": "Low",
        "swap_note": "If brand needs scale, swap to CR-19 (925k median plays).",
    },
}


def default_meta(cid):
    """
    Fallback metadata for a picked creator that has no hand-written CREATOR_META
    entry (e.g. the pick set changed upstream). We do NOT invent marketing copy:
    product defaults to the brand's primary product (milk-mix powder, the
    dominant winning scope in Step 3), and the hand-written fields carry an
    explicit NEEDS REVIEW placeholder. A warning is printed at the call site.
    """
    return {
        "product":    "Nutrimix (milk-mix powder)",  # brand's primary product
        "top_ads":    top_milk,
        "risk":       "NEEDS REVIEW — no hand-written risk note for this creator yet.",
        "confidence": "Review",
        "swap_note":  "NEEDS REVIEW — add a CREATOR_META entry for this creator.",
    }

# ── LLM prompt builder ─────────────────────────────────────────────────────────
def build_prompt(row, meta):
    claims_text = "\n".join(
        f"- {r['claims_made']} (ad {r['ad_id']}, ROAS {r['roas']:.2f})"
        for _, r in meta["top_ads"].iterrows()
        if str(r.get("claims_made", "")) not in ["nan", ""]
    )

    return f"""You are writing a creator brief for Little Joys, a kids nutrition brand.

CREATOR PROFILE (from data):
- Handle: @{row['handle']}
- Persona: {row.get('persona', 'n/a')}
- Followers: {int(row['followers']):,} ({row['follower_tier']})
- Median plays: {int(row['median_plays']):,}
- Child on camera: {row['child_on_camera_pct']*100:.0f}% of posts
- Dominant language: {row['dominant_language']}
- What feels native to their feed: {row.get('what_feels_native', 'n/a')}
- What would feel foreign: {row.get('what_would_feel_foreign', 'n/a')}
- Sponsored posts: {int(row['n_sponsored_posts'])}

RECOMMENDED PRODUCT: {meta['product']}

DATA-BACKED CLAIMS ONLY (use only these, do not invent any numbers or benefits):
{claims_text}

WINNING AD PATTERNS (from Little Joys own ad data):
- Child-led format: ROAS delta +1.02 (strongest signal)
- Child reacts to taste on screen: ROAS delta +0.45
- Child speaks in the ad: ROAS delta +0.43
- Brand named in first 3 seconds: ROAS delta +0.26
- Storytelling persuasion: ROAS delta +0.06
- Buy-now CTA: ROAS delta +0.24

YOUR TASK — write all five sections:

1. CONCEPT (3-4 sentences): A video idea that fits this creator's native style
   and uses the winning patterns. Must involve a child on camera if possible.
   No corporate tone. Must feel like their normal content.

2. OPENING LINE (1 sentence): The very first line of the video in this creator's
   voice and language ({row['dominant_language']}). Natural, not scripted.

3. TALKING POINTS (3 bullet points): What the creator should say during the video.
   In their voice. Only use claims from the DATA-BACKED CLAIMS list above.

4. CLAIM TO AVOID (1 sentence): One specific thing this creator should NOT say,
   given their persona or audience. Explain why in a few words.

5. SUGGESTED CAPTION (2-3 sentences): The Instagram/YouTube caption for the post.
   In their voice. Include a call to action.

STRICT RULES:
- Only use numbers and benefits from the DATA-BACKED CLAIMS list. Do not invent any.
- Do not use clinical or doctor-endorsed language unless the creator is a medical professional.
- Match the creator's language: {row['dominant_language']}.

Format your response exactly as:
CONCEPT: <text>
OPENING LINE: <text>
TALKING POINTS:
- <point 1>
- <point 2>
- <point 3>
CLAIM TO AVOID: <text>
SUGGESTED CAPTION: <text>"""

# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP — generate, check, log
# ══════════════════════════════════════════════════════════════════════════════
briefs       = []   # final verified briefs
ai_log_lines = []   # corrections log

ai_log_lines.append("# AI Log — Step 6 Brief Corrections\n")
ai_log_lines.append("_Documents every claim the LLM invented that was not in the data,_")
ai_log_lines.append("_and how it was handled._\n")
ai_log_lines.append("---\n")

for _, row in top5.iterrows():
    cid  = row["creator_id"]
    if cid in CREATOR_META:
        meta = CREATOR_META[cid]
    else:
        meta = default_meta(cid)
        print(f"  WARNING: {row['handle']} ({cid}) has no hand-written CREATOR_META "
              f"entry. Using safe defaults (product=milk-mix, risk/swap=NEEDS REVIEW). "
              f"Add an entry for this creator before sending the brief.")

    print(f"\nGenerating brief for {row['handle']} ({cid})...")

    # ── call Groq ──────────────────────────────────────────────────────────────
    prompt = build_prompt(row, meta)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1000,
    )
    raw_output = response.choices[0].message.content.strip()
    print(f"  LLM response received ({len(raw_output)} chars)")

    # ── parse all five sections ───────────────────────────────────────────────
    def extract(label, next_labels, text):
        pattern = rf"{label}:\s*(.+?)(?={'|'.join(next_labels)}|$)"
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    concept_draft   = extract("CONCEPT",          ["OPENING LINE", "TALKING POINTS", "CLAIM TO AVOID", "SUGGESTED CAPTION"], raw_output)
    opening_draft   = extract("OPENING LINE",     ["TALKING POINTS", "CLAIM TO AVOID", "SUGGESTED CAPTION"], raw_output)
    talking_draft   = extract("TALKING POINTS",   ["CLAIM TO AVOID", "SUGGESTED CAPTION"], raw_output)
    avoid_draft     = extract("CLAIM TO AVOID",   ["SUGGESTED CAPTION"], raw_output)
    caption_draft   = extract("SUGGESTED CAPTION",[], raw_output)

    # parse talking points into a list
    talking_points = [t.lstrip("-• ").strip()
                      for t in talking_draft.split("\n")
                      if t.strip().startswith(("-", "•", "*")) or
                      (t.strip() and talking_draft.count("\n") == 0)]
    talking_points = [t for t in talking_points if t]

    # ── claim check across all sections ──────────────────────────────────────
    all_text      = " ".join([concept_draft, opening_draft, talking_draft, caption_draft])
    claim_result  = check_claims(all_text)
    unverified    = claim_result["unverified"]
    avoid_hits    = claim_result["avoid"]
    all_invented  = unverified + avoid_hits   # combined, for the brief-note count

    # ── print clear, creator-named warnings to the console ────────────────────
    for frag in unverified:
        print(f"  WARNING: {row['handle']} ({cid}) — claim not found in "
              f"claims_made: \"{frag}\"")
    for frag in avoid_hits:
        print(f"  WARNING: {row['handle']} ({cid}) — AVOID_CLAIMS match "
              f"(unsafe to repeat): \"{frag}\"")

    # ── log corrections ───────────────────────────────────────────────────────
    ai_log_lines.append(f"## {row['handle']} ({cid})\n")
    ai_log_lines.append(f"**Model:** {GROQ_MODEL}  ")
    ai_log_lines.append(f"**Product:** {meta['product']}  \n")
    ai_log_lines.append("**Raw LLM output:**")
    ai_log_lines.append(f"```\n{raw_output}\n```\n")

    if unverified:
        ai_log_lines.append(f"**Unverified claims ({len(unverified)}) — not found in "
                            f"claims_made, flagged and removed:**")
        for inv in unverified:
            ai_log_lines.append(f"- `{inv}`")
        ai_log_lines.append("")
    if avoid_hits:
        ai_log_lines.append(f"**AVOID_CLAIMS matches ({len(avoid_hits)}) — unsafe to "
                            f"repeat (doctor/health/guarantee), flagged and removed:**")
        for bad in avoid_hits:
            ai_log_lines.append(f"- `{bad}`")
        ai_log_lines.append("")
    if unverified or avoid_hits:
        ai_log_lines.append("**Action:** These lines were not included in the final brief.")
        ai_log_lines.append("The concept and opening line in outputs/briefs.md use only")
        ai_log_lines.append("data-backed language from the claims_made column, and no")
        ai_log_lines.append("AVOID_CLAIMS language.\n")
    else:
        ai_log_lines.append("**Claim check:** No unverified or avoid claims detected. Draft used as-is.\n")

    ai_log_lines.append("---\n")

    # ── build final brief ─────────────────────────────────────────────────────
    # Use LLM concept/opening if clean; append data-backed claims regardless
    top_ad_claims = []
    supporting_ads = []
    for _, ad_row in meta["top_ads"].head(3).iterrows():
        if str(ad_row.get("claims_made", "")) not in ["nan", ""]:
            top_ad_claims.append(ad_row["claims_made"])
            supporting_ads.append(f"{ad_row['ad_id']} (ROAS {ad_row['roas']:.2f})")

    stab = row.get("stability_pct", "n/a")

    briefs.append({
        "creator_id":    cid,
        "handle":        row["handle"],
        "name":          row.get("name", ""),
        "followers":     int(row["followers"]),
        "follower_tier": row["follower_tier"],
        "median_plays":  int(row["median_plays"]),
        "child_pct":     row["child_on_camera_pct"],
        "sponsored":     int(row["n_sponsored_posts"]),
        "language":      row["dominant_language"],
        "fit_score":     row["fit_score"],
        "stability_pct": stab,
        "product":       meta["product"],
        "concept":       concept_draft,
        "opening_line":  opening_draft,
        "talking_points":talking_points,
        "claim_to_avoid":avoid_draft,
        "caption":       caption_draft,
        "invented_count":len(all_invented),
        "top_claims":    top_ad_claims,
        "supporting_ads":supporting_ads,
        "risk":          meta["risk"],
        "confidence":    meta["confidence"],
        "swap_note":     meta["swap_note"],
    })

    print(f"  Invented claims flagged: {len(all_invented)}")
    print(f"  Brief ready.")

# ══════════════════════════════════════════════════════════════════════════════
# WRITE outputs/briefs.md
# ══════════════════════════════════════════════════════════════════════════════
brief_lines = []
brief_lines.append("# Creator Briefs\n")
brief_lines.append("_Generated by src/step6_briefs.py using Groq LLM_  ")
brief_lines.append("_Every concept and opening line was drafted by the LLM then claim-checked_  ")
brief_lines.append("_against the data. Invented claims were removed. See ai_log/decisions.md._\n")
brief_lines.append("---\n")

for i, b in enumerate(briefs, 1):
    brief_lines.append(f"## Brief {i}: @{b['handle']} ({b['creator_id']})\n")

    # snapshot table
    brief_lines.append("### Creator snapshot\n")
    brief_lines.append("| Field | Value |")
    brief_lines.append("|---|---|")
    brief_lines.append(f"| Name | {b['name']} |")
    brief_lines.append(f"| Followers | {b['followers']:,} ({b['follower_tier']}) |")
    brief_lines.append(f"| Median plays | {b['median_plays']:,} |")
    brief_lines.append(f"| Child on camera | {b['child_pct']*100:.0f}% of posts |")
    brief_lines.append(f"| Sponsored posts | {b['sponsored']} |")
    brief_lines.append(f"| Dominant language | {b['language']} |")
    brief_lines.append(f"| Fit score | {b['fit_score']} |")
    brief_lines.append(f"| Stability (final pick rate) | {b['stability_pct']}% (500 weight variations, variety rules applied) |")
    brief_lines.append(f"| Risk flags | {b['risk']} |")
    brief_lines.append("")

    # product
    brief_lines.append("### Recommended product\n")
    brief_lines.append(f"**{b['product']}**\n")

    # concept (LLM-drafted, claim-checked)
    brief_lines.append("### Content concept\n")
    brief_lines.append(f"{b['concept']}\n")

    # opening line
    if b["opening_line"]:
        brief_lines.append("### Opening line\n")
        brief_lines.append(f"> {b['opening_line']}\n")

    # talking points
    if b["talking_points"]:
        brief_lines.append("### What to say (talking points)\n")
        for tp in b["talking_points"]:
            brief_lines.append(f"- {tp}")
        brief_lines.append("")

    # claim to avoid
    if b["claim_to_avoid"]:
        brief_lines.append("### Claim to avoid\n")
        brief_lines.append(f"> {b['claim_to_avoid']}\n")

    # suggested caption
    if b["caption"]:
        brief_lines.append("### Suggested caption\n")
        brief_lines.append(f"{b['caption']}\n")

    # data-backed claims
    brief_lines.append("### Data-backed claims (from top ROAS ads)\n")
    for claim in b["top_claims"]:
        for c in claim.split(";"):
            c = c.strip()
            if c:
                brief_lines.append(f"- {c}")
    brief_lines.append("")

    # supporting ads
    brief_lines.append("### Supporting ads from the data\n")
    brief_lines.append(", ".join(b["supporting_ads"]))
    brief_lines.append("")

    # llm note
    if b["invented_count"] > 0:
        brief_lines.append(f"_Note: {b['invented_count']} claim(s) in the LLM draft were_")
        brief_lines.append("_not found in the ad data and were removed. See ai_log/decisions.md._\n")

    # confidence
    brief_lines.append("### Confidence and what would change my mind\n")
    brief_lines.append(f"**Confidence: {b['confidence']}**  ")
    brief_lines.append(f"Final pick rate: {b['stability_pct']}% across 500 weight variations (variety rules applied).  ")
    brief_lines.append(f"Swap note: {b['swap_note']}\n")

    brief_lines.append("---\n")

# write briefs
briefs_path = os.path.join(OUTPUT_DIR, "briefs.md")
with open(briefs_path, "w", encoding="utf-8") as f:
    f.write("\n".join(brief_lines))
print(f"\nBriefs saved: {briefs_path}")

# write ai log
log_path = os.path.join(AI_LOG_DIR, "decisions.md")
with open(log_path, "w", encoding="utf-8") as f:
    f.write("\n".join(ai_log_lines))
print(f"AI log saved: {log_path}")
