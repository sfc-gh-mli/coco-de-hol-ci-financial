import streamlit as st

from components import (
    render_checkpoint,
    render_dependencies,
    render_explanation,
    render_key_concepts,
    render_prompt,
    render_session_header,
    render_technologies_used,
    render_what_you_built,
)

render_session_header(
    6,
    "dbt to Production",
    "10:55 AM",
    "15 min",
    "The validated reconciliation as a dbt model with schema tests, verified in Snowflake and "
    "committed for dbt Cloud to run on schedule",
)

st.info(
    "**This is a stretch session, and nothing depends on it.** Sessions 1 through 5 stand "
    "entirely on their own. If the pre-flight check in Session 1 showed that dbt or the "
    "Bitbucket remote is not ready, this runs as a walkthrough instead — you lose nothing.",
    icon=":material/flag:",
)

render_dependencies(
    requires="The reconciliation logic from Session 2 (or its checkpoint). dbt and a reachable "
             "remote are **optional** — see the three tiers below.",
    unlocks="Nothing. This is the last session by design.",
)

st.space("small")

render_technologies_used([
    {"name": "dbt models & tests", "description": "The transformation as version-controlled code with assertions", "icon": "build_circle"},
    {"name": "Bitbucket → dbt Cloud", "description": "CI's actual execution path: commit to the repo, dbt Cloud runs it", "icon": "cloud_upload"},
    {"name": "SQL verification", "description": "Checking the numbers in Snowflake, because dbt Cloud runs later", "icon": "fact_check"},
])

st.space("small")

st.markdown("#### How this maps to CI's real setup")

with st.container(border=True):
    st.markdown("""
CI authors models locally in Cortex Code Desktop, commits to **Bitbucket**, and **dbt Cloud** runs
the project on a schedule. The agent writes and reviews the model; dbt Cloud executes it.

Two honest caveats:

**This lab uses the repo's own `dbt/` directory as a stand-in** for CI's Bitbucket repo. To use
any of this for real, point the remote at CI's repo and move the `models/` directory across. The
model SQL itself is unchanged by that.

**dbt Cloud runs on a schedule, so nothing gets built in this room.** That is why verification
here is SQL in Snowflake: the agent materialises the compiled `SELECT` into your own schema so
you can check the numbers now, and the committed model is what dbt Cloud picks up later.
""")

st.markdown("""
##### Three tiers — find yours and stop there

| Tier | You have | What you do | What you end with |
|---|---|---|---|
| **A** | dbt installed, remote reachable | Write the model, `dbt build`, push the branch | Model built and pushed |
| **B** | Neither, or only one | Write the model, run the compiled SQL in Snowflake, commit locally | Model written, numbers verified, commit staged |
| **C** | Following along | Watch the facilitator, read the generated model | The model and the reconciliation result |

All three tiers end with the same reviewable artifact. **Writing the model file needs no dbt
install** — only running it does.
""")

st.space("small")

render_prompt(
    "Prompt 6.1",
    "Build the model and its tests",
    """Turn the validated reconciliation into a dbt model in this project.

Create models/marts/fund_performance_monthly.sql implementing the methodology we confirmed
in Session 2. Requirements, all of which come from AGENTS.md:

- Reference every raw table through {{ source('ci_shared', '<table>') }}. Never name the
  database or schema inline.
- Take the schema and reporting year from vars, not hardcoded values — dbt_project.yml
  already defines source_schema and reporting_year.
- snake_case throughout. Percentage columns suffixed _pct, currency amounts _cad.
- Use CTEs with names that say what they hold, in the order the calculation flows.
- Comment each CTE that implements a specific methodology rule with what that rule is and
  why the vendor does it that way.

Also create models/marts/_schema.yml with:
- a description for the model and for every column
- not_null and unique tests on the grain, which is fund_code plus period_end_date — note
  this needs a combination-of-columns test, not a unique test on either column alone
- a relationships test from fund_code to the fund_master source
- accepted_values on any status or category column
- a not_null test on every return column

Do not run anything yet. Show me the files first.""",
)

render_explanation(
    "The grain test is the one people get wrong",
    """
`fund_code` is not unique in this model — there are twelve rows per fund. `period_end_date` is not
unique either — there are six rows per month. The grain is the *combination*, which standard dbt
`unique` tests cannot express on their own.

The usual answers are `dbt_utils.unique_combination_of_columns`, or a singular test in `tests/`
that groups by both columns and asserts no group has more than one row. Either is fine. What is
not fine is a `unique` test on `fund_code`, which will fail immediately, or no grain test at all,
which is worse because it passes.

This matters beyond the syntax. A silent grain violation is how a fanned-out join gets into a
committee pack — the numbers look plausible, every row is individually correct, and the totals
are double-counted. The grain test is the assertion that catches it.

**On the comments.** Asking the agent to explain *why* the vendor does something, not just what
the SQL does, is deliberate. In six months the person reading this model will not have attended
this workshop. `-- Modified Dietz: weights each flow by the fraction of the month remaining` is
worth ten times `-- calculate gross return`.
""",
)

st.space("small")

render_prompt(
    "Prompt 6.2",
    "Verify in Snowflake, then commit for dbt Cloud",
    """Now verify and commit. Adapt to what I actually have available — check first rather
than assuming.

Verification, which does NOT require dbt:

1. Compile the model's SQL and materialise it as a table FUND_PERFORMANCE_MONTHLY_CHECK in
   my DE_HOL_XX schema, substituting the var values directly.
2. Reconcile it against the vendor target the same way we did in Session 2: residuals per
   column in basis points, with a RECONCILED or BREAK status per row.
3. Confirm the result matches what my Session 2 reconciliation produced. If it does not,
   the model has drifted from the logic we validated — tell me exactly where.
4. Independently check the grain: confirm one row per fund per month and no duplicates.

If dbt IS available, additionally:
5. Run dbt build --select fund_performance_monthly --project-dir dbt/ and report the
   result, including which tests ran and which passed.

Commit:

6. Create a branch following AGENTS.md's naming convention, for a ticket reference of
   DATA-1042.
7. Stage the model, the schema tests, and the reconstructed methodology document from
   Session 2. Show me the diff before committing.
8. Write a commit message that explains WHY this model exists — that it reconciles
   vendor-supplied performance figures against CI-derived values and documents five
   methodology discrepancies — not just that it adds a model.
9. Check whether a remote is configured and reachable. If it is, show me the push command
   but do NOT run it. If it is not, stop at the local commit and tell me so plainly.

Do not attempt to install dbt or configure a remote. Report what is there and work with it.""",
)

st.info(
    "**Do not debug a dbt profile in the room.** If `dbt build` fails, you are on tier B — the "
    "compiled SQL verification in steps 1 to 4 gives you the same confidence in the numbers, and "
    "dbt Cloud will run the model from Bitbucket regardless. The artifact is the committed model.",
    icon=":material/timer_off:",
)

render_explanation(
    "Why verification and execution are separated here",
    """
In most dbt workshops `dbt build` is both the execution and the proof. That works when dbt runs
locally. It does not describe CI's setup, where dbt Cloud executes on a schedule from Bitbucket
and the person authoring the model never runs it.

So the two concerns are split on purpose:

- **Verification** is *are the numbers right?* — answered by materialising the compiled SQL and
  reconciling it against the target, in Snowflake, now.
- **Execution** is *does it run in production?* — answered by dbt Cloud, later, from the committed
  branch.

That separation is not a workaround for the lab. It is closer to how CI actually works, and it is
a better habit: a `dbt build` that succeeds tells you the SQL is valid and the tests pass. It does
not tell you the numbers are right. Step 3 — reconciling against the independently validated
Session 2 result — is the check that catches a model that compiles cleanly and computes the wrong
thing.

**Step 3 is the one worth insisting on.** It is entirely possible for the agent to write a model
that runs, passes every schema test, and quietly diverges from the methodology you spent 35
minutes establishing. Comparing it back to the Session 2 reconciliation is the only thing that
catches that, and it takes one query.

**On the commit message.** *"Add fund performance model"* tells a future reader nothing. *"Add
fund_performance_monthly reconciling Meridian-supplied figures against CI-derived values;
documents five methodology discrepancies (DATA-1042)"* tells them why the file exists and where
to look for the reasoning. The agent will write the first kind unless asked for the second.
""",
)

st.space("small")

render_checkpoint(
    "scripts/checkpoints/after_session_02.sql",
    "This session needs the Session 2 reconciliation to verify against. If you do not have it, "
    "run this first — then the comparison in step 3 has something to compare to.",
)

st.space("small")

render_key_concepts([
    {
        "term": "Authoring versus execution",
        "definition": "With dbt Cloud, the person writing the model is not the process running "
                      "it. The agent writes and reviews; dbt Cloud executes on a schedule from "
                      "the repo. Verification has to be possible without executing, which means "
                      "checking the compiled SQL against a known-good result.",
    },
    {
        "term": "Grain test",
        "definition": "An assertion that the table has exactly one row per logical entity. Where "
                      "the grain is a column combination, a single-column `unique` test cannot "
                      "express it — use a combination test or a singular test. Without one, a "
                      "fanned-out join produces plausible, double-counted totals.",
    },
    {
        "term": "Compiled SQL verification",
        "definition": "Rendering the model's SQL with vars substituted and running it directly, "
                      "to check the numbers without a dbt execution environment. Works on any "
                      "machine with a Snowflake connection.",
    },
    {
        "term": "Parameterisation over hardcoding",
        "definition": "Schema names, reporting periods and entity lists come from vars or "
                      "env_var so the same code runs in sandbox and production unchanged. This "
                      "is the rule the deployment checklist from Session 3 checks for, and the "
                      "one the inherited scripts broke most often.",
    },
])

st.space("small")

render_what_you_built([
    "`fund_performance_monthly.sql` — the validated methodology as a dbt model, parameterised and commented per rule",
    "`_schema.yml` with a correct grain test on the fund plus period combination, relationships and not_null tests",
    "`FUND_PERFORMANCE_MONTHLY_CHECK` — the compiled model materialised and reconciled in Snowflake",
    "Confirmation that the model matches the Session 2 reconciliation rather than merely compiling",
    "A feature branch and a commit that explains why the model exists, ready for dbt Cloud",
], session_num=6)

st.space("medium")

st.markdown("##### That's the workshop")

with st.container(border=True):
    st.markdown("""
You started with a vendor dataset nobody could explain and a three-page document that mostly
described something else. You finish with:

- a reconstructed methodology, proven row by row, with **five documented discrepancies** between
  what the vendor says it does and what it does
- a skill that encodes CI's deployment standards and travels with the repo
- a PII exposure found, measured, and fixed in an extract that leaves CI every month
- a validation procedure that returns the same answer every time it runs, on a schedule

All of it on data CI already had, in a little over two hours.

The transferable part is not any single artifact. It is the loop: let the agent execute, measure
the residual, discard what does not survive, and then move whatever you agreed on out of the
prompt and into the database.
""")
