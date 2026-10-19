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
