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


def test_upcoming_filters_started_finished_and_unknown_same_day():
    from viewer_display import upcoming_fixtures
    now='2026-10-16T10:00:00Z'
    rows=[dict(fixture_id=str(i),date=date,competition='EPL',HomeTeam='Home',AwayTeam=f'Away{i}') for i,date in enumerate(['2026-10-15','2026-10-16','2026-10-16','2026-10-16','2026-10-17'])]
    fixtures={}
    for i,status,time in [(1,'TIMED','2026-10-16T09:00:00Z'),(2,'IN_PLAY','2026-10-16T12:00:00Z'),(3,'TIMED','2026-10-16T12:00:00Z')]:
        fixtures[str(i)]={**rows[i], 'kickoff_utc':time,'status':status}
    frame=pd.DataFrame(rows)
    result=upcoming_fixtures(frame,{'schema_version':1,'fixtures':fixtures},now=now)
    assert result.fixture_id.tolist()==['3','4']
    assert '23:00' in result.iloc[0].display_time
    assert upcoming_fixtures(frame,{},now=now).fixture_id.tolist()==['4']


def test_fixture_tiles_select_a_match_without_an_editable_fixture_box():
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'viewer_dashboard.py')).run()
    assert not app.exception
    assert [s.label for s in app.selectbox][:2]==['Competition','Prediction model']
    assert 'Historical competition' in [s.label for s in app.selectbox]
    assert not any(s.label == 'Editable fixture' for s in app.selectbox)
    tiles=[b for b in app.button if b.key and b.key.startswith('fixture_tile_')]
    assert len(tiles)>1
    assert 'crest' in tiles[1].label
    label=tiles[1].label
    tiles[1].click().run()
    assert not app.exception
    assert label in [b.label for b in app.button if b.proto.type=='primary']


def test_schedule_matches_fixture_identity_after_refresh_renumbers_ids():
    from viewer_display import upcoming_fixtures
    frame=pd.DataFrame([dict(
        fixture_id='FUTURE_5',date='2026-10-20',competition='Championship',
        HomeTeam='Wolves',AwayTeam='Portsmouth'
    )])
    old_record=dict(date='2026-10-20',competition='Championship',
                    HomeTeam='Wolves',AwayTeam='Portsmouth',
                    status='TIMED',kickoff_utc='2026-10-20T18:45:00+00:00')
    schedule=dict(schema_version=1,checked_at_utc='2026-10-16T09:38:15+00:00',
                  fixtures={'FUTURE_22':old_record})
    actual=upcoming_fixtures(frame,schedule,now='2026-10-18T02:41:20Z')
    assert actual.fixture_id.tolist()==['FUTURE_5']
    assert actual.iloc[0].display_time=='Wed 21 Oct · 05:45 Sydney'


def test_ambiguous_or_stale_schedule_does_not_invent_kickoff():
    from viewer_display import upcoming_fixtures
    frame=pd.DataFrame([dict(
        fixture_id='FUTURE_NEW',date='2026-10-20',competition='Championship',
        HomeTeam='Wolves',AwayTeam='Portsmouth'
    )])
    item=dict(date='2026-10-20',competition='Championship',
              HomeTeam='Wolves',AwayTeam='Portsmouth',
              status='TIMED',kickoff_utc='2026-10-20T18:45:00Z')
    base=dict(schema_version=1,checked_at_utc='2026-10-16T09:38:15Z',
              fixtures={'old':item})
    now='2026-10-18T02:41:20Z'
    duplicate={**base,'fixtures':{'old':item,'another':dict(item)}}
    assert 'time TBC' in upcoming_fixtures(frame,duplicate,now=now).iloc[0].display_time
    stale={**base,'checked_at_utc':'2026-10-10T00:00:00Z'}
    assert 'time TBC' in upcoming_fixtures(frame,stale,now=now).iloc[0].display_time
    other={**base,'fixtures':{'old':{**item,'AwayTeam':'Millwall'}}}
    assert 'time TBC' in upcoming_fixtures(frame,other,now=now).iloc[0].display_time


def test_player_form_recovers_exact_match_when_new_refresh_renumbers_fixtures():
    from viewer_display import fixture_player_form
    fixture = dict(fixture_id='FUTURE_5',date='2026-10-20',competition='Championship',
                   HomeTeam='Wolves',AwayTeam='Portsmouth')
    old_record = {
        'date': '2026-10-20', 'competition': 'Championship',
        'HomeTeam': 'Wolves', 'AwayTeam': 'Portsmouth',
        'teams': {
            'Wolves': {'status': 'available', 'players': [{'name': 'Fer López', 'xg': 2.15}],
                       'source_from': '2026-09-06', 'source_through': '2026-10-13'},
            'Portsmouth': {'status': 'available', 'players': [{'name': 'Adrian Segečić', 'xg': 1.47}],
                           'source_from': '2026-09-05', 'source_through': '2026-10-14'},
        },
    }
    snapshot = {
        'schema_version': 1, 'generated_at_utc': '2026-10-16T09:17:48Z',
        'max_age_days': 45, 'fixtures': {'FUTURE_22': old_record},
    }
    restored = fixture_player_form(snapshot, fixture, now='2026-10-18T03:08:00Z')
    assert restored['Wolves']['players'][0]['name'] == 'Fer López'
    assert restored['Portsmouth']['players'][0]['name'] == 'Adrian Segečić'


def test_player_form_remap_rejects_ambiguous_mismatched_and_outdated_snapshots():
    from viewer_display import fixture_player_form
    fixture = dict(fixture_id='new',date='2026-10-20',competition='Championship',
                   HomeTeam='Wolves',AwayTeam='Portsmouth')
    record = {k:fixture[k] for k in ('date','competition','HomeTeam','AwayTeam')}
    record['teams'] = {'Wolves': {'status':'available','players':[{'name':'Test player','xg': 1}],
                                 'source_through':'2026-10-13'}}
    original = {'schema_version': 1, 'generated_at_utc':'2026-10-16T09:17:48Z',
                'fixtures': {'old': record}}
    now='2026-10-18T03:08:00Z'
    assert fixture_player_form(original,fixture,now=now)
    # There must be precisely one matching fixture, not a guessed best match.
    duplicates = {**original,'fixtures':{'old':record,'other':dict(record)}}
    assert fixture_player_form(duplicates,fixture,now=now)=={}
    wrong_team={**original,'fixtures':{'old':{**record,'AwayTeam':'Cardiff'}}}
    assert fixture_player_form(wrong_team,fixture,now=now)=={}
    wrong_date={**original,'fixtures':{'old':{**record,'date':'2026-10-21'}}}
    assert fixture_player_form(wrong_date,fixture,now=now)=={}
    stale = {**original,'generated_at_utc':'2026-10-05T00:00:00Z'}
    assert fixture_player_form(stale,fixture,now=now)=={}
    future={**original,'generated_at_utc':'2026-10-20T00:00:00Z'}
    assert fixture_player_form(future,fixture,now=now)=={}
    # Never show data recorded on or after the scheduled match day.
    postmatch={**original,'fixtures':{'old':{**record,'teams':{
        'Wolves':{**record['teams']['Wolves'],'source_through':'2026-10-20'}}}}}
    assert fixture_player_form(postmatch,fixture,now=now)=={}


def test_published_player_form_recovery_after_fixture_id_rotation():
    """Use actual published archives, not just synthetic team names."""
    import json
    from pathlib import Path
    from viewer_display import fixture_player_form
    root = Path(__file__).resolve().parents[1]
    predictions = pd.read_csv(root / 'published' / 'predictions.csv')
    snapshot = json.loads((root / 'published' / 'player_form.json').read_text())
    for _, fixture in predictions[predictions.model.eq('Hybrid')].iterrows():
        exact = [
            record for record in snapshot['fixtures'].values()
            if all(str(record.get(name)) == str(fixture[name])
                   for name in ('date', 'competition', 'HomeTeam', 'AwayTeam'))
        ]
        if len(exact) != 1 or str(fixture.fixture_id) in snapshot['fixtures']:
            continue
        if not any(team.get('status') == 'available'
                   for team in exact[0].get('teams', {}).values()):
            continue
        generated = pd.Timestamp(snapshot['generated_at_utc'])
        check_at = generated + pd.Timedelta(days=2)
        matches = fixture_player_form(snapshot, fixture, now=check_at)
        assert matches, (
            'Published player xG should recover by the exact fixture identity '
            'even when old and new FUTURE IDs differ'
        )
        return
    pytest.skip('No renumbered, verifiable fixture in current published player archive')


def test_streamlit_entrypoint_reloads_player_display_module():
    """Prevent reintroducing cached helper functions on Streamlit Cloud."""
    from pathlib import Path
    code = (Path(__file__).resolve().parents[1] / 'viewer_dashboard.py').read_text()
    assert 'importlib.reload(viewer_display)' in code
