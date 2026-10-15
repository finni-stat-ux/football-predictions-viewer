# Viewer-only package

This ZIP contains only read-only dashboard code and published prediction snapshots. No admin controls, raw match data, API credentials or model training code.

On Windows, in the extracted viewer folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements_viewer.txt
.\.venv\Scripts\python.exe -m streamlit run viewer_dashboard.py
```

The viewer runs locally and will **not** update until you send a newly generated viewer package. A private hosted viewer requires additional deployment and access control; a read-only app alone is not authentication. Confirm permission to share derived predictions before distributing.
