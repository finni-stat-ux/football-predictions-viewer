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
