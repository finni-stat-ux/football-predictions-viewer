"""Validate optional set-total forecasts against exact approved winner fixtures."""
import json
import math
from pathlib import Path
import pandas as pd

FIELDS=('p_a_2_0','p_a_2_1','p_b_2_0','p_b_2_1')


def read_set_scores(root):
    try:
        data=json.loads((Path(root)/'published'/'atp_set_scores.json').read_text())
        if data.get('schema_version')!=1 or data.get('experimental') is not True:return {}
        evaluation=data.get('evaluation',[])
        if {r['year'] for r in evaluation}!={2024,2025}:return {}
        if any(r['matches']<200 or not math.isfinite(r['conditional_log_loss']) for r in evaluation):return {}
        events=data['events']
        if len({r['fixture_id'] for r in events})!=len(events):return {}
        return {str(r['fixture_id']):r for r in events}
    except (OSError,ValueError,KeyError,TypeError):return {}


def add_set_pick(row,pick,scores):
    if pick is None:return pick
    score=scores.get(str(row['fixture_id']))
    if score is None or row['rank_id'] not in (2,3):return pick
    try:
        if pd.Timestamp(score['kickoff_utc'])!=pd.Timestamp(row['start_time_utc']) or score['event_name']!=row['tournament']:return pick
        if score['surface']!=('Hard' if row['surface']=='Indoor hard' else row['surface']):return pick
        for side in 'ab':
            if str(score[f'player_{side}_id'])!=str(row[f'player_{side}_id']) or score[f'player_{side}_name']!=row[f'player_{side}_name']:return pick
        values=[float(score[f]) for f in FIELDS]
        if not all(math.isfinite(v) and 0<=v<=1 for v in values) or abs(sum(values)-1)>1e-6:return pick
        if abs(sum(values[:2])-pick['p_a'])>1e-6 or abs(sum(values[2:])-pick['p_b'])>1e-6:return pick
        outcomes=[{'winner':row[f'player_{side}_name'],'score':label,'p':v} for side,label,v in zip(('a','a','b','b'),('2–0','2–1','2–0','2–1'),values)]
        side=pick['side']
        selected=outcomes[:2] if side=='a' else outcomes[2:] if side=='b' else []
        return dict(pick,set_outcomes=outcomes,set_pick=max(selected,key=lambda r:r['p']) if selected else None)
    except (ValueError,KeyError,TypeError):return pick
