"""Read-only viewer. Reads published snapshots only; no admin imports or functions."""
from pathlib import Path
import json
from html import escape
import pandas as pd
import streamlit as st
from viewer_display import match_pick, display_table, OUTCOMES, team_badge, winner_team, score_chart_svg
from cloud_refresh_ui import show_cloud_refresh
ROOT=Path(__file__).resolve().parent
PUB=ROOT/'published'
TEAM_LOGOS=json.loads((ROOT/'assets'/'team_logos.json').read_text())
st.set_page_config(page_title='Conquerors Venture Predictions',layout='wide')
# Conquerors Venture branded header
st.markdown(
    """
    <style>
    [data-testid="stImage"] img { background: white; padding: 12px; border-radius: 12px; }
    .cv-brand {
        margin-bottom: 1.4rem;
    }

    .cv-brand-title {
        font-family: inherit;
        font-size: clamp(2rem, 3.2vw, 2.75rem);
        font-weight: 700;
        line-height: 1.2;
        letter-spacing: -0.025em;
        color: inherit;
        margin: 0 0 0.65rem 0;
    }

    .cv-brand-signature {
        display: inline-flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.8rem;
    }

    .cv-formula {
        display: inline-block;
        padding: 0.55rem 0.85rem;
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 0.65rem;
        background: rgba(128,128,128,0.055);
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(0.95rem, 1.5vw, 1.2rem);
        font-weight: 500;
        line-height: 1.6;
        color: inherit;
    }

    .cv-formula sub {
        font-size: 0.65em;
    }

    .cv-brand-label {
        font-family: inherit;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        color: #808894;
    }

    @media (max-width: 640px) {
        .cv-formula {
            font-size: 0.9rem;
        }
    }
    </style>

    <div class="cv-brand">
        <h1 class="cv-brand-title">
            Conquerors Venture Predictions
        </h1>
        <div class="cv-brand-signature">
            <div class="cv-formula">
                P<sub>Hybrid</sub>(h,a)
                = &frac12;P<sub>DC</sub>(h,a)
                + &frac12;P<sub>XGB</sub>(h,a)
            </div>
            <span class="cv-brand-label">
                HYBRID PREDICTION ENGINE
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

show_cloud_refresh()
if st.button('Refresh displayed predictions',help='Reload the latest published snapshot; does not retrain models'):
    st.cache_data.clear()
    st.rerun()
st.caption('Read-only · English Premier League and Championship · 90-minute results · probabilities are estimates')
@st.cache_data(ttl=60)
def read(name):
    p=PUB/name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()
p=read('predictions.csv');scores=read('top_scores.csv');metrics=read('model_performance.csv')
if p.empty:
    st.info('No predictions published yet. Ask the admin to generate and publish a snapshot.');st.stop()
st.caption('Last published (UTC): '+str(p.published_at_utc.iloc[0]))
competition_names = {'EPL': 'English Premier League', 'Championship': 'EFL Championship'}
league=st.selectbox('Competition',sorted(p.competition.unique()),format_func=lambda value: competition_names.get(value,value))
competition_assets = {'EPL': 'premier-league.png', 'Championship': 'championship.png'}
logo, heading = st.columns([1, 6])
with logo:
    asset = ROOT / 'assets' / competition_assets.get(league, '')
    if asset.is_file():
        st.image(str(asset), width=100)
with heading:
    st.subheader(competition_names.get(league, league))
    st.caption('Match forecasts · Full-time result after 90 minutes')
filtered=p[p.competition==league]
options=filtered[['fixture_id','date','HomeTeam','AwayTeam']].drop_duplicates()
labels={r.fixture_id:f'{r.date} · {r.HomeTeam} vs {r.AwayTeam}' for _,r in options.iterrows()}
chosen=st.selectbox('Fixture',options.fixture_id.tolist(),format_func=lambda x:labels[x])
view=filtered[filtered.fixture_id==chosen]
fixture = view.iloc[0]
st.subheader(f"{fixture.HomeTeam} vs {fixture.AwayTeam}")
hybrid = view[view.model == 'Hybrid']
if len(hybrid) == 1:
    row = hybrid.iloc[0]
    try:
        pick, probability = match_pick(row)
        with st.container(border=True):
            st.caption('HYBRID MATCH PICK')
            winner = winner_team(row)
            badge = team_badge(winner, TEAM_LOGOS, 48) if winner else ''
            st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin:8px 0 16px">{badge}<h3 style="margin:0;padding:0">{escape(pick)}</h3></div>', unsafe_allow_html=True)
            st.write(f"**{probability:.1%} estimated probability**")
            st.caption('Most likely single result from the 50/50 hybrid. Other outcomes remain possible.')
            home, draw, away = st.columns(3)
            for column, label, key in zip((home, draw, away), (f'{row.HomeTeam} win', 'Draw', f'{row.AwayTeam} win'), OUTCOMES):
                with column:
                    team = row.HomeTeam if key == 'p_home_win' else row.AwayTeam if key == 'p_away_win' else None
                    badge = team_badge(team, TEAM_LOGOS) if team else ''
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;min-height:44px">{badge}<span>{escape(label)}</span></div>', unsafe_allow_html=True)
                    st.metric(label, f'{row[key]:.1%}', label_visibility='collapsed')
    except ValueError:
        st.info('Match pick unavailable for this fixture.')
st.subheader('Match probabilities by model')
cols=['model','p_home_win','p_draw','p_away_win','expected_home_goals','expected_away_goals','p_over_2_5','p_btts','most_likely_score']
st.dataframe(display_table(view[cols]),hide_index=True,use_container_width=True,column_config={name: st.column_config.NumberColumn(format='%.1f%%') for name in ['Home win (%)','Draw (%)','Away win (%)','Over 2.5 goals (%)','Both teams score (%)']})
model=st.selectbox('Score probabilities', ['Hybrid','Dixon-Coles','XGBoost'])
score=scores[(scores.fixture_id==chosen)&(scores.model==model)].sort_values('rank')
if not score.empty:
    chart_column, table_column = st.columns([3, 2])
    with chart_column:
        st.markdown(score_chart_svg(score), unsafe_allow_html=True)
    with table_column:
        st.dataframe(display_table(score[['rank','score','probability']]),hide_index=True,use_container_width=True,height=300,column_config={'Probability (%)': st.column_config.NumberColumn(format='%.1f%%')})
with st.expander('Historical backtest performance'):
    if metrics.empty:st.info('Performance snapshot unavailable.')
    else:
        st.caption('Lower log loss and Brier scores are better; higher accuracy is better.')
        st.dataframe(display_table(metrics),hide_index=True,use_container_width=True)
st.caption('Forecasts may become stale as results change. Updates are initiated through the private GitHub workflow. No betting guarantees.')

st.caption('Competition logos identify the leagues covered. All trademarks belong to their respective owners; no affiliation or endorsement is implied.')
