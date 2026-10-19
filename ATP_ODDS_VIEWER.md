# Read-only ATP fixtures and The Odds API market reference

This public Streamlit viewer **never owns or calls an API key**, and no visitor interaction is billable. The existing football screen, football models and refresh controls are not modified.

- ATP Men’s Singles has a separate **Upcoming ATP fixtures and market reference** section.
- Without a real `published/atp_odds_snapshot.json`, it states that the provider's fixture list is not yet published. It does not fabricate players, matches, odds or ATP Hybrid predictions.
- If the optional snapshot is approved, the section shows the upcoming ATP fixtures (Sydney start times) and, where valid and fresh, the median **bookmaker-implied** match-winner probabilities with each bookmaker's margin removed.
- Odds older than six hours are hidden; kickoff dates, timestamps, player identities and probability totals are checked.
- `Hybrid vs market` percentage-point comparison is only displayed for a separate, vetted ATP Hybrid forecast **with exactly matching provider event ID, both player names and UTC start time**. This is a reference difference, not demonstrated value or a betting recommendation.
- The original `tennis_viewer.py` still requires permission, a real 200-plus match holdout and an approved ATP publication before any model forecasts become visible.

## Getting a snapshot on the site

1. Owner creates a free The Odds API key *outside the public repo*, only in the private engine environment.
2. Run the private, **manual, 0-credit** `python -m tennis_atp.odds_feed` events collector; with explicit `--sport ... --with-odds`, one additional odds request can be made under a guarded 50-credit monthly local budget.
3. **Review** the generated `output/atp_odds_snapshot.json` for rights, data quality, freshness and no credential contents.
4. Publish the **reduced JSON only** to this repository as `published/atp_odds_snapshot.json`. Do not commit the raw HTTP feed or secret environment variables.
5. Streamlit loads the static snapshot. Viewers do not spend API quota. Snapshots require intentional/manual updates; there is no automated feed or scheduled job in this phase.

See private engine `ATP_ODDS_API_INTEGRATION.md` for details and Windows PowerShell instructions.

Provider sources: [Tennis markets](https://the-odds-api.com/sports/tennis-odds.html), [API v4](https://the-odds-api.com/liveapi/guides/v4/), [terms](https://the-odds-api.com/terms-and-conditions.html).

**Important:** Market data is *not* independent ATP Hybrid output. We still need an authorised historical match-and-serve dataset for real tennis model validation.
