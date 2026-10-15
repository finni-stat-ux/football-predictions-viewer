"""Read-only viewer. Reads published snapshots only; no admin imports or functions."""
from pathlib import Path
import pandas as pd
import streamlit as st
from cloud_refresh_ui import show_cloud_refresh
ROOT=Path(__file__).resolve().parent
PUB=ROOT/'published'
st.set_page_config(page_title='Conquerors Venture Predictions',layout='wide')
# Conquerors Venture branded header
st.markdown(
    """
    <style>
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
st.caption('Read-only · EPL and Championship · 90-minute results · probabilities are estimates')
@st.cache_data(ttl=60)
def read(name):
    p=PUB/name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()
p=read('predictions.csv');scores=read('top_scores.csv');metrics=read('model_performance.csv')
if p.empty:
    st.info('No predictions published yet. Ask the admin to generate and publish a snapshot.');st.stop()
st.caption('Last published (UTC): '+str(p.published_at_utc.iloc[0]))
league=st.selectbox('Competition',sorted(p.competition.unique()))
filtered=p[p.competition==league]
options=filtered[['fixture_id','date','HomeTeam','AwayTeam']].drop_duplicates()
labels={r.fixture_id:f'{r.date} · {r.HomeTeam} vs {r.AwayTeam}' for _,r in options.iterrows()}
chosen=st.selectbox('Fixture',options.fixture_id.tolist(),format_func=lambda x:labels[x])
view=filtered[filtered.fixture_id==chosen]
st.subheader('Model comparison')
cols=['model','p_home_win','p_draw','p_away_win','expected_home_goals','expected_away_goals','p_over_2_5','p_btts','most_likely_score']
st.dataframe(view[cols],hide_index=True,use_container_width=True)
model=st.selectbox('Score probabilities', ['Hybrid','Dixon-Coles','XGBoost'])
score=scores[(scores.fixture_id==chosen)&(scores.model==model)].sort_values('rank')
if not score.empty:
    st.bar_chart(score.set_index('score')['probability']);st.dataframe(score[['rank','score','probability']],hide_index=True)
with st.expander('Historical backtest performance'):
    if metrics.empty:st.info('Performance snapshot unavailable.')
    else:st.dataframe(metrics,hide_index=True,use_container_width=True)
st.caption('Forecasts may become stale as results change. Updates are initiated through the private GitHub workflow. No betting guarantees.')
