
"""Password-protected GitHub Actions refresh controls for Streamlit."""

from contextlib import nullcontext
import hmac
import threading
import time

import requests
import streamlit as st

_AUTH_LOCK = threading.Lock()
_FAILED_ATTEMPTS = []
_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = 900


def login_attempt_allowed():
    """Apply a process-wide limit of 10 failed attempts per 15 minutes."""
    now = time.monotonic()

    with _AUTH_LOCK:
        _FAILED_ATTEMPTS[:] = [
            attempt
            for attempt in _FAILED_ATTEMPTS
            if now - attempt < _WINDOW_SECONDS
        ]
        return len(_FAILED_ATTEMPTS) < _MAX_ATTEMPTS


def record_failed_login():
    with _AUTH_LOCK:
        _FAILED_ATTEMPTS.append(time.monotonic())

REPO = "finni-stat-ux/conquerors-venture-engine"
WORKFLOW = "refresh.yml"
API = f"https://api.github.com/repos/{REPO}"


def show_cloud_refresh(*, embedded: bool = False, atp: bool = False):
    workflow = "atp-fixtures.yml" if atp else WORKFLOW
    panel_title = "Refresh ATP fixtures" if atp else "Cloud Prediction Refresh"
    with (nullcontext() if embedded else st.expander(panel_title)):
        st.caption(
            ("Update ATP fixtures for today and the following six UTC dates. "
             "The refresh runs in the cloud and publishes to this website. "
             "Matches appear as the provider releases the draw and schedule.") if atp else
            "Trigger a full football results and prediction refresh "
            "in GitHub Actions. Your computer does not need to be running."
        )

        try:
            password = st.secrets["REFRESH_PASSWORD"]
            token = st.secrets["GITHUB_REFRESH_TOKEN"]
        except (KeyError, FileNotFoundError):
            st.error("Cloud refresh is not configured.")
            return

        if "refresh_failed_attempts" not in st.session_state:
            st.session_state["refresh_failed_attempts"] = 0

        if st.session_state["refresh_failed_attempts"] >= 5:
            st.error(
                "Too many incorrect password attempts in this session."
            )
            return

        if not st.session_state.get("refresh_authenticated", False):
            if not login_attempt_allowed():
                st.error(
                    "Cloud refresh login is temporarily unavailable. "
                    "Please try again in 15 minutes."
                )
                return

        entered = st.text_input(
            "Refresh access password",
            type="password",
            key="cloud_refresh_password",
        )

        if not st.session_state.get("refresh_authenticated", False):
            if not st.button("Log in to Cloud Refresh"):
                return

            if not entered or not hmac.compare_digest(entered, password):
                st.session_state["refresh_failed_attempts"] += 1
                record_failed_login()
                st.error("Incorrect password.")
                return

            st.session_state["refresh_failed_attempts"] = 0
            st.session_state["refresh_authenticated"] = True

        st.success("Refresh access granted.")
        if st.button("Log out of Cloud Refresh"):
            st.session_state["refresh_authenticated"] = False
            st.session_state["cloud_refresh_password"] = ""
            st.rerun()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if st.button("Refresh ATP fixtures — next 7 days" if atp else "Run Full Prediction Refresh", type="primary"):
            try:
                # Check whether a refresh is already running.
                runs_response = requests.get(
                    f"{API}/actions/workflows/{workflow}/runs",
                    headers=headers,
                    params={"per_page": 20},
                    timeout=20,
                )
                runs_response.raise_for_status()

                active = [
                    run for run in runs_response.json().get("workflow_runs", [])
                    if run.get("status") in ("queued", "in_progress", "waiting", "pending", "requested")
                ]

                if active:
                    st.warning(
                        "A refresh is already queued or running. "
                        "Please wait for it to finish."
                    )
                    return

                # Trigger the existing cloud workflow.
                response = requests.post(
                    f"{API}/actions/workflows/{workflow}/dispatches",
                    headers=headers,
                    json={"ref": "main"},
                    timeout=20,
                )
                response.raise_for_status()

                st.success(
                    "GitHub accepted the refresh request. " +
                    ("ATP fixtures will update after the workflow completes." if atp else
                     "Predictions will update after the workflow completes.")
                )
                st.info(
                    ("Reload this page after the workflow finishes to see updated fixtures. "
                     "The free request budget limits how often a refresh can run.") if atp else
                    "The refresh runs in the cloud. "
                    "Check back later and use 'Refresh displayed predictions' "
                    "to load the latest published results."
                )

            except requests.RequestException:
                st.error(
                    "Unable to confirm the refresh request. "
                    "Ask the administrator to check GitHub Actions."
                )
