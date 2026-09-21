# Connecting Cortex Code Desktop to the CI Financial sandbox

**Please do this before the workshop.** Connection setup is the single biggest time sink in a
lab that runs against your own environment, and every minute spent on it in the room is a
minute not spent on the actual work. It takes about ten minutes.

If you get stuck, come with the error message — we will sort it out at 9:05.

---

## Two things, and they are easy to confuse

**The workshop guide is a hosted web app.** You will be given a URL. Keep it open in a browser
tab next to Cortex Code Desktop — every prompt is copied from there and pasted into the agent.
There is nothing to install and nothing to run.

**The repo you clone in step 4 is a workspace for the agent**, not the guide. Cortex Code needs
local files for Sessions 1, 3 and 6: it writes `AGENTS.md` into the project root, reviews the SQL
in `sql/deploy/`, creates a skill in the workspace, and works on the dbt project. Sessions 2, 4
and 5 touch only Snowflake.

**The lab data is already loaded** into `DE_HOL_SHARED` by the facilitator. You never upload a
CSV.

---

## What you need from the facilitator

| Item | Value |
|---|---|
| Account identifier | `{{CI_ACCOUNT_IDENTIFIER}}` |
| Your username | your CI SSO login |
| Role | `{{CI_ROLE}}` |
| Warehouse | `{{CI_WAREHOUSE}}` |
| Database | `{{CI_SANDBOX_DB}}` |
| Your schema | `DE_HOL_<YOUR INITIALS>` |

If any of these are blank, ask before the day. The account identifier is the one people most
often get wrong.

---

## Step 1 — Install Cortex Code Desktop

Download from the [Cortex Code Desktop downloads page](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-desktop/onboarding-and-authentication)
and install.

On Windows you will be offered two installers. Take the **User installer** unless your IT
team has told you otherwise — it needs no administrator rights and updates itself.

---

## Step 2 — Connect to the sandbox

On first launch you get a four-step flow: welcome, connect, mode, theme. At the **connect**
step, click **Add connection** and fill in:

| Field | Value |
|---|---|
| Account identifier | `{{CI_ACCOUNT_IDENTIFIER}}` |
| Connection name | `ci-sandbox` |
| Username | your CI SSO login |
| Authentication method | **External browser (SSO)** |

Click **Sign in**. Your browser opens, you authenticate through CI's identity provider, and
the token is cached in your OS keychain so you will not have to repeat this every launch.

If the browser does not open, use the **"Browser didn't open?"** link in the app to copy the
sign-in URL and open it manually.

### Or edit the config file directly

If you would rather not use the form, or you already have other Snowflake connections, add
this block to `~/.snowflake/connections.toml`:

```toml
[ci-sandbox]
account = "{{CI_ACCOUNT_IDENTIFIER}}"
user = "{{CI_USERNAME}}"
authenticator = "externalbrowser"
client_store_temporary_credential = true
warehouse = "{{CI_WAREHOUSE}}"
role = "{{CI_ROLE}}"
database = "{{CI_SANDBOX_DB}}"
schema = "DE_HOL_XX"
```

Replace `DE_HOL_XX` with your initials. Then in Cortex Code Desktop, click the connection
name in the top navigation bar and choose **Refresh Snowflake Connections**.

Each top-level key in that file is a separate connection, so this will not disturb any
existing setup you have.

---

## Step 3 — Set your role and warehouse

Two things people forget, and both produce confusing errors later:

1. Click the connection name in the top nav → **Change Role** → `{{CI_ROLE}}`.
   Getting this wrong shows up as *"Database not authorized"* or tables that appear not to
   exist.
2. Click the connection name → **Default Warehouse** → `{{CI_WAREHOUSE}}`.
   Getting this wrong shows up as *"no warehouse selected"* on your first query.

The warehouse choice is stored on your Snowflake user, so it applies to future sessions and
other machines too. You only need to do it once.

---

## Step 4 — Clone the workshop repo and trust the workspace

```bash
git clone https://github.com/sfc-gh-mli/coco-de-hol-ci-financial.git
cd coco-de-hol-ci-financial
```

In Cortex Code Desktop: **File → Open Folder**, select the cloned directory.

**Accept the trust prompt.** This matters more than it looks. Project skills under
`.snowflake/cortex/skills/` and plugins under `.cortex/plugins/` only activate in a trusted
workspace, and Session 3 has you building exactly those. If you skip the prompt, the skill
you write will appear to do nothing.

---

## Step 5 — Verify

Paste this into the Cortex Code chat panel:

```
Confirm my Snowflake setup: show my current user, role, warehouse and database, then
list the tables in {{CI_SANDBOX_DB}}.DE_HOL_SHARED with their row counts, and confirm
I can create a table in my own DE_HOL_<INITIALS> schema.
```

You are ready when you see:

- your role is `{{CI_ROLE}}` and a warehouse is set,
- twelve tables in `DE_HOL_SHARED`, the largest being `HOLDINGS_DAILY` at 30,972 rows,
- a successful write to your own schema.

---

## Optional — only if you want the dbt stretch session to run hands-on

Session 6 is the last session, it is explicitly a stretch, and **nothing else in the workshop
depends on it**. Sessions 1 through 5 need only the Snowflake connection you just set up.

If you would like Session 6 to be hands-on rather than a walkthrough:

```bash
# dbt Core, so `dbt build` works locally
pip install dbt-snowflake

mkdir -p ~/.dbt
cp dbt/profiles.yml.example ~/.dbt/profiles.yml
# fill in the placeholders, then:
dbt debug --project-dir dbt/
```

Do not spend more than a few minutes on this. If it does not cooperate, leave it — you will
lose nothing, and we will run Session 6 as a walkthrough.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Account not found" | Identifier in the wrong format | Must be `orgname-accountname`. Read it from Snowsight: avatar → **Connect a tool to Snowflake**. |
| Browser never opens for SSO | No default browser, or a stale IdP session | Use the "Browser didn't open?" link. If that fails, sign out of Snowsight and retry. |
| "No warehouse selected" | No default warehouse | Step 3 above. |
| "Database not authorized" | Wrong active role | Step 3 above. Start a new session if the change does not take effect. |
| Can read shared data, cannot create anything | Your schema was not provisioned | Tell the facilitator your initials — it is a one-line fix on their side. |
| Approval dialogs on every statement | Expected behaviour | Since v1.15, `SELECT` auto-approves while writes and DDL ask per statement. Sessions 2 and 4 are read-heavy; Session 5 will ask a few times. |
