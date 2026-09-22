import streamlit as st

st.title("Getting Started")
st.markdown("Connecting Cortex Code Desktop to the CI Financial sandbox")

st.space("small")

st.info(
    ":material/schedule: **Ideally you did steps 1 to 4 before today.** If not, work through "
    "them now — we will help. Everything here is also in `docs/connect-coco-desktop.md` in "
    "the repo.",
    icon=":material/info:",
)

st.space("small")

st.markdown("#### Two things, and they are easy to confuse")

with st.container(border=True):
    st.markdown("""
**This guide** — the page you are reading — is a hosted web app. You do not download it, install
it, or run it. Just keep this URL open in a browser tab alongside Cortex Code Desktop. Every
prompt in the workshop is copied from here and pasted there.

**The repo** — you do clone that, in step 4. Not for this guide, but because Cortex Code Desktop
needs local files to work on:

| Session | Needs the cloned repo? | What it uses |
|---|---|---|
| 1 | Yes | Writes `AGENTS.md` into the project root |
| 2 | No | Reads data already loaded in Snowflake |
| 3 | **Yes** | Reviews the SQL files in `sql/deploy/`, and creates a skill in the workspace |
| 4 | No | Reads data already loaded in Snowflake |
| 5 | No | Creates objects in Snowflake |
| 6 | Yes | The dbt project in `dbt/` |

The lab data is **already loaded** into `DE_HOL_SHARED` by the facilitator. You never upload a
CSV. The download buttons in Session 2 are only there if you want a local copy to poke at
afterwards.
""")

st.space("small")

st.markdown("#### What you need from the facilitator")

with st.container(border=True):
    st.markdown("""
| Item | Value |
|---|---|
| **Account identifier** | `{{CI_ACCOUNT_IDENTIFIER}}` |
| **Username** | your CI SSO login |
| **Role** | `{{CI_ROLE}}` |
| **Warehouse** | `{{CI_WAREHOUSE}}` |
| **Database** | `{{CI_SANDBOX_DB}}` |
| **Your schema** | `DE_HOL_<YOUR INITIALS>` |

You will read shared data from `DE_HOL_SHARED` and write everything you build to your own
`DE_HOL_<INITIALS>` schema. The shared schema is read-only.
""")

st.space("small")

st.markdown("#### Step 1: Install Cortex Code Desktop")

with st.container(border=True):
    st.markdown("""
Download and install from the
[Cortex Code Desktop downloads page](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-desktop/onboarding-and-authentication).

On Windows, take the **User installer** unless your IT team says otherwise — it needs no
administrator rights and updates itself.
""")

st.space("small")

st.markdown("#### Step 2: Connect to the sandbox")

with st.container(border=True):
    st.markdown("""
On first launch you get a four-step flow: **welcome → connect → mode → theme**. At the
**connect** step click **Add connection**:

| Field | Value |
|---|---|
| Account identifier | `{{CI_ACCOUNT_IDENTIFIER}}` |
| Connection name | `ci-sandbox` |
| Username | your CI SSO login |
| Authentication method | **External browser (SSO)** |

Click **Sign in**. Your browser opens for CI's identity provider, and the token is cached in
your OS keychain so you will not repeat this every launch.

If the browser does not open, use the **"Browser didn't open?"** link in the app to copy the
sign-in URL.
""")

with st.expander(":material/code: Or edit `~/.snowflake/connections.toml` directly"):
    st.markdown(
        "Useful if you already have other Snowflake connections — each top-level key is a "
        "separate connection, so this will not disturb your existing setup."
    )
    st.code("""[ci-sandbox]
account = "{{CI_ACCOUNT_IDENTIFIER}}"
user = "{{CI_USERNAME}}"
authenticator = "externalbrowser"
client_store_temporary_credential = true
warehouse = "{{CI_WAREHOUSE}}"
role = "{{CI_ROLE}}"
database = "{{CI_SANDBOX_DB}}"
schema = "DE_HOL_XX\"""", language="toml")
    st.markdown(
        "Then click the connection name in the top navigation bar and choose "
        "**Refresh Snowflake Connections**."
    )

st.space("small")

st.markdown("#### Step 3: Set your role and warehouse")

with st.container(border=True):
    st.markdown("""
Two things people forget, both of which produce confusing errors later. Click the connection
name in the top navigation bar, then:

1. **Change Role** → `{{CI_ROLE}}`
   Getting this wrong looks like *"Database not authorized"*, or tables that seem not to exist.

2. **Default Warehouse** → `{{CI_WAREHOUSE}}`
   Getting this wrong looks like *"no warehouse selected"* on your first query.

The warehouse choice is stored on your Snowflake user, so it carries to future sessions and
other machines. Once is enough.
""")

st.space("small")

st.markdown("#### Step 4: Clone the repo and trust the workspace")

with st.container(border=True):
    st.markdown("""
This gives Cortex Code Desktop a project to work in. It is **not** how you get this guide —
the guide is the browser tab you are reading.

```bash
git clone https://github.com/sfc-gh-mli/coco-de-hol-ci-financial.git
cd coco-de-hol-ci-financial
```

In Cortex Code Desktop: **File → Open Folder**, select the cloned directory.
""")
    st.warning(
        "**Accept the trust prompt.** Project skills under `.snowflake/cortex/skills/` only "
        "activate in a trusted workspace — and Session 3 has you building exactly one. Skip the "
        "prompt and the skill you write will appear to do nothing.",
        icon=":material/warning:",
    )

st.space("small")

st.markdown("#### Step 5: Pre-flight check")

with st.container(border=True):
    st.markdown("""
This is **Prompt 1.1** in Session 1 — run it there rather than here. It confirms your
connection, checks you can read the shared data and write to your own schema, and reports
which optional tooling you have.

The tooling part only affects **Session 6**, the dbt stretch session. Sessions 1 through 5
need nothing beyond the Snowflake connection you just set up.
""")

st.space("small")

st.markdown("#### Optional: only if you want Session 6 hands-on")

with st.container(border=True):
    st.markdown("""
Session 6 is last, explicitly a stretch, and **nothing else depends on it**. If the tooling
is not ready we run it as a walkthrough and you lose nothing.

If you would like it hands-on:

```bash
pip install dbt-snowflake

mkdir -p ~/.dbt
cp dbt/profiles.yml.example ~/.dbt/profiles.yml
# fill in the placeholders, then:
dbt debug --project-dir dbt/
```

Do not spend more than a few minutes on this.
""")

st.space("medium")

st.markdown("##### Prerequisites recap")
col1, col2, col3 = st.columns(3)
col1.metric("Trial account", "None", help="This workshop runs in CI Financial's own sandbox — no Snowflake trial needed")
col2.metric("Setup time", "~10 min", help="Do it before the day if you can")
col3.metric("Sessions 1-5 need", "Snowflake", help="No dbt, Bitbucket or external network access required")

st.caption(
    "Your role needs `SNOWFLAKE.CORTEX_USER` for the AI Functions session. The facilitator "
    "confirms this ahead of time — flag it if the pre-flight check reports otherwise."
)
