from pathlib import Path
from tennis_programme import read_programme,programme_for,programme_html


def test_official_programme_is_dated_and_does_not_invent_matchups():
    root=Path(__file__).resolve().parents[1]
    rows=read_programme(root)
    finals=programme_for(rows,'2026-10-25','European Open - Brussels')
    assert len(finals)==1
    html=programme_html(finals[0])
    assert 'Mon 26 Oct, 02:30 AM' in html
    assert 'Players to be confirmed' in html and 'Prediction pending' in html
    assert not programme_for(rows,'2026-10-30')
