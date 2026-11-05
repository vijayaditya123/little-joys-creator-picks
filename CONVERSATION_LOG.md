# Conversation Log — Little Joys Creator Picks Code Review & Fixes

_Session date: 2026-11-05. A working log of the end-to-end code review and the
fixes applied to the pipeline, written as a record of what was asked, what was
found, and what was changed._

---

## Session overview

The user asked for an end-to-end review of the `little-joys-creator-picks`
pipeline against the Galvor take-home problem statement, then requested a series
of scoped fixes. Each fix was implemented, verified, and reported. The problem
statement: _"Which 5 of these 20 creators should Little Joys work with next, and
what should each of them say?"_ — answered from the brand's own data.

---

## 1. End-to-end code review

Read the problem statement (`.docx`) and all source files (`step1`–`step6`,
plus outputs and docs). Overall verdict: solid, well-structured pipeline for the
problem size; visible weighted score + bootstrap CIs is the right call over ML
for 100 ads / 20 creators.

Issues found (ranked):

| # | Severity | Issue | File |
|---|---|---|---|
| 1 | High | Stress test skipped the variety rules — stability % was score-only | step5 |
| 2 | High | `product_form` analysed as a creative label | step3 |
| 3 | Medium | `pattern_score` hard-coded, not read from Step 3 output | step4 |
| 4 | Medium | `weighted_score` not clamped to 1.0 | step5 |
| 5 | Medium | `check_claims()` missed non-ASCII/Hindi claims | step6 |
| 6 | Low | step7 scripts referenced in README but missing | README |
| 7 | Low | `.env` present — confirm not tracked before pushing | .env |
| 8 | Low | Unused packages in requirements.txt | requirements.txt |

**Correction from the user:** the pipeline's folder convention is
`intermediate/` for working files and `outputs/` for final deliverables. The
initial review wrongly assumed everything went to `outputs/`. (This later turned
out to be only partly true in the code — see fix in section 7.)

---

## 2. Fix: stress test now applies the variety rules

**Problem:** the main picks applied two variety rules (max 2 per persona, at
least 1 regional-language creator), but the 500-iteration stress test picked the
top 5 by score alone (`stress_scores.nlargest(5)`), so stability % did not
reflect the real selection.

**Changes:**
- Extracted selection into `pick_top5(scores, meta)` + `is_regional(lang)` in a
  new module `src/pick_logic.py` (importable without triggering a CSV load).
- `step5` imports from it; main picks and every stress iteration use the same
  function (rules live in one place).
- Stress test records two metrics per creator: `raw_top5_rate` (score-only top 5)
  and `final_pick_rate` (final 5 after variety rules). Added a `pick_type` label
  (`score_pick` / `variety_pick` / `not_picked`).
- Added `tests/test_pick_top5.py` (6 tests, all pass).

**Verification:** `pick_top5` reproduced the same 5 picks. For all 20 creators
`raw_top5_rate == final_pick_rate` — the variety rules never bind with the data/
weights, so every pick is a `score_pick`. **CR-12 is a genuine score pick at
45.4%, not a variety pick** — disproving the original concern.

Old vs new stability (identical, as expected): CR-11 100, CR-05 99.6, CR-17 71.0,
CR-10 67.4, CR-12 45.4.

---

## 3. Fix: `product_form` removed as a creative label

**Problem:** `product_form` was in `SINGLE_LABELS` but is also the scope-splitter
(gummies vs milk_mix_powder). Comparing it as a label ("gummies vs non-gummies")
is meaningless — it is a product attribute, not a creative choice.

**Changes:**
- Removed `"product_form"` from `SINGLE_LABELS` (with an explanatory comment).
- Kept it as the scope splitter.
- Added a "Context: product form (not a creative pattern)" table (n ads, median
  ROAS, median cost per purchase per product form) before the label results.
- Added a report line stating product form is analysed as a scope, not a pattern.

**Verification:** `product_form` now yields 0 rows in results. Labels analysed
went from 13 → 12. **No other finding changed** (each label is compared
independently). step6's use of `product_form` (to filter reference ads per
product) is legitimate and was left unchanged.

Context table:

| Product form | n ads | Median ROAS | Median cost/purchase |
|---|---|---|---|
| gummies | 20 | 0.85 | 652.93 |
| milk_mix_powder | 48 | 1.20 | 525.94 |
| other | 22 | 1.23 | 532.96 |

---

## 4. Fix: `pattern_score` now reads winning_patterns.csv

**Problem:** the 0–4 `pattern_score` was a hard-coded re-encoding of Step 3's
signals; it did not read `winning_patterns.csv`, so re-running Step 3 with
different labels/thresholds would not change it, and two of its four signals
(reach, sponsored experience) were not Step 3 patterns at all (they double-counted
Step 5 dimensions).

**Changes:**
- Added a visible `PATTERN_MAP` dict (one commented line per mapping) connecting
  each Step 3 pattern `(label_col, label_val)` to a creator-side check.
- `pattern_score` now reads `winning_patterns.csv`; only kept patterns
  (`signal != weak_signal`) that have a mapping contribute. Max is dynamic
  (`MAX_PATTERN_SCORE`), written to the profile as `pattern_score_max`.
- Loud warning for every kept-but-unmapped pattern.
- Missing-file guard: if `winning_patterns.csv` is absent, stop with "Run Step 3
  first" — no fallback to hard-coded values.
- step5 normalises by the actual max instead of `/ 4.0`; "0–4" text updated.
- Added `tests/test_pattern_score.py` (5 tests, all pass).

**Key honest finding:** `MAX_PATTERN_SCORE` collapsed from 4 to **1** because
(a) `language` is not a kept pattern (every language value is weak; `language=Hindi`
has a negative ROAS delta), and (b) the five child patterns collapse to one
observable creator signal (children on camera ≥40%). All 20 pattern_scores
changed. **The picks changed:** new top 5 = CR-05, CR-11, CR-16, CR-12, CR-17
(CR-16 in, CR-10 out). This was flagged to the user as a real consequence.

---

## 5. Fix: `weighted_score` upper clamp + docstring

**Problem:** the score clamped the lower bound to 0.0 but not the upper bound to
1.0.

**Check first (no change):** proved no score can exceed 1.0 — weights sum to 1,
all dimensions in [0,1], penalty only subtracts. Base max 0.7046; max across base
+ all 500 stress iterations 0.8396. Never exceeds 1.0.

**Changes:** added `min(1.0, ...)` as a defensive guarantee; docstring states
the 0–1 range and that risk penalties are fixed (not varied in the stress test).
Added a stability-section sentence: _"The stress test varies the scoring weights.
The ad spend threshold and the risk penalties are held fixed."_

**Verification:** picks and all `final_pick_rate`/`raw_top5_rate` numbers
identical before vs after (as expected — the ceiling was never reached).

---

## 6. Fix: pipeline folder rule (the step6 crash)

**Problem:** step5 read/wrote to `OUTPUT_DIR`; step6 read `ranking.csv`,
`stability.csv`, `ad_metrics.csv` from `OUTPUT_DIR` — but `ad_metrics.csv` only
exists in `INTER_DIR`, so step6 crashed.

**Rule enforced:** every step reads inputs from and writes working files to
`intermediate/`; only final deliverables go to `outputs/`.

**Changes:**
- step5: reads `creator_profiles.csv` and writes `ranking.csv`/`stability.csv` to
  `intermediate/`.
- step6: reads all three inputs from `intermediate/`; writes `briefs.md` to
  `outputs/`; `decisions.md` stays in `ai_log/`.
- Fixed a redundant `stability` merge in step6 that collided with the
  `final_pick_rate` column now present in `ranking.csv` (a correctness fix the
  path migration exposed).
- README run-comments and repo structure corrected; added a "Folder Rule" section.
- Steps all `os.makedirs(..., exist_ok=True)` for the folders they need.

**Verification:** from-zero run completed steps 1–5 into `intermediate/`; step6's
original crash is gone (all three inputs load). A new, unrelated blocker surfaced:
`KeyError: 'CR-16'` in step6's hand-curated `CREATOR_META` (CR-16 became a pick
after the pattern_score fix) — fixed in section 8.

---

## 7. Five small cleanup items

1. **ALLOWED_CLAIMS → runtime evidence table + AVOID_CLAIMS.** step6 now builds
   `intermediate/claim_evidence.csv` (353 claims with n_ads + median ROAS) at
   runtime. Added a hand-written `AVOID_CLAIMS` list (doctor-recommended,
   immunity/health claims for children, guarantees, growth promises) that
   overrides the evidence table. `check_claims` returns `unverified` and `avoid`
   lists and prints creator-named warnings. Rationale: a winning ad can contain a
   claim that is unsafe to repeat, so the allow-list must not be auto-built from
   top-ROAS ads alone.
2. **Stale `outputs/ad_metrics.csv`.** Confirmed no code reads it; fixed the stale
   step2 docstring. The file itself is locked by OneDrive and must be deleted
   manually.
3. **Column validation in step6.** Added a required-columns guard across
   ranking.csv / stability.csv / ad_metrics.csv that stops with a clear message.
   Confirmed `is_pick` matches between step5 write and step6 read.
4. **.gitignore.** Added `.pytest_cache/` (`__pycache__/`, `*.pyc` already present).
   Not a git repo, so nothing tracked to untrack.
5. **architecture.html chips.** All chips show `intermediate/` for working files
   and `outputs/` for deliverables, plus a folder-rule note in the legend.

---

## 8. CR-16 fallback (defensive, no invented marketing)

Added `default_meta(cid)` in step6 so any pick without a hand-written
`CREATOR_META` entry gets safe defaults (product = milk-mix powder, risk/swap =
"NEEDS REVIEW") and a printed warning. This fixed the `KeyError: 'CR-16'`.
step6 ran all 5 briefs to completion with this in place ("Briefs saved" / "AI log
saved"). Also removed a stray " yes" string that had been accidentally injected
into the `CREATOR_META` CR-12 entry (would have been a syntax error).

---

## Final state

**Final 5 picks (deterministic, confirmed stable):**

| # | Creator | Followers | fit_score | final_pick_rate | pick_type |
|---|---|---|---|---|---|
| 1 | @sia_3vedi (CR-05) | 2.8M | 0.7046 | 99.8% | score_pick |
| 2 | @raja_choudhary04 (CR-11) | 197k | 0.6435 | 100.0% | score_pick |
| 3 | @paediatrics_decoded (CR-16) | 263k | 0.5883 | 81.8% | score_pick |
| 4 | @raising_zohran (CR-12) | 22.7k | 0.5521 | 61.6% | score_pick |
| 5 | @radhikabansal0908 (CR-17) | 396k | 0.5397 | 46.6% | score_pick |

**Tests:** 11 pass (6 `test_pick_top5` + 5 `test_pattern_score`). All changed
scripts compile.

**Files added:** `src/pick_logic.py`, `tests/test_pick_top5.py`,
`tests/test_pattern_score.py`, `ISSUES.md`, this log.

**Files modified:** `src/step2_ad_metrics.py`, `src/step3_winning_patterns.py`,
`src/step4_creator_profiles.py`, `src/step5_scoring.py`, `src/step6_briefs.py`,
`README.md`, `architecture.html`, `.gitignore`.

**Constraints honoured throughout:** no changes to scoring weights, the ad spend
threshold, the variety rules, or analysis logic beyond what each fix explicitly
required. Weights/threshold/penalties left as-is.

---

## Known environment limitations (not code defects)

- **OneDrive sync** on the project folder intermittently locked/cleared files in
  `intermediate/` between separate command invocations, preventing a clean
  single from-zero verification. Each step succeeded individually and the full
  pipeline completed in a single uninterrupted session; running from a
  non-OneDrive local folder would remove this instability.
- **Groq free-tier rate limiting** caused step6's LLM calls to fail intermittently
  after many test runs. The code path is correct (step6 completed all 5 briefs
  earlier in the session); the failures are API quota, not logic.
- **`outputs/ad_metrics.csv`** is a locked stale leftover to delete manually once
  OneDrive releases it. No code reads or writes it anymore.

## Recommended next actions

- Add a CR-16 entry to `CREATOR_META` (product, risk note, swap note) or revert to
  the earlier pick set — a human decision, not auto-generated.
- Optionally add retry/backoff around the Groq call in step6 so transient API
  failures do not abort the run.
- Run the pipeline from a non-OneDrive local folder for a clean end-to-end pass.
