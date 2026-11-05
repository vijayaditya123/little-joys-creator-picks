"""
pick_logic.py — Selection logic for step5_scoring.py

Extracted into its own module so it can be imported by tests without
triggering the module-level CSV load in step5_scoring.py.

Public API:
    is_regional(lang)           -> bool
    pick_top5(scores, meta)     -> list[str]  (5 creator_ids)
"""


def is_regional(lang):
    """True if dominant_language is Hindi/Hinglish or another Indian regional language."""
    return any(l in str(lang).lower()
               for l in ["hindi", "hinglish", "tamil", "malayalam",
                         "kannada", "punjabi", "telugu"])


def pick_top5(scores, meta):
    """
    Apply score ranking + variety rules to select 5 creator_ids.

    Rules (applied in this order):
      1. Sort creators by score descending.
      2. Walk down the list; skip any creator whose persona type (first 30
         chars of the persona string) already appears 2 or more times in the
         current picks.
      3. After filling 5 slots: if none of the 5 posts in a regional language,
         swap the lowest-scoring pick for the highest-scoring regional creator
         from the remainder.

    Parameters
    ----------
    scores : pd.Series
        Fit score for each creator, indexed by the same row index as meta.
    meta : pd.DataFrame
        Must contain columns: creator_id, persona, dominant_language.
        Same row index as scores.

    Returns
    -------
    list of str
        5 creator_id values in the order they were selected (highest score first).
    """
    # merge scores into meta and sort by score descending
    ranked = meta.copy()
    ranked["_score"] = scores
    ranked = ranked.sort_values("_score", ascending=False)

    persona_count = {}
    picks         = []   # row dicts for selected creators
    runners_up    = []   # row dicts for everyone else

    for _, row in ranked.iterrows():
        persona_key = str(row.get("persona", "other"))[:30]

        if len(picks) < 5 and persona_count.get(persona_key, 0) < 2:
            picks.append(row)
            persona_count[persona_key] = persona_count.get(persona_key, 0) + 1
        else:
            runners_up.append(row)

    # regional language check
    has_regional = any(is_regional(r["dominant_language"]) for r in picks)

    if not has_regional:
        regional_runners = [r for r in runners_up
                            if is_regional(r["dominant_language"])]
        if regional_runners:
            swap_in  = regional_runners[0]   # highest-scoring regional in runners_up
            picks[-1] = swap_in              # replace lowest-scoring pick

    return [r["creator_id"] for r in picks]
