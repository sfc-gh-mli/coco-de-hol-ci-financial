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
    5,
    "Determinism",
    "10:35 AM",
    "20 min",
    "The agreed calculation moved out of the prompt and into a stored procedure, scheduled, "
    "audited, and reproducible — including the AI function calls",
)

render_dependencies(
    requires="The reconciliation from Session 2. A checkpoint script covers you if you did not "
             "finish it. Nothing from Sessions 3 or 4 is required.",
    unlocks="Session 6 turns the same logic into a dbt model. Nothing else depends on this.",
)

st.space("small")

render_technologies_used([
    {"name": "SQL stored procedures", "description": "Agreed logic living in the database, not in a prompt", "icon": "functions"},
    {"name": "Snowflake Tasks", "description": "Scheduled execution with no dbt involvement", "icon": "schedule"},
    {"name": "Structured output", "description": "Pinned models and enforced response schemas for AI calls", "icon": "data_object"},
])

st.space("small")

st.markdown("#### Why the same prompt gives different answers")

with st.container(border=True):
    st.markdown("""
This is the concern that tends to stop enterprise adoption, and it is a legitimate one. Four
distinct causes, which need different fixes:

| Cause | What it looks like |
|---|---|
| **Sampling** | The model draws from a distribution. Two identical calls can produce different wording, a different SQL formulation, or a different classification label. |
| **Tool-order variance** | The agent decides which tables to inspect and in what order. A different path through the same problem reaches a different-looking answer. |
| **Context differences** | A session where you already discussed fee accruals behaves differently from a fresh one. Same prompt, different surrounding context. |
| **Model version drift** | The model behind `auto` changes over time. A prompt that produced correct SQL in March may not in September. |

You saw the first of these in Session 4 when the same `AI_CLASSIFY` call disagreed with itself
on the marginal notes.

None of this makes the agent unusable. It makes it unsuitable as the **execution layer** for
something a committee relies on. The answer is not to stop using it — it is to stop asking it to
recompute things that have already been agreed.
""")

st.markdown("""
##### The determinism ladder

Weakest to strongest. Each rung narrows the space the agent can vary within, and the bottom
two remove it from the calculation entirely.

| Rung | Mechanism | What it pins | Still probabilistic? |
|---|---|---|---|
| 1 | `AGENTS.md` | Facts and conventions | Yes |
| 2 | Skill | The workflow and its steps | Yes |
| 3 | `resources/` | The specific rules applied | Yes |
| 4 | Structured output schema | The shape of the answer | Yes, but constrained |
| 5 | **Hook** | Hard block — a command cannot run | **No** |
| 6 | **Stored procedure** | The calculation itself | **No** |

Rungs 1 to 4 make the agent *more likely* to do the right thing. Rungs 5 and 6 make it
*unable* to do otherwise. For anything client-facing, you want 6.
""")

st.space("small")

render_prompt(
    "Prompt 5.1",
    "Move the calculation into a stored procedure, then prove it is deterministic",
    """The reconciliation we built in Session 2 is agreed logic now. Let's take it out of the
prompt and put it in the database.

1. Create a table VENDOR_RECON_RESULTS in my DE_HOL_XX schema to hold validation output.
   Separate the columns deliberately into two groups and comment them as such:
   - PROVENANCE: a run id, a run timestamp, and the user who ran it. These SHOULD differ
     every run — that is how you tell two runs apart.
   - RESULT: fund code, period end date, the residual on each column, and a status of
     RECONCILED or BREAK. These MUST be identical for identical inputs.

2. Create a stored procedure SP_VALIDATE_VENDOR_PERFORMANCE(P_FUND_CODE VARCHAR,
   P_PERIOD_END DATE) that reads my reconciliation view, writes one row per fund-month to
   VENDOR_RECON_RESULTS, and returns a summary string.
   - Pass 'ALL' for every fund; pass NULL for every period.
   - The RETURN value must deliberately EXCLUDE the run id and timestamp, so that two runs
     over the same inputs return a byte-identical string.
   - Reference procedure parameters with a colon prefix inside the body, for example
     WHERE fund_code = :P_FUND_CODE. Without the colon Snowflake reads them as column
     identifiers and raises "invalid identifier".

3. Now prove it. Call the procedure twice with the same arguments. Show me:
   - the two return values side by side
   - a query grouping VENDOR_RECON_RESULTS by fund and period, showing that the number of
     distinct RUN_IDs is 2 while the number of distinct statuses and residuals is 1

4. Then the contrast. In a fresh context, ask yourself in plain language — no procedure —
   "reconcile the vendor performance figures and tell me which fund-months break". Do it
   twice. Show me how the two answers differ: the SQL formulation, the column selection,
   the wording, the ordering, the precision reported.

Tell me plainly what is stable in each approach and what is not.""",
)

st.warning(
    "**The colon prefix is the one thing that will bite you.** Inside a SQL procedure body, "
    "`WHERE fund_code = P_FUND_CODE` compiles and then fails at runtime with *invalid "
    "identifier* — Snowflake reads the bare name as a column. It must be `:P_FUND_CODE`.",
    icon=":material/warning:",
)

render_explanation(
    "What determinism does and does not mean",
    """
Step 3 is worth doing carefully because the naive version of this claim is wrong, and someone in
the room will notice.

**The timestamp differs on every run. That is correct behaviour.** If it did not, you could not
distinguish one run from another, and the audit trail would be worthless. Determinism is a
property of the *result*, not of the provenance. Hence the deliberate split in the table: two
groups of columns with opposite requirements, commented so the next person does not "fix" the
timestamp.

This is why the procedure's return value excludes the run id. The summary string is the thing
you can assert on in a test, diff between environments, or alert on. A return value containing a
UUID cannot be compared to anything.

**What step 4 actually shows.** The bare prompt will probably produce the *right answer* both
times — the model is capable. What it will not produce is the *same* answer. Expect variation in
which columns it selects, how it formats the residual, how many decimal places it reports,
whether it sorts by fund or by residual, and how it words the summary.

For exploration, that variation is harmless and sometimes useful. For a monthly control that
feeds a committee pack, it means you cannot diff this month against last month, cannot write a
regression test, and cannot tell a change in the data from a change in the phrasing.

**The shift in the agent's role.** Before this session the agent computed the reconciliation.
After it, the agent calls `SP_VALIDATE_VENDOR_PERFORMANCE`. The intelligence went into building
the procedure — which is where you want it, because that work was reviewed. What remains is
invocation, and invocation is cheap to verify.

That is the whole answer to "how do we get consistent results": stop asking the model to
recompute what has already been agreed.
""",
)

st.space("small")

render_prompt(
    "Prompt 5.2",
    "Make the AI function calls reproducible, and schedule the whole thing",
    """Two things to finish: the AI calls from Session 4 are not reproducible yet, and none of
this runs on a schedule.

Part A — make the AI classification reproducible.

The AI_CLASSIFY calls in Session 4 disagreed with themselves between runs on the marginal
notes. Fix that with every lever available, and explain what each one does:

1. Pin the model explicitly by name and version rather than relying on a default alias, so
   a model upgrade cannot silently change the output.
2. Use AI_COMPLETE with an enforced response schema instead of free-form output, so the
   shape of the answer is fixed even if the wording varies.
3. Set temperature to 0 where the function supports it.
4. Most important: MATERIALISE the classification once into a table rather than calling the
   AI function inside a view. Explain why a view that calls an AI function is a correctness
   problem, not just a cost problem.
5. Record the model name and version in the output table alongside each classification, so
   a future reader knows which model produced it.

Then rebuild KYC_PII_SCAN as KYC_PII_SCAN_V2 with all of that applied, run it twice into
separate tables, and show me whether the two runs now agree.

Be honest in your assessment: which of these four levers actually gives determinism, and
which only reduce variance?

Part B — schedule the deterministic validation.

Create a Snowflake Task that calls SP_VALIDATE_VENDOR_PERFORMANCE('ALL', NULL) on the 5th
of each month. Use a Snowflake Task rather than dbt so this does not depend on dbt Cloud.
Tasks are created suspended — show me the ALTER TASK ... RESUME and the SHOW TASKS output.

Then add a simple alert condition: a query that returns rows only when the most recent run
contains a BREAK that was not present in the prior run. That is the thing worth waking
someone up for — a new break, not a known one.""",
)

st.info(
    "Note the asymmetry in Part A. Pinning the model and fixing the schema **reduce variance**. "
    "Materialising the output once is the only step that gives you actual determinism — because "
    "after it, there is no model call left to vary.",
    icon=":material/lightbulb:",
)

render_explanation(
    "Why a view that calls an AI function is a correctness problem",
    """
This is the part most worth taking away, because it is a mistake that looks like good practice.

A view is normally a definition, not data. Query it twice, get the same answer twice — that
assumption is so deep that nobody states it. An AI function inside a view breaks it. Every query
re-invokes the model, so:

- two users querying the same view on the same day can see different classifications
- a dashboard refresh can change a number nobody changed
- a downstream `JOIN` against the view is joining to something unstable
- you cannot reproduce last month's report, because the view no longer returns last month's
  answer

It is also expensive — every query pays for inference again — but the cost is the lesser problem.
Cost shows up on a bill where someone will notice. Silent instability in a committee number does
not.

**The pattern:** call the AI function once, write the result to a table with the model name and
the run timestamp, and point everything downstream at the table. The AI call becomes an
ingestion step with a recorded provenance, which is exactly how you would treat any other
external input.

Stated as a rule worth keeping: **an AI function belongs in an `INSERT`, not in a `SELECT` that
others depend on.**

**On the honest assessment.** Pinning the model prevents a version upgrade from changing your
output — real and important, but it does not make two calls to the same version agree. A response
schema fixes the shape, not the content. Temperature 0 substantially reduces variance but is not
a guarantee across all functions and inputs. Only materialisation removes the variance entirely,
because after it there is nothing left to sample.

So the ladder for AI calls specifically is: pin the model, fix the schema, lower the temperature
— and then materialise, which is the step that actually settles it.

**Why a Task rather than a dbt post-hook.** A `post-hook` on a dbt model would work, and it is a
reasonable pattern once CI's dbt Cloud project is configured. A Snowflake Task depends on nothing
outside Snowflake, which means this control keeps running whether or not the dbt schedule is
healthy — and a validation check that shares a failure mode with the pipeline it validates is not
much of a control.
""",
)

st.space("small")

render_checkpoint(
    "scripts/checkpoints/after_session_05.sql",
    "If you did not finish, this creates the audit table and the validation procedure directly, "
    "then calls it twice to demonstrate the determinism. Requires the Session 2 checkpoint "
    "first. Puts you where Session 6 expects you.",
)

st.space("small")

render_key_concepts([
    {
        "term": "Determinism versus provenance",
        "definition": "A deterministic process returns the same RESULT for the same inputs. Its "
                      "provenance — run id, timestamp, who ran it — is supposed to differ every "
                      "run. Conflating the two leads people to either claim determinism they do "
                      "not have, or dismiss determinism they do.",
    },
    {
        "term": "The determinism ladder",
        "definition": "AGENTS.md pins facts, skills pin the workflow, resources pin the rules, "
                      "response schemas pin the shape. Those all reduce variance. Hooks and "
                      "stored procedures eliminate it, because they remove the model from the "
                      "decision entirely.",
    },
    {
        "term": "Colon-prefixed parameters",
        "definition": "Inside a Snowflake SQL stored procedure, parameters and variables must be "
                      "referenced as `:NAME`. A bare `NAME` is parsed as a column identifier and "
                      "raises \"invalid identifier\" at runtime. The most common error when "
                      "writing SQL procedures.",
    },
    {
        "term": "Materialise, do not re-evaluate",
        "definition": "An AI function in a view re-invokes the model on every query, so the view "
                      "is not reproducible and downstream joins are unstable. Call it once, write "
                      "to a table with the model version recorded, and point everything "
                      "downstream at the table.",
    },
    {
        "term": "Agent as invoker",
        "definition": "Once logic is agreed and encoded, the agent's job is to call it, not to "
                      "recompute it. The reasoning went into building and reviewing the "
                      "procedure. What is left is invocation, which is cheap to verify.",
    },
])

st.space("small")

render_what_you_built([
    "`VENDOR_RECON_RESULTS` — an audit table that separates stable results from varying provenance",
    "`SP_VALIDATE_VENDOR_PERFORMANCE` — the agreed calculation, deterministic by construction",
    "Proof that two runs return a byte-identical summary while the audit trail still distinguishes them",
    "A side-by-side demonstration of how the equivalent bare prompt drifts",
    "`KYC_PII_SCAN_V2` — pinned model, enforced schema, materialised once, model version recorded",
    "A monthly Task running the validation, and an alert that fires only on a NEW break",
], session_num=5)
