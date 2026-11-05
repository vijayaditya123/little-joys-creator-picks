# Which 5 Creators Should Little Joys Work With Next?

_Prepared from Little Joys' own ad performance data and creator post data._
_Every finding below traces to a row in the data. No claim is invented._

---

## 1. The 5 Picks

| # | Creator | Followers | Product | Confidence | Stability | Risk |
|---|---|---|---|---|---|---|
| 1 | @sia_3vedi (CR-05) | 2.8M | Nutrimix | Medium | 99.8% | Child creator — needs parent approval |
| 2 | @raja_choudhary04 (CR-11) | 197k | Nutrimix | High | 100% | None |
| 3 | @paediatrics_decoded (CR-16) | 263k | Nutrimix | High | 81.8% | None |
| 4 | @raising_zohran (CR-12) | 23k | Gummies | Medium | 61.6% | Low reach — micro tier |
| 5 | @radhikabansal0908 (CR-17) | 396k | Nutrimix | Low | 46.6% | None |

**Stability** = how often this creator stayed in the final 5 across 500 random weight
variations. A high number means the pick is robust; a low number means it depends more
on the exact weights chosen.

> **One decision for the brand to make:** CR-05 (sia_3vedi) ranks #1 and is in the
> final 5 in 99.8% of weight scenarios — but she is a child creator managed by her
> parents. All her messaging must be taste-and-fun only, no health claims, and the
> brief needs guardian sign-off. If that is not acceptable, the strongest no-flag
> replacement is **CR-15 (tej.lil.diary)**, the top runner-up.

---

## 2. The Reasoning

### What the ad data showed

We analysed 90 ads above a minimum spend threshold of INR 5,000 (the bottom 10% by
spend were too small to give reliable rates). For each ad label — hook type, format,
who is on screen, when the brand is named — we compared ads that had that label against
ads that didn't, using bootstrap confidence intervals so every finding comes with a range.

The clearest pattern across the data:

| Pattern | ROAS delta vs rest | Signal |
|---|---|---|
| Ad format: child-led | +1.02 | Strong |
| Creator type: child presenter | +0.95 | Strong |
| Child reacts to taste on screen | +0.45 | Strong |
| Child speaks in the ad | +0.43 | Strong |
| Brand named in first 3 seconds | +0.26 | Moderate |
| Buy-now CTA | +0.24 | Moderate |
| Storytelling persuasion | +0.06 | Moderate |

**In plain terms:** ads where a child is visibly on screen — reacting to the taste,
speaking naturally, or leading the video — consistently outperform every other format.
This held for all products combined and for milk-mix powder specifically. For gummies,
identity-appeal and question hooks performed better (a more discovery-led audience).

### How we scored creators

Each of the 20 creators got a fit score from five dimensions, with visible weights:

| Dimension | Weight | Why |
|---|---|---|
| Child on camera % | 35% | Strongest signal from the ad data |
| Median plays | 25% | Creator must be seen to drive conversions |
| Sponsored post experience | 15% | Lower execution risk |
| Pattern match (from Step 3) | 15% | Overall fit with what works |
| Reshare rate | 10% | Shareability amplifies organic reach |

Risk flags (already worked with Little Joys, child creator, audience mismatch, few
posts, missing data) were subtracted as penalties. Weights live in
`src/step5_scoring.py` and can be changed and re-run.

### Why these 5 and not others

- **CR-20 (storiesbyvihaa)** has huge reach (2.2M median plays) but was penalised for
  two flags: already worked with Little Joys, and child creator — less new value.
- **CR-06 (thatkushalmistry)** has 1.7M followers but 0% child on camera — the opposite
  of what the data says works.
- **CR-14 (parentingtips_surat)** has 1.1M followers but a cross-border audience and a
  platform mismatch between its files that we cannot resolve.
- **CR-15 (tej.lil.diary)** is the strongest no-flag runner-up — the natural swap-in if
  CR-05 is ruled out.

---

## 3. What Each Creator Should Say

Full briefs — concept, opening line, talking points, claims to make, claims to avoid,
and a ready caption — are in `outputs/briefs.md`. The one-line version:

| Creator | Product | Core idea |
|---|---|---|
| @sia_3vedi | Nutrimix | Child refuses plain milk, then asks for more after one sip. Taste-and-fun only. |
| @raja_choudhary04 | Nutrimix | Dad quietly mixes protein into roti; child eats, never notices. |
| @paediatrics_decoded | Nutrimix | Pediatrician explains the protein gap, then shows the simple fix. |
| @raising_zohran | Gummies | Child picks up a gummy on their own — the whole review. |
| @radhikabansal0908 | Nutrimix | "What I actually feed my kids" demo — no taste change. |

The brief language was drafted with an LLM and every claim was checked against the ad
data; anything invented was removed and logged in `ai_log/decisions.md`.

---

## 4. What to Watch Out For

| Limit | What it means in practice |
|---|---|
| Ad performance numbers are synthetic | Treat the patterns as directional signals, not exact forecasts |
| AI labels are mostly right, not always | A manual check of 15 ads is in `intermediate/label_check.csv` |
| Only 3 of 20 creators have audience data | We cannot verify who follows most creators |
| Hidden like counts on 10 posts | Likes were excluded from all scoring — plays and reshares used instead |
| 39 posts missing plays data | Engagement rates use available posts only |
| CR-12 has low reach (14k median plays) | Add a reach guarantee if the brand needs minimum impressions |
| CR-05 is a child creator | Messaging must be taste-and-fun only; brief needs guardian sign-off |
| Patterns are correlational | Child-led ads performing better does not prove causation |

---

_Full methodology: `src/` directory. Working data: `intermediate/` directory._
_Full creator briefs: `outputs/briefs.md`. AI correction log: `ai_log/decisions.md`._
