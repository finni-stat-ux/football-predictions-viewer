import copy
from test_tennis_design import fixture,forecast
from tennis_design import prediction_for,pick_html
from tennis_set_scores import add_set_pick


def sample():
    row=fixture();row['rank_id']=2
    score={'fixture_id':42,'kickoff_utc':row['start_time_utc'],'event_name':row['tournament'],'surface':'Hard',
           'player_a_id':1,'player_b_id':2,'player_a_name':row['player_a_name'],'player_b_name':row['player_b_name'],
           'p_a_2_0':.4,'p_a_2_1':.24,'p_b_2_0':.2,'p_b_2_1':.16}
    return row,score


def test_sets_attach_only_to_exact_fixture_and_winner_marginals():
    row,s=sample();pick=prediction_for(row,forecast())
    result=add_set_pick(row,pick,{'42':s})
    assert result['set_pick']['score']=='2–0'
    assert '40.0%' in pick_html(row,result) and 'Experimental' in pick_html(row,result)
    for field,value in [('player_a_id',999),('p_a_2_0',.5),('kickoff_utc','2026-10-22T12:00:00Z')]:
        bad=copy.deepcopy(s);bad[field]=value
        assert 'set_pick' not in add_set_pick(row,pick,{'42':bad})
    row['rank_id']=4
    assert 'set_pick' not in add_set_pick(row,pick,{'42':s})


def test_sets_never_create_winner_without_approved_forecast():
    row,s=sample()
    assert add_set_pick(row,None,{'42':s}) is None
