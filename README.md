# Little Joys: Creator Selection

Take-home assignment for Galvor. The question: **which 5 of 20 creators should
Little Joys work with next, and what should each of them say?**

---

## The Problem

Little Joys is a kids' nutrition brand (milk-mix powder and gummies).
The brief provides 4 data files:

| File | Rows | What it holds |
|---|---|---|
| `ads.csv` | 100 | One row per ad: spend, impressions, purchases, revenue, ~35 AI labels |
| `creators.csv` | 20 | Profile, followers, persona, feed description |
| `creator_posts.csv` | 392 | ~20 recent posts per creator: plays, reshares, transcripts |
| `creator_audience.csv` | 3 | Audience demographics for 3 of the 20 creators |

The task: use the brand's own data to pick 5 creators and write a brief for each.

## How to Run

```bash
# 1. Clone the repo and install dependencies
git clone https://github.com/vijayaditya123/little-joys-creator-picks.git
cd little-joys-creator-picks
pip install -r requirements.txt

# 2. Add your Groq API key for Step 6 (brief drafting)
#    Create a .env file in the repo root containing:
#    GROQ_API_KEY=your_key_here

# 3. Run each step in order
python src/step1_audit.py             # data audit   -> intermediate/data_audit.md
python src/step2_ad_metrics.py        # ad metrics   -> intermediate/ad_metrics.csv
python src/step3_winning_patterns.py  # patterns     -> intermediate/winning_patterns.csv
python src/step4_creator_profiles.py  # profiles     -> intermediate/creator_profiles.csv
python src/step5_scoring.py           # scoring      -> intermediate/ranking.csv, stability.csv
python src/step6_briefs.py            # briefs (LLM) -> outputs/briefs.md
```

The final answer for the marketing manager — `outputs/answer_for_manager.md` — and
this README and `NOTE.md` are written documents, not script output.

> After running step1, open `intermediate/label_check.csv`, fill in the `reviewed`
> and `error_noted` columns manually, then re-run step1 to get the label error rate.

## Repo Structure

```
little-joys-creator-picks/
├── data/                    # raw CSVs (not modified)
│   ├── ads.csv
│   ├── creators.csv
│   ├── creator_posts.csv
│   └── creator_audience.csv
├── src/                     # one script per step + shared selection logic
│   ├── step1_audit.py
│   ├── step2_ad_metrics.py
│   ├── step3_winning_patterns.py
│   ├── step4_creator_profiles.py
│   ├── step5_scoring.py
│   ├── step6_briefs.py
│   └── pick_logic.py        # selection + variety rules (unit-tested)
├── intermediate/            # working files (one step feeds the next)
│   ├── data_audit.md
│   ├── label_check.csv      # fill in manually after step1
│   ├── ad_metrics.csv
│   ├── winning_patterns.csv
│   ├── winning_patterns_summary.md
│   ├── creator_profiles.csv
│   ├── ranking.csv
│   ├── stability.csv
│   └── claim_evidence.csv   # claims built from the ad data (Step 6)
├── outputs/                 # final deliverables only
│   ├── briefs.md
│   └── answer_for_manager.md
├── ai_log/
│   └── decisions.md         # moments where the AI was corrected
├── tests/                   # unit tests (pytest)
│   ├── test_pick_top5.py
│   └── test_pattern_score.py
├── architecture.html        # visual pipeline diagram
├── requirements.txt
├── README.md                # this file
└── NOTE.md                  # one-page choices and what to build next
```

## Folder Rule

The pipeline follows one rule for file locations:

- **`data/`** — raw input CSVs, never modified.
- **`intermediate/`** — every step writes its working files here, and every step
  reads its inputs from here. This is the hand-off between steps (e.g. Step 2
  writes `ad_metrics.csv`, Steps 3, 4 and 6 read it).
- **`outputs/`** — final deliverables only (`briefs.md`, `answer_for_manager.md`).
- **`ai_log/`** — the AI correction log (`decisions.md`).

Each step calls `os.makedirs(..., exist_ok=True)` for the folders it needs, so a
fresh clone runs without manual setup.

## Method

Plain statistics and a weighted score. No ML model.

**Why no ML?** With 100 ads and 20 creators, a model would overfit immediately
and be impossible to explain. A visible weighted score with bootstrap confidence
intervals is more trustworthy for a decision of this size.

**Pipeline:**

```
raw CSVs -> audit -> ad metrics -> winning patterns -> creator profiles
                                                            |
  final answer <- briefs <- scoring + stress test <---------
```

**AI use:** an LLM (Groq) was used only to draft brief language in Step 6 — concept,
opening line, talking points, claim-to-avoid, and caption. Allowed claims are built
at runtime from the ad data, and a claim-checker flags any invented number or unsafe
claim. Every correction is logged in `ai_log/decisions.md`.

## Key Findings

**What works in Little Joys ads (from 90 ads above INR 5,000 spend threshold):**

| Pattern | ROAS delta | Signal |
|---|---|---|
| Child-led ad format | +1.02 | Strong |
| Child presenter creator type | +0.95 | Strong |
| Child reacts to taste on screen | +0.45 | Strong |
| Child speaks in the ad | +0.43 | Strong |
| Brand named in first 3 seconds | +0.26 | Moderate |
| Buy-now CTA | +0.24 | Moderate |
| Storytelling persuasion | +0.06 | Moderate |

**The 5 picks:**

| Creator | Followers | Product | Stability |
|---|---|---|---|
| @sia_3vedi (CR-05) | 2,831,180 | Nutrimix | 99.8% |
| @raja_choudhary04 (CR-11) | 196,955 | Nutrimix | 100.0% |
| @paediatrics_decoded (CR-16) | 263,188 | Nutrimix | 81.8% |
| @raising_zohran (CR-12) | 22,659 | Gummies | 61.6% |
| @radhikabansal0908 (CR-17) | 395,569 | Nutrimix | 46.6% |

**Stability** = how often the creator stayed in the final 5 across 500 random
weight variations. CR-05 carries a child-creator flag (see the answer and NOTE);
the strongest no-flag runner-up is CR-15 (tej.lil.diary).

## Data Limits

- Ad performance numbers are synthetic (brief instruction — treat as real)
- AI labels may contain errors — manual check scaffold in `intermediate/label_check.csv`
- Only 3 of 20 creators have audience data
- Hidden like counts on 10 posts — likes excluded from all scoring
- 39 posts missing plays data
- Patterns are correlational, not causal

---

_See `outputs/answer_for_manager.md` for the full answer._  
_See `NOTE.md` for key choices and what to build next._
