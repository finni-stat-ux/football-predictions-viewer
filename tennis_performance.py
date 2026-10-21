"""Read-only performance from saved pre-match predictions and verified outcomes."""
import json
import math
from pathlib import Path
import pandas as pd


def read_performance(root):
    path=Path(root)/'published/atp_performance.json'
    if not path.exists():return None
    data=json.loads(path.read_text())
    if data.get('schema_version')!=1 or not isinstance(data.get('matches'),list):raise ValueError('Invalid performance report')
    if pd.Timestamp(data['generated_at_utc']).tzinfo is None:raise ValueError('Missing report timestamp')
    for row in data['matches']:
        if row.get('status') not in ('settled','awaiting_verified_result'):raise ValueError('Invalid result status')
        if row['status']=='settled':
            if not math.isfinite(row['brier']) or not 0<=row['brier']<=1 or not math.isfinite(row['log_loss']) or row['log_loss']<0:raise ValueError('Invalid probability score')
    return data


def show_performance(root):
    import streamlit as st
    st.subheader('ATP results & performance')
    st.caption('Tracks the first saved pre-match forecast for each fixture and model. Only verified completed results count; retirements and walkovers are excluded. This is live tracking, separate from historical model testing.')
    try:report=read_performance(root)
    except (ValueError,KeyError,TypeError,OSError):
        st.warning('Performance data did not pass validation.');return
    if not report:
        st.info('Performance tracking is starting. Results will appear after a cloud refresh verifies completed matches.');return
    summaries=report.get('summary',[])
    if not summaries:
        st.info('No saved forecasts have reached their start time yet.');return
    models=[r['model'] for r in summaries]
    preferred='ATP Hybrid' if 'ATP Hybrid' in models else models[0]
    model=st.selectbox('Performance model',models,index=models.index(preferred),key='atp_performance_model')
    selected=next(r for r in summaries if r['model']==model)
    cols=st.columns(3)
    cols[0].metric('Verified results',selected['settled'])
    cols[1].metric('Correct winner picks',f"{selected['accuracy']:.1%}" if selected.get('accuracy') is not None else 'Pending')
    cols[2].metric('Awaiting verified results',selected['pending'])
    if selected['settled']<30:st.caption('Small sample: early results are descriptive and do not establish model quality.')
    rows=[r for r in report['matches'] if r['model']==model]
    if not selected['settled']:st.info('No verified outcomes have been collected yet. A passed start time does not confirm that a match finished.')
    with st.expander('Weekly accuracy & probability calibration'):
        weekly=[r for r in report.get('weekly',[]) if r['model']==model]
        calibration=[r for r in report.get('calibration',[]) if r['model']==model]
        if weekly:st.dataframe(pd.DataFrame(weekly).drop(columns='model').rename(columns={'week_start':'Week starting','matches':'Matches','accuracy':'Winner accuracy'}),hide_index=True,use_container_width=True)
        if calibration:st.dataframe(pd.DataFrame(calibration).drop(columns='model').rename(columns={'band':'Prediction band','matches':'Matches','mean_probability':'Average predicted chance','actual_win_rate':'Actual win rate'}),hide_index=True,use_container_width=True)
        st.caption('Calibration compares the predicted favourite’s chance with its observed win rate. Brier score and log loss measure probability quality; lower is better.')
        if selected.get('brier') is not None:st.write(f"Brier score: {selected['brier']:.3f} · Log loss: {selected['log_loss']:.3f}")
    if rows:
        table=pd.DataFrame([{'Date (Sydney)':r['match_date'],'Match':r['player_a_name']+' vs '+r['player_b_name'],
                             'Original pick':r['predicted_winner'],'Probability':f"{r['confidence']:.1%}",
                             'Actual winner':r.get('actual_winner','Awaiting verified result'),
                             'Outcome':('Correct' if r.get('correct') is True else 'Incorrect' if r.get('correct') is False else 'No winner pick') if r['status']=='settled' else 'Pending'} for r in rows])
        st.dataframe(table.sort_values('Date (Sydney)',ascending=False),hide_index=True,use_container_width=True)
    if report.get('results_checked_at_utc'):
        st.caption('Results last checked: '+pd.Timestamp(report['results_checked_at_utc']).tz_convert('Australia/Sydney').strftime('%d %b %Y, %I:%M %p Sydney'))
    else:
        st.caption('Awaiting the first cloud result check. Use Refresh ATP predictions & results to collect verified outcomes.')
