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
        assert any('HYBRID MATCH PICK' in x.value for x in app.markdown)
        assert any('cv-outcomes' in x.value for x in app.markdown)

def test_crests_cover_published_teams_and_winner_is_not_draw():
    import json
    from pathlib import Path
    from viewer_display import team_badge, winner_team
    root=Path(__file__).resolve().parents[1]
    logos=json.loads((root/'assets/team_logos.json').read_text())
    predictions=pd.read_csv(root/'published/predictions.csv')
    assert (set(predictions.HomeTeam)|set(predictions.AwayTeam)) <= logos.keys()
    assert winner_team(row((.6,.2,.2))) == 'Arsenal'
    assert winner_team(row((.2,.5,.3))) is None
    assert winner_team(row((.4,.4,.2))) is None
    assert 'Arsenal crest' in team_badge('Arsenal',logos)
    assert team_badge('Unknown club',logos) == ''

def test_score_chart_is_static_and_keeps_score_order():
    from viewer_display import score_chart_svg
    svg=score_chart_svg(pd.DataFrame([dict(score='1-0',probability=.2),dict(score='0-0',probability=.1)]))
    assert 'pointer-events:none' in svg
    assert '<script' not in svg
    assert '20.0%' in svg and '10.0%' in svg
    assert svg.index('1-0') < svg.index('0-0')
    assert score_chart_svg(pd.DataFrame()) == ''

def test_score_table_has_no_empty_rows():
    from viewer_display import score_table_html
    scores=pd.DataFrame([dict(rank=1,score='1-1',probability=.119),dict(rank=2,score='1-0',probability=.101)])
    html=score_table_html(scores)
    assert html.count('<tr>')==3
    assert '11.9%' in html and '10.1%' in html
    assert '<th scope="col">Score</th>' in html


def test_player_form_rejects_old_and_mismatched_fixture():
    from viewer_display import fixture_player_form
    fixture={'fixture_id':'f','date':'2026-10-17','competition':'EPL','HomeTeam':'Home','AwayTeam':'Away'}
    record={k:v for k,v in fixture.items() if k!='fixture_id'}
    record['teams']={'Home':{'status':'available','source_through':'2026-10-12','players':[]}}
    snapshot={'schema_version':1,'generated_at_utc':'2026-10-16T00:00:00Z','fixtures':{'f':record}}
    assert 'Home' in fixture_player_form(snapshot,fixture,now='2026-10-16')
    assert fixture_player_form(snapshot,{**fixture,'HomeTeam':'Other'},now='2026-10-16')=={}
    assert fixture_player_form(snapshot,fixture,now='2026-12-16')=={}
