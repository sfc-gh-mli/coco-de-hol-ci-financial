import streamlit as st

st.title("Workshop agenda")

AGENDA = [
    ("9:00 AM", "Welcome & Workshop Overview", None, None),
    ("9:05 AM", "Session 1: Connect & Ground", "20 min", "1"),
    ("9:25 AM", "Session 2: Reverse-Engineer the Vendor Dataset", "35 min", "2"),
    ("10:00 AM", "Session 3: Custom Skills & Sharing", "20 min", "3"),
    ("10:20 AM", "Session 4: AI Functions for Data Engineering", "15 min", "4"),
    ("10:35 AM", "Session 5: Determinism", "20 min", "5"),
    ("10:55 AM", "Session 6: dbt to Production :orange-badge[STRETCH]", "15 min", "6"),
    ("11:10 AM", "Wrap-up & Q&A", None, None),
]

for time, title, duration, session_num in AGENDA:
    col1, col2 = st.columns([1, 4])
    col1.markdown(f"**{time}**")
    if session_num:
        col2.markdown(f":material/play_circle: **{title}** :gray-badge[{duration}]")
    else:
        col2.markdown(f":gray[{title}]")

st.space("medium")

st.markdown("##### What you'll build by end of session")
st.markdown("""
| Object Type | Count | Examples |
|-------------|-------|---------|
| **AGENTS.md** | 1 | CI conventions, encoded once for every future session |
| **Reconstructed methodology doc** | 1 | Seven rules with the proving SQL for each |
| **Stated-vs-actual claim diff** | 1 | `VENDOR_METHODOLOGY_CLAIMS` from the vendor PDF via `AI_EXTRACT` |
| **Custom skill** | 1 | `deployment-checklist` with a 4-file `resources/` folder, committed to the repo |
| **AI-assisted PII scan** | 1 | `AI_CLASSIFY` + `AI_REDACT` over free-text advisor notes |
| **PII scan + redaction** | 2 | `AI_CLASSIFY` and `AI_REDACT` over free-text KYC notes |
| **Stored procedure** | 1 | `SP_VALIDATE_VENDOR_PERFORMANCE` — deterministic, auditable |
| **Audit table + Task** | 2 | `VENDOR_RECON_RESULTS` and a scheduled validation task |
| **dbt model** *(stretch)* | 1 | `fund_performance_monthly` with schema tests |
""")

st.space("small")

st.markdown("##### Session dependencies")
with st.container(border=True):
    st.markdown("""
Sessions 1 through 5 require **only your Snowflake connection**. Nothing in them needs dbt,
dbt Cloud, Bitbucket, or network access beyond Snowflake.

Session 6 is the only session that touches dbt Cloud and Bitbucket, it is the **last** session,
and **nothing depends on it**. The Getting Started pre-flight check tells you at the start of
the morning whether it will run hands-on or as a walkthrough.

If you fall behind, Sessions 2 and 5 each have a **checkpoint script** that puts you back on
the main line in about 30 seconds.
""")

st.space("small")

st.markdown("##### Location")
with st.container(border=True):
    st.markdown("""
:material/location_on: **CI Financial — Toronto, ON**

9:00 AM — 11:15 AM
""")
