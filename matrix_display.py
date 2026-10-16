"""Validate optional Matrix snapshots; never alter the established forecasts."""
import hashlib
import io
import json

import numpy as np
import pandas as pd

KEYS=['fixture_id','date','competition','HomeTeam','AwayTeam']


def load_matrix(directory, baseline_bytes=None):
    empty=(pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),{})
    try:
        base_bytes=(directory/'predictions.csv').read_bytes() if baseline_bytes is None else baseline_bytes
        metadata=json.loads((directory/'matrix_metadata.json').read_text())
        if metadata.get('schema_version')!=1 or metadata.get('experimental') is not True or metadata.get('baseline_predictions_sha256')!=hashlib.sha256(base_bytes).hexdigest():return empty
        baseline=pd.read_csv(io.BytesIO(base_bytes))[KEYS].drop_duplicates()
        p=pd.read_csv(directory/'matrix_predictions.csv');s=pd.read_csv(directory/'matrix_top_scores.csv');m=pd.read_csv(directory/'matrix_performance.csv')
        if p.empty or not p.model.eq('Matrix').all() or p.fixture_id.duplicated().any():return empty
        joined=p[KEYS].merge(baseline,on=KEYS,how='inner',validate='one_to_one')
        if len(joined)!=len(p):return empty
        columns=['p_home_win','p_draw','p_away_win','p_over_2_5','p_btts']
        values=p[columns].to_numpy(float)
        if not np.isfinite(values).all() or ((values<0)|(values>1)).any() or not np.allclose(values[:,:3].sum(1),1,atol=1e-7):return empty
        goals=p[['expected_home_goals','expected_away_goals']].to_numpy(float)
        if not np.isfinite(goals).all() or (goals<0).any():return empty
        if not p.competition.isin(['EPL','Championship']).all():return empty
        if not s.model.eq('Matrix').all() or set(s.fixture_id)!=set(p.fixture_id):return empty
        if s.duplicated(['fixture_id','rank']).any() or not s.score.str.fullmatch(r'[0-8]-[0-8]').all():return empty
        if not np.isfinite(s.probability).all() or not s.probability.between(0,1).all():return empty
        for _,g in s.groupby('fixture_id'):
            if sorted(g['rank'])!=[1,2,3,4,5] or g.probability.sum()>1+1e-7:return empty
        if not m.model.isin(['Matrix','Hybrid']).all() or not m.competition.isin(['EPL','Championship']).all():return empty
        if m.duplicated(['season','competition','model']).any():return empty
        for league in p.competition.unique():
            perf=m[m.competition==league]
            if set(perf.model)!= {'Matrix','Hybrid'}:return empty
        for c in ['matches','1x2_log_loss','1x2_brier','1x2_accuracy','exact_score_log_loss']:
            if not np.isfinite(m[c]).all() or (m[c]<0).any():return empty
        return p,s,m,metadata
    except (OSError,ValueError,KeyError,TypeError,AttributeError):return empty


def performance_summary(metrics,league,model='Matrix'):
    rows=metrics[(metrics.competition==league)&(metrics.model==model)]
    if rows.empty:return None
    return dict(matches=int(rows.matches.sum()),**{c:float(np.average(rows[c],weights=rows.matches)) for c in ['1x2_log_loss','1x2_brier','1x2_accuracy','exact_score_log_loss']})
