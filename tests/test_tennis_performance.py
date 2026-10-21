import json
import pytest
from tennis_performance import read_performance


def test_performance_does_not_invent_outcomes(tmp_path):
    assert read_performance(tmp_path) is None
    root=tmp_path/'published';root.mkdir()
    report=dict(schema_version=1,generated_at_utc='2026-10-21T02:00:00Z',matches=[dict(status='awaiting_verified_result')])
    (root/'atp_performance.json').write_text(json.dumps(report))
    assert read_performance(tmp_path)['matches'][0]['status']=='awaiting_verified_result'
    report['matches']=[dict(status='settled',brier=-1,log_loss=.5)]
    (root/'atp_performance.json').write_text(json.dumps(report))
    with pytest.raises(ValueError):read_performance(tmp_path)
