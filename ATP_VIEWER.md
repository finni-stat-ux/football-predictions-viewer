# ATP Men's Singles display

The Conquerors site defaults to Football. Use the **Sport** switch at the top to select **ATP Men's Singles**. The ATP view is completely separate from English Premier League and EFL Championship predictions.

## Current availability

**There is no approved ATP snapshot yet.** The ATP page must tell visitors that real match-winning forecasts are not available; no real or fabricated ATP fixtures or probabilities are bundled with this change.

When independently authorised and evaluated ATP forecasts are made available, publish both files together under `published/`:

- `atp_predictions.csv`
- `atp_metadata.json`

The viewer accepts `Surface Elo` (long-run/surface match strength), `Serve/return` (lagged match-point performance), and `ATP Hybrid` (a validation-selected probability mixture of the two). It recomputes the blend to reject internally contradictory forecasts. Missing historical sample or unavailable serve/return history must not be silently labelled a complete two-model Hybrid.

The metadata **must be approved outside this code** by the rights holder/release process and contain:

```json
{
  "schema_version": 1,
  "published_at_utc": "2026-10-19T02:00:00Z",
  "approved_for_publication": true,
  "source_rights_confirmed": true,
  "history_rights_url": "https://EXAMPLE/real-history-rights",
  "fixture_rights_url": "https://EXAMPLE/real-fixture-rights",
  "holdout_checked": true,
  "holdout_matches": 200,
  "hybrid_weight_serve_return": 0.5
}
```

This is a **schema illustration, not an actual licence or release approval**. Do not replace example URLs with invented rights documents or set approval booleans without verifying the source terms and model evaluation.

The CSV needs `fixture_id,match_date,kickoff_utc,event_name,surface,player_a_id,player_b_id,player_a_name,player_b_name,model,p_player_a,p_player_b,serve_return_weight,prior_matches_a,prior_matches_b`. Every row is a **single match / model**. Model outcomes must sum to one, all kickoffs must carry timezone offsets, player IDs/names must agree across rows, and each fixture must have a Surface Elo baseline. A Hybrid is accepted only when the corresponding serve/return forecast also exists and its probability matches the blend weighted by the metadata.

## Source restrictions

- Jeff Sackmann mirrors retain non-commercial dataset restrictions; public accessibility alone does not grant broader usage.
- Tennis-Data.co.uk prohibits automated data harvesting and model-training product usage.
- TennisData.App's free CSV download page says visitors may use files broadly, **but its formal Terms of Service sections 18 and 20 restrict commercial/derivative/republished/competing-product and automated uses**. In the absence of explicit permission, do not use its data to populate this public ATP page.

Only publish forecasts from results and future fixture information that you have valid rights to use for Conquerors' intended public purpose.

## Operations

No live ATP scraper, prediction refresher, new paid API, scheduled workflow or access token is introduced. No football data or football pipeline is changed. The ATP view will render only after a separate, approved and genuine ATP snapshot is supplied. For the time being the page is a truthful preparation/status view.

Match results are winner-only. Set scores, in-play predictions and market profitability are not promised.
