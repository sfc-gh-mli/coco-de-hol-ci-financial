# Troubleshooting

Ordered roughly by how often you will hit each one.

---

## Connection and access

### "Account not found" when adding the connection

The account identifier is wrong. It must be `orgname-accountname`, not the full URL and not the
legacy `xy12345.region` form. Have them read it from Snowsight: avatar (bottom left) →
**Connect a tool to Snowflake**. It is also in the URL:
`https://app.snowflake.com/<orgname>/<accountname>/`.

### The browser never opens for SSO

1. Confirm they have a default browser set at the OS level.
2. Use the **"Browser didn't open?"** link in Cortex Code Desktop to copy the sign-in URL and
   open it manually.
3. If their IdP session is stale, signing out of Snowsight in the browser first and retrying
   usually clears it.

### Connected, but every query fails with "no warehouse selected"

No default warehouse. Click the connection name in the top nav → **Default Warehouse** → pick the
sandbox warehouse. This persists server-side via `ALTER USER SET DEFAULT_WAREHOUSE`, so it only
needs doing once.

Alternatively add `warehouse = "..."` to their `~/.snowflake/connections.toml` entry and use
**Refresh Snowflake Connections** from the connection menu.

### "Database not authorized" or objects that should exist do not

Almost always the wrong active role. Click the connection name → **Change Role** and select the
sandbox role. Note that Cortex Code caches some object metadata per session — if the role change
does not seem to take effect, start a new session.

### Attendee can read `DE_HOL_SHARED` but cannot create anything

Their `DE_HOL_<INITIALS>` schema was not created, or ownership was not granted. Re-run
`scripts/01_attendee_schema.sql` with their initials. This is why that script runs at T−3 days,
not during the lab.

---

## Cortex Code behaviour

### Approval dialogs appear for every statement and it is slowing them down

Expected. Since Desktop v1.15, `snowflake_sql_execute` runs a SQL trust analyzer: `SELECT`-only
statements auto-approve, while DDL, DML writes and `GRANT`/`REVOKE` get a per-statement approval
dialog. Sessions 2 and 4 are read-heavy so this is mostly invisible; Session 5 creates a
procedure, a table and a task, so expect three or four dialogs there.

Tell them at the start of Session 5 that the dialogs are coming and are a feature, not a
misconfiguration. If someone wants fewer interruptions they can switch the approval preference
in the input bar, but do not encourage blanket bypass in a customer environment.

### The skill or plugin does not appear in Session 3

Workspace trust. Project-scoped skills under `.snowflake/cortex/skills/` and plugins under
`.cortex/plugins/` **only auto-activate in a trusted workspace**.

1. Settings (gear, bottom of left sidebar) → **Plugins**.
2. If `ci-de-toolkit` is listed but toggled off, toggle it on.
3. If it is not listed at all, click the **↻ refresh** button in the Plugins toolbar.
4. If it still does not appear, the workspace is untrusted — reopen the folder and accept the
   trust prompt.

This is called out as an explicit step in Getting Started for exactly this reason.

### Cortex Code tries to run `cortex plugin install` instead of writing files

Bundled skills know about the CLI and can activate here. The `AGENTS.md` created in prompt 1.2
includes an instruction not to use the `cortex` CLI, which normally prevents it. If it happens
anyway, tell them to reply: *"Do not use the cortex CLI — write the files directly."*

### The agent invented a column that does not exist

Have them ask it to `DESCRIBE` the table first. Worth doing openly in front of the room once if
it comes up — it is a good, honest teaching moment about grounding, and it reinforces why
Session 2 measures residuals instead of trusting output.

---

## Session 2 specifics

### January rows are missing from their NAV reconciliation

They inner-joined FX on the same date and lost the first business day of January, because its
prior business day falls in December 2024. The calendar deliberately includes late December 2024
so the lag is available. The fix is `LAG(rate) OVER (PARTITION BY from_currency ORDER BY rate_date)`,
not an equi-join to a lagged date.

This is a designed trap. It is worth letting them find it.

### Their residuals are enormous — thousands of basis points

Usually one of:
- `BEGINNING_NAV` taken as the first day of the month rather than the last day of the prior month.
- Quantities joined without the date predicate, producing a fan-out. Have them check row counts.
- Percentages versus decimals: `TOTAL_RETURN_PCT` and the target's `*_PCT` columns are in percent,
  so `1.5` means 1.5%, not 150%.

### Nothing reconciles and they are ready to give up

Give them rule 2 (distributions). It is the loudest signal, it only affects eight rows, and
finding it produces enough momentum to carry the rest. See `SOLUTION.md`.

### They force the December outlier to fit

Do not let this slide quietly — it is one of the better teachable moments in the lab. They will
have produced a formula that reconciles all 72 rows perfectly and describes nothing real. The
correct move is to segment: notice one fund-month is different in kind, exclude it, reconcile the
other 71 cleanly, and raise the outlier as a vendor question.

---

## AI Functions

### `AI_PARSE_DOCUMENT` / `AI_CLASSIFY` / `AI_REDACT` fail with "unknown function"

The function is not available in the sandbox's region, or the role lacks
`SNOWFLAKE.CORTEX_USER`. Verify with:

```sql
SHOW GRANTS TO ROLE <sandbox_role>;
SELECT AI_COMPLETE('claude-4-sonnet', 'reply with OK');
```

Use the fallback in `run-of-show.md`. Test this at T−3 days.

### The staged PDF cannot be read

`AI_PARSE_DOCUMENT` needs the file on a stage the role can read, and the stage needs
`DIRECTORY = (ENABLE = TRUE)` for `GET_PRESIGNED_URL`-style access patterns.
`scripts/00_facilitator_load_shared.sql` creates the stage correctly — confirm the PDF actually
landed with `LIST @DE_HOL_SHARED.VENDOR_DOCS;`.

### `AI_CLASSIFY` output varies between two runs on the same row

Expected, and it is the setup for Session 5 rather than a bug. Do not fix it in Session 4 — let
them see it, then resolve it deliberately in Session 5 by pinning the model, fixing the output
schema, and materialising the result once.

If someone raises it in Session 4, the right answer is *"hold that thought, it's the next
session."*

---

## Session 5 specifics

### The stored procedure fails with "invalid identifier" on a parameter

The single most common Snowflake stored-procedure error. Inside a SQL procedure body, parameters
must carry a colon prefix:

```sql
-- wrong: Snowflake reads FUND_CODE as a column name
WHERE fund_code = FUND_CODE

-- right
WHERE fund_code = :FUND_CODE
```

Cortex Code usually gets this right, but if the procedure will not compile, check this first.

### The task will not start

Tasks are created suspended. They need `ALTER TASK <name> RESUME`, and the role needs
`EXECUTE TASK` on the account. If the sandbox role does not have it, have them create the task
and show it in `SHOW TASKS` without resuming — the object is the deliverable, not the schedule.

---

## Session 6 specifics

### `dbt debug` fails

Out of scope for the room. Session 6 is a stretch session with three degradation tiers — drop to
tier (b): have Cortex Code write the model file and run the compiled SQL directly in Snowflake.
The artifact is the same. Do not spend lab time debugging a dbt profile.

### The Bitbucket remote is unreachable

Also fine. Have them commit locally on a `feature/` branch and stop there. The commit is the
deliverable; the push is not.

---

## Environment reset

To wipe an attendee's work and start over:

```sql
DROP SCHEMA IF EXISTS {{CI_SANDBOX_DB}}.DE_HOL_<INITIALS> CASCADE;
```

Then re-run `scripts/01_attendee_schema.sql`. `DE_HOL_SHARED` is read-only to attendees and
should never need resetting; if it does, `scripts/00_facilitator_load_shared.sql` is idempotent.

To put someone back on the main line without redoing earlier work, use the checkpoints:

```sql
-- gets them a working seven-rule reconciliation (skips ahead past Session 2)
-- scripts/checkpoints/after_session_02.sql

-- gets them the stored procedure and audit table (skips ahead past Session 5)
-- scripts/checkpoints/after_session_05.sql
```
