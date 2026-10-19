"""Dated official round programmes, separate from confirmed player fixtures."""
import json
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


def read_programme(root):
    try:
        data=json.loads((Path(root)/'published'/'atp_programme.json').read_text())
        if data.get('schema_version')!=1 or data.get('status')!='provisional_tournament_programme':return []
        rows=data['events']
        for row in rows:
            stamp=datetime.fromisoformat(row['programme_start_local'])
            if stamp.tzinfo is None or stamp.date().isoformat()!=row['venue_date']:return []
            if urlsplit(row['source_url']).scheme!='https':return []
            ZoneInfo(row['venue_timezone'])
        return rows
    except (OSError,ValueError,KeyError,TypeError):return []


def programme_for(rows,date,tournament='All tournaments'):
    return [row for row in rows if row['venue_date']==date and (tournament=='All tournaments' or row['tournament']==tournament)]


def programme_html(row):
    from tennis_design import tournament_mark
    start=datetime.fromisoformat(row['programme_start_local'])
    sydney=start.astimezone(ZoneInfo('Australia/Sydney'))
    return f'<article class="atp-card"><div class="atp-card-top">{tournament_mark(row["tournament"])}<div><span>{escape(row["tournament"])}</span><small>Tournament programme · Provisional</small></div></div><div class="atp-player">{escape(row["round"])}</div><p>Players to be confirmed</p><small>Venue date: {escape(start.strftime("%a %d %b"))}<br>{escape(row["time_basis"])}: {escape(start.strftime("%I:%M %p"))} local<br>Sydney: {escape(sydney.strftime("%a %d %b, %I:%M %p"))}</small><div class="atp-pending"><strong>Prediction pending</strong><span>Available after the player matchup is confirmed and a model forecast is generated.</span></div><p><a href="{escape(row["source_url"],quote=True)}" target="_blank" rel="noopener noreferrer">Official programme</a></p></article>'
