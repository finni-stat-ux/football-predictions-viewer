# Historical Match Results — verified observation archive

This is an **individual-match prediction record**, separate from the three-season retrospective backtest metrics.

## Initial release (18 Oct 2026)

- 17 completed matches: one EFL Championship fixture dated 16 Oct and sixteen games dated 17 Oct (eleven Championship, five Premier League).
- Three independently published prediction sources per match: Dixon–Coles, XGBoost and the production Hybrid, for **51 model rows**.
- Every probability and top score comes from the **immutable viewer commit** [615b3c2b9c2cbda33f2507ddca5e617a34d5a2fb](https://github.com/finni-stat-ux/football-predictions-viewer/blob/615b3c2b9c2cbda33f2507ddca5e617a34d5a2fb/published/predictions.csv), originally published at **2026-10-15T11:24:57+00:00**, prior to every included fixture's UTC date. No current model was rerun to manufacture historical predictions.
- Verified **90-minute scores** were checked from published full-time results. League-specific links are present in every row: FBref (Burnley–Wolves, 16 Oct), RTÉ Sport (Championship, 17 Oct), Sky Sports (Premier League, 17 Oct).
- Matrix wasn't published in that qualifying 15 October forecast, so there is **no Matrix historical game-level result** in the initial release. W-H-W isn't independent: its underlying probability estimate is Hybrid.
- Fixture IDs such as `FUTURE_22` were intentionally **not** used as historical join keys because they change when forecasts refresh. The archive uses competition, UTC fixture date and exact home/away club names.

## Validation and viewing

`historical_matches.validated_history` rejects missing identity, duplicate model forecasts for the same match, conflicting final results across models, invalid goal counts and probabilities, and missing or insecure source URLs. **The forecast must be timestamped earlier than midnight UTC at the start of the match date**, even if it could have occurred before the actual kickoff. This deliberately excludes uncertain same-day snapshots where no independently verified kickoff was retained.

On the website, expand **Historical Match Results · predictions vs final scores**, choose a league and model, optionally select a date, and select a completed match. You can see the pick, its source probability, the actual full-time score, and whether the pick was correct. The link to the Git-committed probability CSV proves it was stored before the result.

## Future completed matches

The current implementation is **read-only** and uses a curated snapshot. It does not automatically fetch new historical results, dispatch private GitHub Actions, consume a new API or use additional paid resources. New rows require a verified finished match and a previously committed eligible pre-match forecast. Never generate a historical row from a model retrained after the result, and never assume a score from an unavailable match. Any future automated settlement process must retain this timestamp audit and source provenance.

Accuracy from 17 matches is a very small sample and cannot substitute for ongoing, prospective calibration or indicate betting profitability. The current three-season aggregate backtest comparisons remain under **Models & performance**.
