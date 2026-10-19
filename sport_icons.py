"""Original lightweight SVG marks for sport navigation."""
import base64

FOOTBALL = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="white" stroke="#252339" stroke-width="3"/><path d="m32 20 12 9-5 14H25l-5-14zM9 20l12-3 3-12M55 20l-12-3-3-12M9 44l10-4 7 16M55 44l-10-4-7 16M21 17l11 3 11-3M20 29 9 20M44 29l11-9M25 43l-6-3M39 43l6-3" fill="#252339" stroke="#252339" stroke-width="2"/></svg>'
TENNIS = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><g transform="rotate(36 32 28)"><ellipse cx="31" cy="23" rx="17" ry="21" fill="#f5f0ff" stroke="#7856d8" stroke-width="4"/><path d="M20 10v26m7-33v39m8-39v39m7-32v26M16 15h30M14 23h34M16 31h30" stroke="#7856d8" stroke-width="1" opacity=".65"/><path d="m24 42 4 9h6l4-9M31 50v12" fill="none" stroke="#7856d8" stroke-width="5"/><path d="M27 54h8m-8 5h8" stroke="#252339" stroke-width="2"/></g><circle cx="51" cy="47" r="9" fill="#c5ed47" stroke="#647b16" stroke-width="1.5"/><path d="M45 41c8 2 3 10 12 10" fill="none" stroke="white" stroke-width="2"/></svg>'


def icon_data(sport):
    return "data:image/svg+xml;base64," + base64.b64encode((FOOTBALL if sport == "Football" else TENNIS).encode()).decode()


def show_sport_picker():
    import streamlit as st
    st.session_state.setdefault("selected_sport", "Football")
    def choose(value):
        st.session_state["selected_sport"] = value
    st.caption("Sport")
    with st.container(horizontal=True, key="sport_picker"):
        for value, key in (("Football", "football"), ("ATP Men's Singles", "tennis")):
            st.button(f"![{key} icon]({icon_data(value)}) {value}", key="sport_"+key,
                      type="primary" if st.session_state["selected_sport"] == value else "secondary",
                      on_click=choose, args=(value,), width=220)
    return st.session_state["selected_sport"]
