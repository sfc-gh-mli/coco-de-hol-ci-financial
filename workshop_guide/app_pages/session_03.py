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
    "A deployment-checklist skill with a resources/ folder, invoked against real code, and a "
    "concrete plan for sharing it with the team",
)

render_dependencies(
    requires="A trusted workspace and `AGENTS.md` from Session 1. The review targets ship in "
             "the repo, so nothing from Session 2 is needed.",
    unlocks="Nothing depends on this session. Session 5 references skills as one rung on the "
            "determinism ladder, but does not require this one.",
)

st.space("small")

render_technologies_used([
    {"name": "Custom skills", "description": "Your team's conventions encoded once, applied consistently", "icon": "psychology"},
    {"name": "resources/ folder", "description": "Progressive disclosure — the agent loads only the rules that apply", "icon": "folder_open"},
    {"name": "Skill sharing", "description": "Git, a Snowflake stage, or the account catalog", "icon": "share"},
])

st.space("small")

st.markdown("#### Why AGENTS.md is not enough")

with st.container(border=True):
    st.markdown("""
`AGENTS.md` told the agent CI's database name and naming rules, and it enforced them when asked.
That works for context.

It does not work for **process**. When the task is *"review this before we deploy it"*, there is a
specific sequence CI wants followed, a specific set of things to check, and a specific report
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
check", "is this ready to ship", "code review this SQL".

Then show me the finished directory tree so I can see the SKILL.md / resources split.""",
)

st.warning(
    "**A new skill is not callable until the session reloads.** Skills are discovered when a "
    "session starts, so the one you just wrote will not appear yet — this is the single most "
    "common reason this session looks broken. Either start a **new session** in the same "
    "workspace, or open **Agent Settings → Skills** and hit **↻ refresh**.\n\n"
    "Then confirm before moving on: type `/` in the chat input and look for "
    "`deployment-checklist`, or ask *\"list your available skills and tell me whether "
    "deployment-checklist is among them, and what location it was loaded from\"* — you want "
    "location **project**.",
    icon=":material/refresh:",
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
registration, no install step, no manifest. Write the files and the skill is live on the next
session reload.
""",
)

st.space("small")

render_prompt(
    "Prompt 3.2",
    "Invoke the skill on real code",
    """Use the deployment-checklist skill to review these three files:

- sql/deploy/01_monthly_performance_extract.sql
- sql/deploy/02_investor_extract_to_vendor.sql
- dbt/models/staging/stg_HoldingsValued.sql

Give me the full findings table, then the summary and the deploy recommendation.

I want to see whether it catches things I never pointed it at on this specific code — so do
not let me tell you what is wrong with these files. Work from the skill's own rules.""",
)

st.info(
    "That prompt does not name the skill's rules or the problems in the files. That is the test: "
    "a skill that only catches the example it was written for is not a skill. If the findings "
    "surprise you, the rules were written well.",
    icon=":material/target:",
)

render_explanation(
    "What the review should catch, and why the second file matters",
    """
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

**On the report format.** The skill specifies a findings table and an explicit deploy /
do-not-deploy verdict. That matters more than it looks: a review that ends in prose gets
interpreted, and a review that ends in a verdict gets acted on. If the agent softens the verdict
because the fixes look small, that is a bug in the skill's instructions, not a judgement call —
tighten the wording.
""",
)

st.space("small")

st.markdown("#### Sharing it with the team")

with st.container(border=True):
    st.markdown("""
Right now this skill exists on one laptop, in one workspace. Three ways to change that, in the
order CI should actually adopt them.
""")

    with st.expander(":material/merge: **1. Commit it to Bitbucket** — the right default", expanded=True):
        st.markdown("""
The skill is just files. Commit the folder into the repo that already holds the code it governs:

```bash
git add .snowflake/cortex/skills/deployment-checklist
git commit -m "Add deployment-checklist skill: CI pre-deployment review standards"
```

Anyone who clones the repo and opens it in Cortex Code Desktop gets the skill automatically —
**no install step, no registration.** Updates arrive with `git pull`.

Why this is the default:

- **Versioned with the code it governs.** The rules and the SQL they check move together, so the
  skill can never drift out of step with the conventions it enforces.
- **Reviewable.** Changing a rule is a pull request, with a diff and an approver.
- **Scoped.** Only people working in this repo get it, which is usually what you want for
  repo-specific conventions.

The limitation: it only reaches people working in *this* repo. For a rule set that should apply
across every project at CI, use option 2 or 3.
""")

    with st.expander(":material/cloud_upload: **2. Publish to a Snowflake stage** — governed by grants"):
        st.markdown("""
Push the skill into Snowflake and let RBAC decide who can use it. No Git credentials to
distribute, and access is auditable through the same grants as everything else.

```bash
# publisher
cortex skill publish .snowflake/cortex/skills/deployment-checklist \\
    --to-stage @{{CI_SANDBOX_DB}}.DE_HOL_SHARED.TEAM_SKILLS/

# anyone with SELECT on the stage
cortex skill add @{{CI_SANDBOX_DB}}.DE_HOL_SHARED.TEAM_SKILLS/deployment-checklist/
```

Good when the skill should reach people across repositories, and when you want access controlled
by Snowflake role rather than repository membership. Note that this is a *copy*: consumers re-run
`cortex skill add` to pick up a new version, so it does not stay in sync the way a Git clone does.

There is also a Git-backed variant that creates a Snowflake Git repository pointing at your
Bitbucket repo, which gives you Snowflake-side governance without losing Git as the source of
truth:

```bash
cortex skill publish --from-git <your-bitbucket-repo-url> \\
    --to-repo {{CI_SANDBOX_DB}}.DE_HOL_SHARED.CI_SKILLS_REPO
```
""")

    with st.expander(":material/storefront: **3. Publish to the account catalog** — discoverable by everyone"):
        st.markdown("""
The **Skills & Plugins catalog** is Snowflake's built-in registry for sharing skills across an
account. Entries are stored as versioned Cortex Extension objects, so access is governed by
Snowflake roles and grants — no Git credentials, no file sharing.

**To publish:** Agent Settings → **Skills**, open the skill, and use the publish action. It
creates a Cortex Extension object in the account, uploads the files, commits a version, grants
read access to `PUBLIC` or a role you name, and hands back a `snow://` URI to circulate.

**To consume**, teammates either paste that URI into Agent Settings → **+** → *Add from catalog*,
or use the CLI:

```bash
cortex skill find "deployment"     # discover what is published
cortex skill add --catalog deployment-checklist
```

This is the right endpoint for a rule set that genuinely belongs to the whole organisation —
CI's naming conventions or PII rules, rather than one repo's quirks. It is also the most work to
maintain, because a published version is a thing people depend on: bump it deliberately.
""")

    st.markdown("""
**A reasonable progression:** start with option 1 while the rules are still changing weekly, and
promote to option 3 once they have stabilised and other teams start asking for them. Publishing a
rule set that is still in flux just means everyone inherits your half-finished thinking.
""")

st.space("small")

render_explanation(
    "Going further: hooks, subagents and plugins",
    """
Not part of this session — there is not time — but worth knowing they exist, because they are the
next things you will want.

A skill **guides** the agent. It is instructions, and the agent can in principle ignore them.
For a rule that must never be broken, you want something that does not depend on cooperation:

**Hooks** are shell commands that run on lifecycle events and can *block* a tool call. A
`PreToolUse` hook that refuses any `dbt` command containing `--target prod` is deterministic in a
way an instruction is not — and because it fires before execution, it works even on a machine
where dbt is not installed. Session 5 places this on the determinism ladder.

**Subagents** are Markdown-defined agents that run autonomously to completion on one task, rather
than guiding an interactive session. The same subagent can run locally before a pull request and
headlessly in CI — the same standard applied in two contexts.

**Plugins** are how you bundle all of it. A plugin is a directory with a
`.cortex-plugin/plugin.json` manifest that packages skills, hooks, subagents and MCP servers as
one versioned, validated, installable unit. Once more than one person depends on your rules, the
version number and the validation step stop being theoretical.

A worked example of all three — the skill you just built, plus a production-safety hook and a
`dbt-review` subagent, packaged as `ci-de-toolkit` — is in the repo at
`facilitator/reference-plugin/`. Take it as a starting point rather than something to build
today.

One gotcha if you do build one: if the manifest points at a `skills`, `agents` or `hooks` path
that does not exist, the **whole plugin is invalid and silently does not load** — no error, just
nothing in the Plugins panel. Create the directories first, write the manifest last, and check
your work with `cortex plugin validate <path>`.
""",
)

st.space("small")

render_explanation(
    "Troubleshooting: the skill does not appear",
    """
Two causes, in order of how often they actually happen. The skill content is rarely at fault.

**1. The session has not reloaded.** Skills are discovered when a session starts. Writing one
mid-session does not register it, and the symptom is indistinguishable from a broken skill. Start
a new session in the same workspace, or hit **↻ refresh** in Agent Settings → Skills.

**2. It went to the wrong place.** Confirm what is actually on disk:

```bash
find .snowflake/cortex/skills -type f
```

The skill must be at `<workspace>/.snowflake/cortex/skills/<name>/SKILL.md`, relative to the
folder you opened in Cortex Code Desktop. If you opened a parent directory or a second clone, the
agent may have written it somewhere the open workspace does not scan.

**Confirming it is really loaded.** Do not rely on the agent appearing to follow it — ask
directly:

> List your available skills. Is `deployment-checklist` among them, and what location was it
> loaded from?

You want location **project**. If it says **user**, the skill landed in
`~/.snowflake/cortex/skills/` instead of the project. That still works on your machine, but it
will not travel with the repo — which defeats the point of committing it.
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
        "term": "Skill description as a trigger",
        "definition": "The `description` field is what the agent matches against to decide "
                      "whether to load the skill. Write it as the situation, not the content — "
                      "\"use when asked to review code before deploying\" beats \"contains CI's "
                      "deployment rules\".",
    },
    {
        "term": "Discovery at session start",
        "definition": "Skills and plugins are enumerated when a session begins. A skill created "
                      "mid-session is not callable until the session reloads or the registry is "
                      "refreshed. The most common reason a correct skill appears broken.",
    },
    {
        "term": "Sharing paths",
        "definition": "Committing to the repo gives zero-install distribution to anyone working "
                      "in that repo. A Snowflake stage or the account catalog reaches across "
                      "repositories with access governed by Snowflake roles. Repo first, catalog "
                      "once the rules have stabilised.",
    },
])

st.space("small")

render_what_you_built([
    "A `deployment-checklist` skill with a four-file `resources/` folder, one per requirement area",
    "A findings table over three non-compliant files, including a PII leak nobody pointed it at",
    "Confirmation that the skill loaded as a **project** skill, so it travels with the repo",
    "A concrete plan for sharing it: commit to Bitbucket now, publish to the account catalog once the rules settle",
], session_num=3)
