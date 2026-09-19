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
    1,
    "Connect & Ground",
    "9:05 AM",
    "20 min",
    "A verified sandbox connection, an AGENTS.md that encodes CI's conventions, and a working "
    "map of which bundled skills to reach for",
)

render_dependencies(
    requires="Cortex Code Desktop installed and connected — see **Getting Started**.",
    unlocks="Everything. The `AGENTS.md` you write here grounds every later session.",
)

st.space("small")

render_technologies_used([
    {"name": "Cortex Code Desktop", "description": "Agent with local file access, connected to your sandbox over SSO", "icon": "terminal"},
    {"name": "AGENTS.md", "description": "Project context the agent reads automatically, every session", "icon": "description"},
    {"name": "Bundled skills", "description": "Snowflake-specific knowledge the base model does not reliably have", "icon": "extension"},
])

st.space("small")

render_prompt(
    "Prompt 1.1",
    "Verify your environment and check optional tooling",
    """Confirm my Snowflake setup and report the results as a short table.

1. Show my current user, role, warehouse, database and schema.
2. List every table in {{CI_SANDBOX_DB}}.DE_HOL_SHARED with its row count.
3. Confirm I can create and drop an object in my own DE_HOL_XX schema.
4. Confirm the role has the SNOWFLAKE.CORTEX_USER database role, and that AI functions
   are callable — test with AI_COMPLETE using a trivial prompt.
5. List the files on the @{{CI_SANDBOX_DB}}.DE_HOL_SHARED.VENDOR_DOCS stage.

Then, separately, report which OPTIONAL local tooling is present. These affect Session 6
only — report them without trying to install or fix anything:
- Is dbt installed? Run: dbt --version
- Is there a git remote configured, and is it reachable? Run: git remote -v and git ls-remote

Tell me plainly whether I am ready for Sessions 1 to 5, and separately whether Session 6
can run hands-on.""",
)

st.warning(
    "Replace `DE_HOL_XX` with your own initials here and in every later prompt.",
    icon=":material/edit:",
)

render_explanation(
    "Why the pre-flight is split in two",
    """
Sessions 1 through 5 need exactly one thing: a working Snowflake connection with
`SNOWFLAKE.CORTEX_USER`. Session 6 additionally wants dbt and a reachable Bitbucket remote.

Keeping those two checks visibly separate is deliberate. It means a missing dbt install is
information rather than a problem, and you spend no time worrying about it during the four
sessions that do not care.

Expected shared-data row counts, so you can spot a partial load immediately:

| Table | Rows |
|---|---|
| `HOLDINGS_DAILY` | 30,972 |
| `PRICES_DAILY` | 16,020 |
| `FUND_EXPENSES_DAILY` | 1,602 |
| `INDEX_RETURNS_DAILY` | 1,068 |
| `FX_RATES_DAILY` | 801 |
| `INVESTOR_ACCOUNTS` | 420 |
| `VENDOR_FUND_PERFORMANCE_MONTHLY` | **72** |
| `SECURITY_MASTER` | 60 |
| `CASH_FLOWS` | 38 |
| `FUND_MASTER` / `BENCHMARK_COMPONENTS` / `BENCHMARK_MASTER` | 6 / 6 / 5 |
""",
)

st.space("small")

render_prompt(
    "Prompt 1.2",
    "Create AGENTS.md",
    """Create an AGENTS.md file at the root of this project. Keep it short — under 40 lines.
Only include things you could not infer from reading the code.

Snowflake environment:
- Database {{CI_SANDBOX_DB}}, warehouse {{CI_WAREHOUSE}}, role {{CI_ROLE}}
- Source data lives in DE_HOL_SHARED and is READ ONLY
- All my own objects go in DE_HOL_XX

Conventions:
- Model files, columns and aliases are snake_case
- Raw tables are always referenced through dbt's _sources.yml using source(), never by
  naming the database and schema inline in model SQL
- Database names, schema names, reporting dates and year boundaries are parameterised
  through dbt vars or env_var, never hardcoded
- Every model's primary key has not_null and unique tests
- Monetary columns are NUMBER, never FLOAT, in anything client-facing
- Percentage columns are stored as percent (1.5 means 1.5%) and suffixed _pct

Workflow:
- dbt Cloud runs this project from Bitbucket on a schedule. Never run dbt against
  production locally, and never use --target prod
- Use `dbt build`, not `dbt run`, so tests run with compilation
- Feature branches follow feature/<ticket>-<description>; PRs required before merge
- In-lab verification happens with SQL in Snowflake, not with dbt build

Agent behaviour:
- This project uses Cortex Code Desktop. Do not use the `cortex` CLI — write files directly
- Before writing SQL against a table, DESCRIBE it rather than assuming column names""",
)

render_explanation(
    "What belongs in AGENTS.md, and what does not",
    """
`AGENTS.md` is read automatically at the start of every session. It is the difference between
re-explaining your environment in every prompt and never explaining it again.

Three tests before adding a line:

**Could the model infer this on its own?** Do not write instructions explaining how dbt works
or what a window function is. It knows. Write down your database name, your naming rules, and
the exact command you want used.

**Is it stable between sessions?** Project facts belong here. "Today I am working on the
performance model" belongs in a prompt.

**Is the context worth it?** The context window is shared and finite. A 200-line `AGENTS.md`
crowds out the thing you actually asked about. Challenge every sentence.

The last line is worth noticing. *"Before writing SQL against a table, DESCRIBE it rather than
assuming column names"* is a behavioural instruction, not a fact — and it is the one that will
save you the most rework in Session 2.

The note about the `cortex` CLI is defensive: some bundled skills know about CLI commands and
can try to use them. Telling the agent up front that this is a Desktop project prevents the
detour.
""",
)

st.space("small")

render_prompt(
    "Prompt 1.3",
    "Find out which bundled skills apply to CI's work",
    """I'm a data engineer at CI Financial. We run dbt Cloud from Bitbucket against Snowflake,
and we own the pipelines behind fund performance reporting and the outbound extracts we
send to third-party vendors.

For each of these tasks, tell me which of your bundled skills would activate, and which
would send me down the wrong path:

1. A monthly performance query got slow and I need to know whether to add a clustering key
2. I need to know what breaks if I change a column in a shared model
3. I need to monitor whether the daily holdings feed is complete and on time
4. I want to attribute warehouse credits to a specific pipeline
5. I need to find and mask investor PII before an outbound extract goes to a vendor
6. I want to schedule a validation check to run after every dbt Cloud job
7. I want to deploy our dbt project

Be direct about number 7 in particular — given that we use dbt Cloud, is there a bundled
skill that sounds relevant but actually is not?""",
)

render_explanation(
    "Bundled versus custom, and the dbt trap",
    """
The answer to number 7 is the useful one. There is a bundled `dbt-projects-on-snowflake`
skill, and it sounds exactly like what CI needs. It is not.

That skill covers dbt deployed **as a Snowflake object** through the `snow dbt` CLI —
`CREATE DBT PROJECT`, `EXECUTE DBT PROJECT`. CI runs dbt Cloud from Bitbucket, which is a
completely different execution model. Asking for it will produce confident, well-formed advice
for a product you do not use.

For CI's workflow, dbt is ordinary code: the agent writes and reviews the model SQL, and dbt
Cloud executes it. No special skill required.

That is the general shape of the distinction:

- **Bundled skills** carry Snowflake product knowledge — what makes a dynamic table refresh
  incrementally, which `ACCOUNT_USAGE` view answers a cost question, how masking policies
  interact with roles. Snowflake maintains them.
- **Custom skills** carry *your* conventions — CI's naming rules, CI's pre-deployment
  checklist, CI's definition of done. Nobody can write those for you. That is Session 3.
- **Neither** is needed for standard SQL, Python or dbt syntax. A skill that re-teaches those
  only burns context.

The shortlist for CI, with a note on when each earns its place, is in
`skills_reference/recommended-bundled-skills.md`. Take it with you — it is more useful after
the workshop than during it.
""",
)

st.space("small")

render_key_concepts([
    {
        "term": "AGENTS.md",
        "definition": "A Markdown file at the project root that the agent reads at the start of "
                      "every session. Holds stable project facts and conventions the model "
                      "cannot infer. The single highest-leverage file in an agentic workflow, "
                      "and the cheapest to write.",
    },
    {
        "term": "Skill",
        "definition": "A folder containing a `SKILL.md` with YAML frontmatter and instructions. "
                      "The `description` field is what the agent matches against to decide "
                      "whether to load it, so it should read as a trigger — \"use this when...\" "
                      "Skills encode repeatable multi-step workflows.",
    },
    {
        "term": "Bundled versus custom skill",
        "definition": "Bundled skills carry Snowflake product knowledge and are maintained by "
                      "Snowflake. Custom skills carry your team's choices. The test: if you "
                      "catch yourself starting a prompt with \"remember, we always...\", that is "
                      "a custom skill waiting to be written.",
    },
    {
        "term": "Workspace trust",
        "definition": "Project-scoped skills and plugins only activate in a trusted workspace. "
                      "An untrusted workspace shows them in the Plugins panel but leaves them "
                      "disabled, which looks exactly like a skill that does not work.",
    },
    {
        "term": "SNOWFLAKE.CORTEX_USER",
        "definition": "The database role that permits Cortex AI function calls. Available to "
                      "PUBLIC by default, but frequently revoked in enterprise accounts. "
                      "Without it, Session 4 cannot run.",
    },
])

st.space("small")

render_what_you_built([
    "A verified connection to the CI sandbox with the right role and warehouse",
    "Confirmed read access to 12 shared tables and write access to your own schema",
    "A known answer on whether Session 6 runs hands-on or as a walkthrough",
    "`AGENTS.md` — CI's conventions, encoded once instead of re-explained every session",
    "A map of which bundled skills apply to CI's work, and which one to deliberately avoid",
], session_num=1)
