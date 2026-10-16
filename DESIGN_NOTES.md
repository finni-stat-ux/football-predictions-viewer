# Readability and mobile update — 2026-10-16

Applied the relevant principles from https://www.canva.com/learn/20-web-design-principles-follow/: readable typography, consistent spacing, clear hierarchy, a restrained colour palette, fewer competing choices and layouts designed for desktop and mobile.

The primary flow is competition → fixture → Hybrid pick → score probabilities → recent player xG. Detailed model comparisons, historical backtests and refresh controls are still available in expandable sections. The production 50/50 model and its probability snapshots are unchanged.

The score table contains exactly the five published score rows, centred consistently, without the fixed-height dataframe's empty rows. The chart remains a static SVG without zoom, pan or fullscreen controls. At widths up to 680px, the chart and table stack and a compact SVG keeps labels readable. Team probability tiles stay together; player panels use one column. On desktop, score views and team player panels each use two columns.

Historical player cards show three positive recorded-xG leaders per team over the latest five canonical league matches, including minutes, appearances and source dates. They are not forecasts of individual xG, confirmed lineups or model inputs. The published snapshot currently covers all 20 English Premier League teams and 22 Championship teams. Lincoln and West Ham lack a complete five-match player-data window because one provider match was incomplete. A clear unavailable state replaces obsolete or mismatched data.

Validation: 13 Streamlit/unit tests pass. Headless browser layout checks passed at 360, 390, 430 and 1440 pixels: no page-level horizontal overflow, five score rows, six player rows for the EPL sample, stacked chart/table on phones and adjacent chart/table on desktop. QA used verified cached crest images for the local browser's CDN requests; public-site crest loading is checked separately. Player-form generation is reproducible in the engine; no automatic player-data refresh schedule has been enabled. Identity and freshness checks suppress mismatched snapshots after later prediction refreshes.
