# CI Data Engineering Toolkit

Encodes CI Financial's data engineering standards so the agent applies them consistently,
without being reminded.

## What's included

**`deployment-checklist` skill** — runs CI's pre-deployment review over SQL and dbt code.
Triggers on phrases like "review before deploy", "is this ready to ship", or "code review this
SQL". The rules live in `resources/`, split by area:

| File | Owns |
|---|---|
| `naming-conventions.md` | File, model, column and alias naming |
| `optimization.md` | Query patterns and performance |
| `parameterization.md` | Hardcoded values that should be configuration |
| `security-and-pii.md` | Investor data and outbound extracts |

**Production safety hook** — blocks any `dbt` command targeting production. Production runs go
through dbt Cloud from Bitbucket, never from a laptop. The hook fires before the command
executes, so it holds whether or not dbt is installed.

**`dbt-review` subagent** — runs the deployment checklist autonomously and returns a PASS/FAIL
report per category. Works locally before a PR and headlessly in CI.

## Changing the rules

Edit the file in `resources/` that owns the area. Each file is independently reviewable, so a
change to the PII rules does not require re-reading the naming conventions. Keep `SKILL.md`
short — it should say *which* resource to read, not restate the rules.
