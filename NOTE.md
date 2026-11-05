# NOTE — Key Choices and What to Build Next

_One-page note accompanying the Little Joys creator selection._

---

## Key Choices

**1. No ML model — plain statistics and a weighted score**

With 100 ads and 20 creators, any model would overfit immediately and be impossible
to explain to the marketing manager. A visible weighted score with bootstrap
confidence intervals is less impressive but more trustworthy. The weights are in
a config dict at the top of `src/step5_scoring.py` — anyone can read and challenge them.

**2. Minimum spend threshold of INR 5,000**

The 10th percentile of ad spend from the audit was INR 5,053. Ads below this level
had too few impressions and purchases to give stable rates. A ₹298 ad with 2 clicks
tells us nothing about what works. We flagged those 10 ads rather than deleting them,
so they remain in the file for reference.

**3. Likes excluded from all scoring**

10 posts across 3 creators had hidden like counts (showing as exactly 3, not 0).
Since likes are selectively hidden, comparing creators on likes would be unfair.
All engagement scoring uses plays and reshares only.

**4. Bootstrap confidence intervals instead of p-values**

With small group sizes (some label groups had n=6 or n=7), p-values would be
misleading. Bootstrap CIs give a range that is easier to interpret:
if the lower bound of the in-group CI is above the out-group mean,
we call it a win on that metric. A pattern needs to win on 2+ metrics to be kept.

**5. Child on camera as the heaviest weight (35%)**

This was the strongest signal in the data: child-led ad format had ROAS delta +1.02,
the highest of any label. Child presenter had ROAS delta +0.95. Both held on 3–4 of
5 metrics. No other pattern came close. Weighting it at 35% reflects that dominance.

**6. Controlling for product_form in Step 3**

Gummies and milk-mix powder are different products with different price points and
audience intents. Running patterns on all ads together would mix these signals.
We ran analysis three times: all products, gummies only, milk-mix only.
The child-on-screen pattern held for both — which increased our confidence in it.

**7. LLM used only for brief language in Step 6**

The brief opening lines, concepts, talking points and captions were drafted with
LLM assistance (Groq), then every claim was checked against the ad data. Anything
the LLM invented that wasn't in the `claims_made` of the top ROAS ads — or that hit
the hand-written AVOID list (doctor-recommended / child health claims) — was flagged
and logged. The selection of the 5 creators is not made by the LLM: it comes from a
transparent weighted score and the `pick_top5()` rule in `src/pick_logic.py`, with
weights I set and can defend. The LLM writes; the data and the rules decide.

**8. CR-05 flagged, not removed**

sia_3vedi ranked #1 by score and appeared in 99.8% of stress-test scenarios.
Removing her automatically would mean the data doesn't drive the decision.
Instead, we flagged the child-creator risk clearly (taste-and-fun messaging only,
guardian sign-off required) and gave the brand a specific swap option — **CR-15
(tej.lil.diary), the strongest runner-up with no risk flags** — with its own data
justification. The decision stays with the brand.

---

## What I Would Build Next With One More Week

**1. Creator-level ad performance linkage**

The current model scores creators on their organic posts. With one more week,
I would attempt to link ad IDs to creator handles (via transcript or visual similarity)
to see which creators have actually run Little Joys ads before and how those performed.
This would give a direct performance signal instead of a proxy from organic content.

**2. Audience data for all 20 creators**

Only 3 creators have audience demographics. The single most valuable addition
would be audience data (age, gender, cities, country) for the remaining 17.
This would let us score creators on audience-brand fit, not just content-brand fit.

**3. Transcript-based content analysis**

Only 28.8% of posts have transcripts. With full transcripts, we could measure
how often each creator naturally uses language that matches the winning ad patterns
(problem_statement hook, brand named early, storytelling structure) —
a much stronger signal than format labels alone.

**4. Sensitivity analysis on the minimum spend threshold**

We chose INR 5,000 as the threshold. A more rigorous approach would test
several thresholds (INR 2,500, 5,000, 10,000, 20,000) and check whether
the winning patterns change. If they don't, the threshold choice doesn't matter.
If they do, we'd want to understand why.

**5. Automated brief verification**

Currently, claim verification in Step 6 is manual. With more time, I would write
a script that takes each claim from a brief and checks it against the `claims_made`
column of all ads — flagging any claim that doesn't appear verbatim. This would
make the no-invented-claims guarantee automatic rather than human-checked.

---

_See `outputs/answer_for_manager.md` for the full answer and `outputs/briefs.md` for creator briefs._