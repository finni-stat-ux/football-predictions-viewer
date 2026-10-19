# ATP Tour fixtures from SportsAPI365

The ATP section reads a static `published/atp_fixtures.json` with strict field,
identity, competition and UTC timestamp validation. It displays upcoming men's
singles fixtures with tournament filtering, surface, round and Sydney start
times. Completed/start-passed fixtures are hidden. Partial and older snapshots
are labelled. No public interaction calls an external API or spends quota.

The initial owner-verified Lyon fixture is a partial snapshot from a live
SportsAPI365 Direct request. It is not a model prediction or complete schedule.
The engine's manual `tennis_atp.sportsapi_feed` collector produces the same
schema for a bounded date window. Only publish its reduced JSON; credentials
and quota ledgers stay outside the public repository.

The independent ATP Hybrid forecast validation and optional The Odds API
market section retain their existing behavior.


The password-protected **Refresh ATP fixtures** panel dispatches the private
engine's manual seven-day collection and publication workflow. Reuses the
existing refresh password/token. Provider credentials remain in private Actions
secrets. A shared daily cloud request ledger caps collection at 40 attempted
requests per UTC day. The button checks for queued/running ATP jobs and never
calls the provider from the public app. Reload after the cloud job finishes.


## Visual presentation

The ATP view shares the football page's purple accent, spacing, scrollable
match tiles and selected-match hierarchy. An original soccer ball and racket
mark identify the two sports. Tournament court badges are original identifiers,
not official tournament marks. Fixture cards collapse to one column on mobile.
Country flags use provider country codes only; refresh the cloud collector to
populate codes in older snapshots. No nationalities are inferred from names.

Each fixture has a winner panel. Actual picks are bound to approved forecasts
by fixture ID, both player IDs/names, tournament, surface and exact start time.
Missing forecasts display `Prediction pending` without invented probabilities.
The display prefers the validated ATP Hybrid, then a labelled component model.
No live ATP model forecast has been published as part of the design change.
