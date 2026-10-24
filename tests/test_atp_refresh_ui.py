from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def test_atp_button_dispatches_only_atp_workflow():
    source = '''
import streamlit as st
from cloud_refresh_ui import show_cloud_refresh
st.session_state["refresh_authenticated"] = True
show_cloud_refresh(atp=True)
'''
    app = AppTest.from_string(source)
    app.secrets["REFRESH_PASSWORD"] = "test-password"
    app.secrets["GITHUB_REFRESH_TOKEN"] = "test-token"
    with patch("cloud_refresh_ui.requests.get") as get, patch("cloud_refresh_ui.requests.post") as post:
        get.return_value.json.return_value = {"workflow_runs": []}
        app.run()
        next(b for b in app.button if b.label == "Refresh ATP predictions & results — next 7 days").click().run()
        assert not app.exception
        assert "/atp-fixtures.yml/dispatches" in post.call_args.args[0]
        assert post.call_args.kwargs["json"] == {"ref": "main"}
        assert any("ATP fixtures, eligible predictions and verified results will update" in x.value for x in app.success)


def test_atp_button_does_not_dispatch_while_active():
    app = AppTest.from_string('''
import streamlit as st
from cloud_refresh_ui import show_cloud_refresh
st.session_state["refresh_authenticated"] = True
show_cloud_refresh(atp=True)
''')
    app.secrets["REFRESH_PASSWORD"] = "test-password"
    app.secrets["GITHUB_REFRESH_TOKEN"] = "test-token"
    with patch("cloud_refresh_ui.requests.get") as get, patch("cloud_refresh_ui.requests.post") as post:
        get.return_value.json.return_value = {"workflow_runs": [{"status": "queued"}]}
        app.run()
        next(b for b in app.button if "next 7 days" in b.label).click().run()
        assert not app.exception and not post.called
        assert app.warning


def test_refresh_module_reload_preserves_failed_login_throttle():
    import importlib,cloud_refresh_ui
    before=list(cloud_refresh_ui._FAILED_ATTEMPTS)
    cloud_refresh_ui.record_failed_login()
    entries=cloud_refresh_ui._FAILED_ATTEMPTS
    importlib.reload(cloud_refresh_ui)
    assert cloud_refresh_ui._FAILED_ATTEMPTS is entries and len(entries)==len(before)+1
    entries[:]=before


def test_player_refresh_dispatches_dedicated_workflow_and_coexists_with_football():
    app=AppTest.from_string('''
import streamlit as st
from cloud_refresh_ui import show_cloud_refresh
st.session_state['refresh_authenticated']=True
show_cloud_refresh(players=True)
show_cloud_refresh()
''')
    app.secrets['REFRESH_PASSWORD']='test-password';app.secrets['GITHUB_REFRESH_TOKEN']='test-token'
    with patch('cloud_refresh_ui.requests.get') as get,patch('cloud_refresh_ui.requests.post') as post:
        get.return_value.json.return_value={'workflow_runs':[]}
        app.run()
        assert not app.exception
        next(b for b in app.button if b.label=='Refresh player xG — both leagues').click().run()
        assert not app.exception and '/refresh-player-xg.yml/dispatches' in post.call_args.args[0]
        assert post.call_args.kwargs['json']=={'ref':'main'}
