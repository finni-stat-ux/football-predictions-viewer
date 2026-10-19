"""ATP presentation helpers. Only supplied country codes and approved forecasts."""
import base64
from html import escape
from pathlib import Path

import pandas as pd

# IOC codes returned by the provider -> ISO 3166-1 alpha-2 for flag assets.
COUNTRIES = dict(AUS="au", AUT="at", ARG="ar", BEL="be", BIH="ba", BLR="by", BRA="br", BUL="bg", CAN="ca", CHI="cl", CHN="cn", COL="co", CRO="hr", CYP="cy", CZE="cz", DEN="dk", ECU="ec", EGY="eg", ESP="es", EST="ee", FIN="fi", FRA="fr", GBR="gb", GEO="ge", GER="de", GRE="gr", HKG="hk", HUN="hu", IND="in", INA="id", IRL="ie", ISR="il", ITA="it", JPN="jp", KAZ="kz", KOR="kr", LAT="lv", LTU="lt", LUX="lu", MAR="ma", MEX="mx", MNE="me", NED="nl", NOR="no", NZL="nz", PER="pe", POL="pl", POR="pt", ROU="ro", RSA="za", RUS="ru", SLO="si", SRB="rs", SUI="ch", SVK="sk", SWE="se", THA="th", TPE="tw", TUN="tn", TUR="tr", UAE="ae", UKR="ua", URU="uy", USA="us", UZB="uz", VEN="ve", VIE="vn")


def flag_url(code):
    iso = COUNTRIES.get(code)
    return f"https://flagcdn.com/w80/{iso}.png" if iso else None


def flag_html(code):
    url = flag_url(code)
    if url:
        return f'<img class="atp-flag" src="{url}" alt="{escape(code)} flag" title="{escape(code)}" loading="lazy">'
    return '<span class="atp-no-flag" title="Country not supplied" aria-label="Country unavailable">◉</span>'


def player_html(row, side):
    return flag_html(row.get(f"player_{side}_country")) + '<span>' + escape(row[f"player_{side}_name"]) + '</span>'


def tournament_mark(name):
    """Original court badge, not an official tournament logo."""
    city = next((city for city in ("Lyon", "Brussels", "Almaty", "Paris", "Melbourne", "London") if city.lower() in name.lower()), "ATP")
    initials = {"Lyon": "LY", "Brussels": "BR", "Almaty": "AL", "Paris": "PA", "Melbourne": "ME", "London": "LD"}.get(city, "T")
    color = {"Lyon": "#7856d8", "Brussels": "#137d77", "Almaty": "#285da5"}.get(city, "#7856d8")
    return f'<svg class="atp-mark" viewBox="0 0 64 64" role="img" aria-label="{escape(city)} tennis badge"><rect x="1" y="1" width="62" height="62" rx="16" fill="{color}"/><rect x="12" y="10" width="40" height="30" rx="2" fill="none" stroke="white" opacity=".75"/><path d="M12 25h40M20 10v30m24-30v30m-24-15h24M32 10v30" stroke="white" opacity=".75"/><text x="32" y="56" text-anchor="middle" fill="white" font-family="sans-serif" font-size="12" font-weight="700">{initials}</text></svg>'


def prediction_for(row, forecasts):
    """Bind an already-approved forecast to exact fixture/player identity."""
    required = {"fixture_id", "model", "kickoff_utc", "event_name", "surface", "player_a_id", "player_b_id", "player_a_name", "player_b_name", "p_player_a", "p_player_b"}
    if forecasts is None or forecasts.empty or not required.issubset(forecasts.columns):
        return None
    matches = forecasts.loc[forecasts.fixture_id.astype(str).eq(str(row["fixture_id"]))]
    for model in ("ATP Hybrid", "Surface Elo", "Serve/return"):
        candidates = matches.loc[matches.model.eq(model)]
        if len(candidates) != 1:
            continue
        p = candidates.iloc[0]
        if pd.Timestamp(p.kickoff_utc) != pd.Timestamp(row["start_time_utc"]) or p.event_name != row["tournament"]:
            continue
        if p.surface != ("Hard" if row["surface"] == "Indoor hard" else row["surface"]):
            continue
        a = (str(row["player_a_id"]), row["player_a_name"])
        b = (str(row["player_b_id"]), row["player_b_name"])
        pa = (str(p.player_a_id), p.player_a_name)
        pb = (str(p.player_b_id), p.player_b_name)
        if (pa, pb) == (a, b):
            probability = float(p.p_player_a)
        elif (pa, pb) == (b, a):
            probability = float(p.p_player_b)
        else:
            continue
        if not 0 <= probability <= 1 or abs(float(p.p_player_a) + float(p.p_player_b) - 1) > 1e-6:
            continue
        side = "a" if probability > .5 else "b" if probability < .5 else None
        return {"model": model, "p_a": probability, "p_b": 1-probability, "side": side,
                "winner": row[f"player_{side}_name"] if side else "Too close to call",
                "confidence": max(probability, 1-probability)}
    return None


def pick_html(row, pick, *, compact=False):
    if pick is None:
        return '<div class="atp-pending"><span class="atp-pick-label">PREDICTED WINNER</span><strong>Prediction pending</strong><span>A validated forecast is not available for this match yet.</span></div>'
    side = pick["side"]
    winner = flag_html(row.get(f"player_{side}_country")) if side else ""
    suffix = ' to win' if side else ''
    heading = escape(pick["winner"]) + suffix
    title = f'<div class="atp-winner">{winner}<strong>{heading}</strong></div>'
    sets=pick.get("set_pick")
    set_line=(f'<div class="atp-set-pick"><span>SET-SCORE ESTIMATE</span><strong>{escape(sets["winner"])} {escape(sets["score"])}</strong><small>{sets["p"]:.1%} probability of this exact set result · Experimental</small></div>' if sets else '')
    if compact:
        return f'<div class="atp-pick"><span class="atp-pick-label">PREDICTED WINNER · {escape(pick["model"])}</span>{title}<span>{pick["confidence"]:.1%} estimated probability</span>{set_line}</div>'
    return f'<div class="atp-pick"><span class="atp-pick-label">{escape(pick["model"]).upper()} MATCH PICK</span>{title}<p>{pick["confidence"]:.1%} estimated probability</p><div class="atp-prob-grid"><div>{player_html(row,"a")}<b>{pick["p_a"]:.1%}</b></div><div>{player_html(row,"b")}<b>{pick["p_b"]:.1%}</b></div></div><div class="atp-prob-bar" aria-label="Player A {pick["p_a"]:.1%}, Player B {pick["p_b"]:.1%}"><span style="width:{100*pick["p_a"]:.4f}%"></span></div>{set_line}<small>Match winner · Probabilities are estimates, not guarantees.</small></div>'


def card_html(row, time_label, pick, selected=False):
    state = " atp-card-selected" if selected else ""
    return f'<article class="atp-card{state}" aria-label="{escape(row["player_a_name"])} versus {escape(row["player_b_name"])}"><div class="atp-card-top">{tournament_mark(row["tournament"])}<div><span>{escape(row["tournament"])}</span><small>{escape(row["round"])} · {escape(row["surface"])}</small></div></div><div class="atp-player">{player_html(row,"a")}</div><div class="atp-versus">VS</div><div class="atp-player">{player_html(row,"b")}</div><div class="atp-start">{escape(time_label)} Sydney</div>{pick_html(row,pick,compact=True)}</article>'


def tile_label(row, time_label):
    def player(side):
        code = row.get(f"player_{side}_country")
        flag = f'![{code}]({flag_url(code)}) ' if flag_url(code) else ''
        return flag + row[f"player_{side}_name"]
    return f'{player("a")}\nvs {player("b")}\n{time_label} Sydney'


def inject_style(root):
    import streamlit as st
    st.markdown((Path(__file__).resolve().parent / "assets" / "tennis.css").read_text(), unsafe_allow_html=True)
