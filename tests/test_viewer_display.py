import pandas as pd
import pytest
from viewer_display import match_pick, display_table

def row(values):
    return dict(zip(('p_home_win','p_draw','p_away_win'),values),HomeTeam='Arsenal',AwayTeam='Liverpool')

@pytest.mark.parametrize('values,label', [((.6,.2,.2),'Arsenal to win'),((.2,.5,.3),'Draw'),((.2,.3,.5),'Liverpool to win'),((.4,.4,.2),'Too close to call')])
def test_pick(values,label):
    assert match_pick(row(values))[0] == label

@pytest.mark.parametrize('values',[(float('nan'),.2,.8),(.6,.6,.2),(-.1,.5,.6)])
def test_invalid_pick(values):
    with pytest.raises(ValueError): match_pick(row(values))

def test_display_does_not_change_snapshot():
    original=pd.DataFrame([dict(p_home_win=.45,expected_home_goals=1.7)])
    shown=display_table(original)
    assert shown['Home win (%)'][0] == 45
    assert shown['Home expected goals'][0] == 1.7
    assert original.p_home_win[0] == .45

def test_app_both_leagues():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'viewer_dashboard.py')).run()
    assert not app.exception
    for league in ('EPL','Championship'):
        app.selectbox[0].select(league).run()
        assert not app.exception
        assert any(x.value == 'HYBRID MATCH PICK' for x in app.caption)
        assert len(app.metric) == 3
