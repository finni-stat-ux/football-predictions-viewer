# Readability and mobile update — 2026-10-16

Applied the relevant principles from https://www.canva.com/learn/20-web-design-principles-follow/: readable typography, consistent spacing, clear hierarchy, a restrained colour palette, fewer competing choices and layouts designed for desktop and mobile.

The primary flow is competition → fixture → Hybrid pick → score probabilities → recent player xG. Detailed model comparisons, historical backtests and refresh controls are still available in expandable sections. The production 50/50 model and its probability snapshots are unchanged.

The score table contains exactly the five published score rows, centred consistently, without the fixed-height dataframe's empty rows. The chart remains a static SVG without zoom, pan or fullscreen controls. At widths up to 680px, the chart and table stack and a compact SVG keeps labels readable. Team probability tiles stay together; player panels use one column. On desktop, score views and team player panels each use two columns.

Historical player cards show three positive recorded-xG leaders per team over the latest five canonical league matches, including minutes, appearances and source dates. They are not forecasts of individual xG, confirmed lineups or model inputs. The published snapshot currently covers all 20 English Premier League teams and 22 Championship teams. Lincoln and West Ham lack a complete five-match player-data window because one provider match was incomplete. A clear unavailable state replaces obsolete or mismatched data.

Validation: 13 Streamlit/unit tests pass. Headless browser layout checks passed at 360, 390, 430 and 1440 pixels: no page-level horizontal overflow, five score rows, six player rows for the EPL sample, stacked chart/table on phones and adjacent chart/table on desktop. QA used verified cached crest images for the local browser's CDN requests; public-site crest loading is checked separately. Player-form generation is reproducible in the engine; no automatic player-data refresh schedule has been enabled. Identity and freshness checks suppress mismatched snapshots after later prediction refreshes.

## Upcoming match tiles — 2026-10-16

Fixture selection uses fixed native buttons with both club crests and kickoff times in Sydney time. The row scrolls within its own container on phones without widening the page. Competition and model selectors disable typing with `filter_mode=None`; Streamlit 1.66 or newer is required. There is no editable fixture selector.

A separate read-only schedule export matched all 45 published fixtures. Started matches and non-scheduled statuses are excluded; unknown same-day kickoff times are hidden conservatively. Clock filtering is checked each minute while the page is open. Provider status metadata remains a snapshot, not a live status feed. Predictions and model probabilities are unchanged.

Validation: 15 viewer tests and 54 engine tests pass. Responsive checks before workspace cleanup passed at 360, 390, 430 and 1440px with no page-level horizontal overflow. Added tests cover started games, in-play statuses, unknown same-day kickoff times, Sydney time conversion and selection by a fixed match tile.
