import streamlit as st

st.title("CI Financial Data Engineering Workshop")
st.markdown("Validating vendor data, encoding your standards, and making agent output reproducible")

st.space("small")

col1, col2, col3 = st.columns(3)
col1.metric("Sessions", "6", help="Five core sessions plus one stretch session")
col2.metric("Prompts", "15", help="Total prompts across all sessions")
col3.metric("Duration", "2 hrs 15", help="Total workshop time")

st.space("medium")

st.markdown("#### How this workshop works")

st.markdown("""
Each session has **numbered prompts** that you copy and paste into **Cortex Code Desktop**,
connected to your CI Financial sandbox.

You are not being shown a demo. You will be driving the agent, reading what it produces,
and deciding whether to accept it — which is the actual job.

Sessions build on each other, but **Sessions 1 through 5 need nothing except your Snowflake
connection**. Session 6 is a stretch session that touches dbt Cloud and Bitbucket; if that
tooling is not ready on the day, the first five sessions stand entirely on their own.
""")

st.space("small")

st.markdown("#### The scenario")
with st.container(border=True):
    st.markdown("""
CI Financial's asset management arm sends daily holdings, prices, FX rates and cash flows to a
third-party performance vendor, **Meridian Performance Analytics**. Meridian returns a monthly
fund performance dataset: NAV, gross and net returns, benchmark returns, excess returns.

Those numbers get used. They go to clients, to committees, and into regulatory filings. Meridian
also supplies a three-page methodology statement describing how they are produced — written the
way vendor documents are always written: confident, prose-heavy, and vague in exactly the places
that matter.

**Your job is to be able to defend those numbers.** That means reconstructing how they were
actually produced from the source data CI already has, checking that against what the vendor
*says* it does, and then making the whole thing repeatable so it does not depend on whoever ran
it or how they happened to phrase the question.

| What you get | What you have to figure out |
|---|---|
| 11 source tables CI sends the vendor | Which sources feed which target column |
| 1 target table the vendor returns | What FX convention, return formula, and fee basis were used |
| A 3-page methodology PDF | Which of the vendor's stated claims survive contact with the data |
""")

st.space("small")

st.markdown("#### What we're building")

with st.container(border=True):
    st.markdown("""
**1. A grounded workspace** — Cortex Code connected to your sandbox, an `AGENTS.md` that encodes
CI's conventions once instead of re-explaining them every session, and a working map of which
bundled skills are worth reaching for.

**2. A reconstructed vendor methodology** — found by running SQL, computing residuals, and reading
what the residuals are correlated with. This is where code execution earns its place: the agent
does not guess the formula, it tests hypotheses against data and reports what survives. Then
`AI_PARSE_DOCUMENT` and `AI_EXTRACT` pull the vendor's *stated* claims out of the PDF so you can
diff claim against reality.

**3. A deployment checklist skill** — your naming conventions, optimization rules, parameterization
requirements and PII rules, encoded as a custom skill with a `resources/` folder so each area can
be owned and reviewed independently. Then shared with the team, three ways.

**4. AI Functions doing data engineering work** — `AI_CLASSIFY` to triage reconciliation breaks by
root cause, and `AI_CLASSIFY` plus `AI_REDACT` to prove that nothing CI sends the vendor carries
investor PII buried in free-text advisor notes.

**5. A deterministic validation procedure** — the agreed calculation moved out of the prompt and
into a Snowflake stored procedure, so the same inputs produce byte-identical output every run.
Including the harder question: how do you keep AI function calls reproducible inside a pipeline?

**6. A production dbt model** *(stretch)* — the validated logic as a dbt model, committed for
dbt Cloud to run on schedule.
""")

st.space("small")

st.markdown("#### Prerequisites")
with st.container(border=True):
    st.markdown("""
- **Cortex Code Desktop** installed — see **Getting Started** in the sidebar
- Access to the **CI Financial sandbox** with your own `DE_HOL_<INITIALS>` schema
- Your sandbox credentials from the facilitator (SSO login)
- A role carrying `SNOWFLAKE.CORTEX_USER` — needed for the AI Functions session
- Familiarity with SQL; dbt familiarity helps for the stretch session but is not required

:material/info: You do **not** need a Snowflake trial account. This workshop runs entirely in
CI Financial's own sandbox environment.
""")

st.space("medium")
st.caption("Built for the CI Financial workshop  :material/location_on:  Toronto, ON  —  9:00 AM to 11:15 AM")
