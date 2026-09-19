import streamlit as st

from components import (
    render_dependencies,
    render_explanation,
    render_key_concepts,
    render_prompt,
    render_session_header,
    render_technologies_used,
    render_what_you_built,
)

render_session_header(
    3,
    "Custom Skills & Sharing",
    "10:00 AM",
    "20 min",
    "A deployment-checklist skill with a resources/ folder, packaged as a plugin with a safety "
    "hook and a review subagent, and shared with the team",
)

render_dependencies(
    requires="A trusted workspace and `AGENTS.md` from Session 1. The review targets ship in "
             "the repo, so nothing from Session 2 is needed.",
    unlocks="Nothing depends on this session. Session 5 references the plugin as one rung on "
            "the determinism ladder, but does not require it.",
)

st.space("small")

render_technologies_used([
    {"name": "Custom skills", "description": "Your team's conventions encoded once, applied consistently", "icon": "psychology"},
    {"name": "resources/ folder", "description": "Progressive disclosure — the agent loads only the rules that apply", "icon": "folder_open"},
    {"name": "Plugins", "description": "Skills, hooks and subagents versioned and shared as one unit", "icon": "extension"},
])

st.space("small")

st.markdown("#### Why AGENTS.md is not enough")

with st.container(border=True):
    st.markdown("""
`AGENTS.md` told the agent CI's database name and naming rules, and it enforced them when asked.
That works for context.

It does not work for **process**. When the task is *"review this before we deploy it"*, there is
a specific sequence CI wants followed, a specific set of things to check, and a specific report
format expected at the end. That is a workflow, not a fact — and a workflow that must hold
whoever runs it, on whatever code, six months from now.

That is what a skill is for.
""")

st.markdown("""
Your review targets are already in the repo, deliberately non-compliant:

| File | What it is |
|---|---|
| `sql/deploy/01_monthly_performance_extract.sql` | Plain SQL. Builds the committee performance pack. |
| `sql/deploy/02_investor_extract_to_vendor.sql` | Plain SQL. Builds the monthly file sent to Meridian. |
| `dbt/models/staging/stg_HoldingsValued.sql` | The dbt-flavoured equivalent. |

Reviewing these needs no dbt install — they are read as text.
""")

st.space("small")

render_prompt(
    "Prompt 3.1",
    "Build the deployment-checklist skill with a resources/ folder",
    """Create a custom skill that runs CI's pre-deployment review on SQL and dbt code.

Put it at .snowflake/cortex/skills/deployment-checklist/ so it is auto-discovered.

Structure it with a SHORT SKILL.md that delegates to separate resource files. SKILL.md
should contain only: the frontmatter, the workflow steps, and instructions on WHICH
resource file to read for WHICH kind of check. Do not inline the rules into SKILL.md.

Create these resource files under resources/, each holding one category of requirement:

resources/naming-conventions.md
- snake_case for files, models, columns and aliases
- staging models prefixed stg_, marts prefixed dim_ or fact_
- _pct suffix on percentage columns, _cad on currency amounts, _ts on timestamps
- no abbreviations that are not in CI's glossary; spell out words
- table and column names are nouns, not verb phrases

resources/optimization.md
- no SELECT * in anything that persists; enumerate columns
- no implicit cross joins; use explicit JOIN ... ON
- predicates must be sargable — no functions wrapped around a filtered column
- flag correlated subqueries in the SELECT list that should be joins
- flag aggregations over percentage columns, which are almost always wrong
- note when a clustering key would help, based on the actual filter and join columns

resources/parameterization.md
- no hardcoded database or schema names; use dbt sources, vars, or env_var
- no hardcoded dates or year boundaries; parameterise the reporting period
- no hardcoded lists of entity keys that will drift as the business changes
- no credentials, hostnames or connection strings anywhere in the repo

resources/security-and-pii.md
- investor-identifying columns must never appear in an outbound vendor extract
- treat free-text note fields as PII until proven otherwise
- SELECT * over a table containing PII is automatically a HIGH finding
- flag anything that widens the column set of a file leaving CI's perimeter

The workflow in SKILL.md should be:
1. Identify the files in scope. Ask if ambiguous.
2. For each file, read the relevant resource files and check it against them.
3. Report findings as a table: file, line, category, severity HIGH/MEDIUM/LOW, the
   offending code, and the specific fix.
4. Summarise: total findings by severity, and a clear deploy / do-not-deploy recommendation.
5. Never modify the code. Review only.

Write a description that triggers on phrases like "review before deploy", "pre-deployment
check", "is this ready to ship", "code review this SQL".""",
)

render_explanation(
    "Why the rules live in resources/ and not in SKILL.md",
    """
This is the structural point of the session, and it is worth being precise about the four
reasons — because "keep files small" is the least interesting of them.

**Context economy.** A skill's instructions are loaded into the context window. If every naming,
optimization, parameterization and PII rule is inlined, all of it loads every time — including
the PII rules when someone is reviewing a harmless staging view. With `resources/`, `SKILL.md`
stays short and the agent pulls only the file that applies to the code in front of it.

**Ownership.** Different people own different rules. The naming conventions belong to the data
engineering leads; the PII rules belong to compliance. In separate files, compliance can review
and change `security-and-pii.md` without reading or risking anything else. In one file, every
change is a change to the whole skill.

**Reviewability.** A pull request that changes `parameterization.md` is legible. A pull request
that changes forty lines in the middle of a 500-line `SKILL.md` is not.

**Maintainability.** Skills degrade past roughly 500 lines — they become hard to keep coherent
and they dilute the context they are competing for. The `resources/` split is how you add rules
for years without hitting that wall.

The shape:

```
.snowflake/cortex/skills/deployment-checklist/
├── SKILL.md                      # frontmatter, workflow, and which resource to read when
└── resources/
    ├── naming-conventions.md
    ├── optimization.md
    ├── parameterization.md
    └── security-and-pii.md
```

Note the location. `.snowflake/cortex/skills/` is auto-discovered in a trusted workspace — no
registration, no install. Write the file and the skill is live. That makes it the right place to
*develop* a skill, and the wrong place to *share* one, which is the next prompt.
""",
)

st.space("small")

render_prompt(
    "Prompt 3.2",
    "Run it, then package it as a plugin and share it",
    """First, use the deployment-checklist skill to review these files:
- sql/deploy/01_monthly_performance_extract.sql
- sql/deploy/02_investor_extract_to_vendor.sql
- dbt/models/staging/stg_HoldingsValued.sql

Give me the full findings table. I want to see whether it catches things I have not told it
to look for on this specific code.

Then package the skill for the team. Consult the Cortex Code Desktop plugin documentation
at https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-desktop/plugins for the
correct schema, and write the files directly — do not use the cortex CLI.

1. Move the skill to .cortex/plugins/ci-de-toolkit/skills/deployment-checklist/
2. Create .cortex/plugins/ci-de-toolkit/.cortex-plugin/plugin.json with name ci-de-toolkit,
   version 1.0.0, an author, and pointers to ./skills, ./agents and ./hooks/hooks.json.
   Add an activation.md that briefly says what the plugin contains.
3. Add a PreToolUse hook at hooks/validate-bash.sh that blocks any dbt command containing
   --target prod, with an error message saying production runs go through dbt Cloud from
   Bitbucket, not from a laptop. Wire it up in hooks/hooks.json using the matcher "bash".
4. Add a subagent at agents/dbt-review.md that runs the deployment checklist autonomously
   and produces a PASS/FAIL report per category. It must work by reviewing files at given
   paths. If a git remote is available it may additionally diff against it, but it must not
   REQUIRE a reachable remote — that is a fallback, not a dependency.

Then verify the plugin is active: Settings, Plugins, look for ci-de-toolkit.""",
)

st.info(
    "**Test the hook without dbt.** Ask the agent to run `dbt build --target prod`. The hook "
    "fires *before* the command executes, so it blocks even if dbt is not installed at all. "
    "That is the difference between a guardrail and a suggestion — it does not depend on the "
    "tool being present, or on the agent choosing to cooperate.",
    icon=":material/shield:",
)

render_explanation(
    "What the review should catch, and why the second file matters",
    """
The findings you get back should include things nobody pointed the skill at specifically. That
is the test of whether the rules were written well: a rule that only catches the example it was
written for is not a rule.

Across the three files there are hardcoded database and schema names, hardcoded dates, a
hardcoded list of fund codes that will drift the moment CI launches a fund, `SELECT *` in
persisted tables, an implicit cross join, a `TO_CHAR` wrapped around a filtered date column, a
plaintext credential sitting in a comment, and a sum over a percentage column that produces a
meaningless number.

**The second file is the one that matters.** `02_investor_extract_to_vendor.sql` selects `ia.*`
from `INVESTOR_ACCOUNTS` into a file that leaves CI and goes to Meridian. That table holds
investor names, emails, phone numbers, and free-text advisor notes with identifiers embedded in
prose. Every one of those columns is in the outbound extract.

Notice how it happened: nobody decided to send investor PII to a vendor. Someone wrote
`SELECT *`, and the column set grew. That is why `SELECT *` over a table containing PII is a
HIGH finding rather than a style preference, and it is the thread Session 4 picks up.

**On sharing.** Three options, in the order CI should actually adopt them:

1. **Commit the plugin into the Bitbucket repo under `.cortex/plugins/`.** Auto-discovered by
   every clone, versioned alongside the code it governs, no install step, and updates arrive
   with `git pull`. This is the right default.
2. **The account-level Shared Skills Catalog**, for reach across repositories. Browse, import
   and publish from the Agent Manager sidebar. Feature-flagged as of Desktop v1.15 — check
   availability before promising it.
3. **`cortex plugin install` from a git URL**, for cases where the plugin is not part of the
   repo being worked on.

**Why a plugin rather than a loose skill folder.** A plugin is versioned, its manifest is
validated on load, it installs as one unit, and it can carry hooks and subagents alongside the
skill. A skill folder has no version, no validation, and no way to bundle a hook. Once more than
one person depends on it, that difference stops being theoretical.
""",
)

st.space("small")

render_key_concepts([
    {
        "term": "Skill versus AGENTS.md",
        "definition": "`AGENTS.md` carries stable facts and is always loaded. A skill carries a "
                      "repeatable multi-step workflow and loads only when its description "
                      "matches the request. Facts go in `AGENTS.md`; processes go in skills.",
    },
    {
        "term": "Progressive disclosure",
        "definition": "Keeping the entry point short and loading detail on demand. A skill that "
                      "says \"read resources/security-and-pii.md when the code touches investor "
                      "data\" costs almost nothing until that condition holds. The alternative "
                      "spends context on rules that do not apply.",
    },
    {
        "term": "Plugin",
        "definition": "A directory with a `.cortex-plugin/plugin.json` manifest that bundles "
                      "skills, hooks, subagents and MCP servers as one versioned, validated, "
                      "installable unit. Auto-discovered from `.cortex/plugins/` in a trusted "
                      "workspace.",
    },
    {
        "term": "PreToolUse hook",
        "definition": "A shell command that runs before the agent executes a tool, and can "
                      "block it. Unlike an instruction in `AGENTS.md`, a hook is deterministic: "
                      "it does not depend on the agent choosing to comply. The right mechanism "
                      "for anything that must never happen.",
    },
    {
        "term": "Subagent",
        "definition": "A Markdown-defined agent that runs autonomously to completion on one "
                      "task, as opposed to a skill that guides an interactive session. The same "
                      "subagent can run locally before a PR and headlessly in CI — same "
                      "standard, two contexts.",
    },
])

st.space("small")

render_what_you_built([
    "A `deployment-checklist` skill with a four-file `resources/` folder, one per requirement area",
    "A findings table over three non-compliant files, including a PII leak nobody pointed it at",
    "`ci-de-toolkit` — a versioned plugin bundling the skill, a hook and a subagent",
    "A `PreToolUse` hook that blocks production dbt runs whether or not dbt is installed",
    "A `dbt-review` subagent that works from file paths, with git diff as an enhancement",
    "A concrete plan for sharing it: commit to the repo, then the account catalog",
], session_num=3)
