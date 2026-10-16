import json
import shutil
from pathlib import Path

import pandas as pd

from matrix_display import load_matrix,performance_summary

ROOT=Path(__file__).resolve().parents[1]


def test_matrix_snapshot_is_separate_and_covers_both_leagues():
    p,s,m,metadata=load_matrix(ROOT/'published')
    assert not p.empty and set(p.competition)=={'EPL','Championship'}
    assert set(p.model)=={'Matrix'} and metadata['experimental']
    assert len(s)==5*len(p)
    for league,expected in [('EPL',1140),('Championship',1656)]:
        summary=performance_summary(m,league)
        assert summary['matches']==expected
        assert 0<summary['1x2_log_loss']<2


def test_stale_or_corrupt_matrix_does_not_change_baseline(tmp_path):
    for p in (ROOT/'published').glob('*.csv'):shutil.copy(p,tmp_path/p.name)
    shutil.copy(ROOT/'published/matrix_metadata.json',tmp_path/'matrix_metadata.json')
    before=(tmp_path/'predictions.csv').read_bytes()
    metadata=json.loads((tmp_path/'matrix_metadata.json').read_text());metadata['baseline_predictions_sha256']='stale'
    (tmp_path/'matrix_metadata.json').write_text(json.dumps(metadata))
    assert load_matrix(tmp_path)[0].empty
    assert (tmp_path/'predictions.csv').read_bytes()==before
    shutil.copy(ROOT/'published/matrix_metadata.json',tmp_path/'matrix_metadata.json')
    p=pd.read_csv(tmp_path/'matrix_predictions.csv');p.loc[0,'HomeTeam']='Wrong fixture'
    p.to_csv(tmp_path/'matrix_predictions.csv',index=False)
    assert load_matrix(tmp_path)[0].empty


def test_matrix_selection_changes_pick_chart_and_own_measure_for_both_leagues():
    from streamlit.testing.v1 import AppTest
    for league in ('EPL','Championship'):
        app=AppTest.from_file(str(ROOT/'viewer_dashboard.py')).run()
        app.selectbox[0].select(league).run()
        assert app.selectbox[1].value=='Hybrid'
        app.selectbox[1].select('Matrix').run()
        assert not app.exception
        assert any('MATRIX MATCH PICK' in x.value for x in app.markdown)
        assert len(app.metric)==3
        assert any('Matrix result log loss' in x.label for x in app.metric)
        assert any('cv-score-grid' in x.value for x in app.markdown)
        app.selectbox[1].select('Hybrid').run()
        assert not app.exception
        assert any('HYBRID MATCH PICK' in x.value for x in app.markdown)
