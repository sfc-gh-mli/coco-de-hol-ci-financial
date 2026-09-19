from pathlib import Path

import streamlit as st

from components import is_session_complete

_DIR = Path(__file__).parent


def _title(session_num: int, label: str) -> str:
    check = " :green[:material/check_circle:]" if is_session_complete(session_num) else ""
    return f"{session_num}. {label}{check}"


st.set_page_config(
    page_title="CI Financial Data Engineering Workshop",
    page_icon=":material/engineering:",
    layout="wide",
)

st.logo(
    str(_DIR / "static" / "snowflake_full_logo.png"),
    icon_image=str(_DIR / "static" / "snowflake_logo.png"),
)

page = st.navigation(
    {
        "": [
            st.Page("app_pages/home.py", title="Home", icon=":material/home:"),
            st.Page("app_pages/getting_started.py", title="Getting Started", icon=":material/rocket_launch:"),
            st.Page("app_pages/agenda.py", title="Agenda", icon=":material/calendar_today:"),
        ],
        "Block 1: Ground & Investigate": [
            st.Page("app_pages/session_01.py", title=_title(1, "Connect & Ground"), icon=":material/link:"),
            st.Page("app_pages/session_02.py", title=_title(2, "Reverse-Engineer"), icon=":material/travel_explore:"),
        ],
        "Block 2: Standardize & Ship": [
            st.Page("app_pages/session_03.py", title=_title(3, "Custom Skills"), icon=":material/psychology:"),
            st.Page("app_pages/session_04.py", title=_title(4, "AI Functions"), icon=":material/auto_awesome:"),
            st.Page("app_pages/session_05.py", title=_title(5, "Determinism"), icon=":material/replay:"),
            st.Page("app_pages/session_06.py", title=_title(6, "dbt to Production"), icon=":material/build_circle:"),
        ],
    },
    position="sidebar",
)

page.run()
