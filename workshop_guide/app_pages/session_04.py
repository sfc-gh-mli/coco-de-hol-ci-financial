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
    4,
    "AI Functions for Data Engineering",
    "10:20 AM",
    "15 min",
    "Reconciliation breaks triaged by likely cause, and a PII scan over free-text notes that "
    "proves the outbound vendor extract is safe",
)

render_dependencies(
    requires="`SNOWFLAKE.CORTEX_USER` on your role. Prompt 4.1 uses the reconciliation from "
             "Session 2 — use the checkpoint script if you did not finish it.",
    unlocks="Session 5 resolves the non-determinism you are about to see in the AI output. "
            "Nothing else depends on this session.",
)

st.space("small")

render_technologies_used([
    {"name": "AI_CLASSIFY", "description": "Categorise rows against labels you define, in SQL", "icon": "label"},
    {"name": "AI_REDACT", "description": "Remove personal identifiers from free text", "icon": "visibility_off"},
    {"name": "AI_COMPLETE", "description": "Structured output with an enforced response schema", "icon": "auto_awesome"},
])

st.space("small")

st.markdown("#### Where AI functions actually help a data engineer")

with st.container(border=True):
    st.markdown("""
Not everywhere. The reconciliation in Session 2 was arithmetic, and arithmetic belongs in SQL —
an LLM would have been slower, more expensive and less reliable at it.

AI functions earn their place on the parts of data engineering that are **not** arithmetic:

- text that has structure but no schema — advisor notes, vendor documents, incident logs
- classification where the rule is a judgement rather than a threshold
- work that does not scale by reading harder, because there are three hundred documents

You already used one in Session 2. `AI_EXTRACT` turned three pages of vendor prose into a table
you could diff. This session does two more, both on work CI has to do anyway.
""")

st.space("small")

render_prompt(
    "Prompt 4.1",
    "Triage the reconciliation breaks by likely cause",
    """I want to turn the reconciliation residuals into a triage queue instead of a wall of
numbers.

Build a table BREAK_TRIAGE in my DE_HOL_XX schema, from the residual view I created in
Session 2 (V_VENDOR_RECON_RESIDUALS, or your equivalent).

For every fund-month, assemble a short text description of the evidence: the residual in
basis points on each column, whether a cash flow occurred that month and on which day,
whether a distribution was paid, the number of business days in the month, and the size of
the return.

Then use AI_CLASSIFY over that description to assign a likely root cause from exactly
these categories:
- FX_TIMING
- FLOW_TIMING
- FEE_BASIS
- BENCHMARK_CONSTRUCTION
- PERFORMANCE_FEE
- NO_BREAK

Include the reasoning alongside the classification, and a confidence level.

Then show me two things:
1. A summary: count of fund-months per category.
2. The rows classified as anything other than NO_BREAK, with the evidence and the
   classification side by side, so I can judge whether the classification is sensible.

Finally: run the exact same classification a second time into a separate table, and show
me any row where the two runs disagree.""",
)

st.info(
    "That last instruction is not a bug hunt — it is the setup for the next session. Note what "
    "you see and hold the question.",
    icon=":material/pin:",
)

render_explanation(
    "Why classify a number you could threshold",
    """
A fair objection: you already know which rule causes which break, and a `CASE` statement would
be faster, cheaper and deterministic. For *this* dataset, that objection is correct — and you
should prefer the `CASE` statement.

What makes the pattern useful is what happens next month, when Meridian changes something and
the break has a cause that is not in your `CASE` statement. A threshold rule returns
`UNKNOWN`. A classifier returns a reasoned guess and a confidence, which is a better starting
point for a human who has forty rows to work through before a committee meeting.

So the honest framing is: **AI_CLASSIFY is for triage, not for truth.** It ranks and routes;
the SQL reconciliation decides. Anyone who inverts that — letting the classification stand as
the finding — has built something worse than the `CASE` statement.

Two things to notice in the output:

**Include the evidence, not the raw number.** Handing the model `net_resid_bps = 74.8` gives it
nothing to reason from. Handing it *"residual 74.8 bps; a distribution was paid on the last
business day; no subscription or redemption this month"* gives it something a person could also
reason from. Feature engineering for a classifier is still feature engineering.

**The two runs will not fully agree.** On the clear-cut rows they will. On the marginal ones —
low residual, ambiguous evidence — you will see the classification move. That is not a defect in
the function; it is what a sampled model does. It is also completely unacceptable in a control
that compliance relies on, which is the problem Session 5 exists to solve.
""",
)

st.space("small")

render_prompt(
    "Prompt 4.2",
    "Prove the outbound vendor extract carries no investor PII",
    """In Session 3 the deployment checklist flagged that
sql/deploy/02_investor_extract_to_vendor.sql sends SELECT * from INVESTOR_ACCOUNTS to
Meridian. Let's quantify the exposure and then fix it properly.

INVESTOR_ACCOUNTS.KYC_NOTES is free-text advisor commentary. Some rows embed personal
identifiers mid-sentence; most do not.

1. First establish the baseline a regex would give you. Write a pattern-matching query that
   flags KYC_NOTES containing an email address or a phone number. Report how many rows it
   catches.

2. Now use AI_CLASSIFY over KYC_NOTES to classify each note as CONTAINS_PII or NO_PII,
   with the identifier type where present. Materialise this as KYC_PII_SCAN in my schema.

3. Compare the two. Show me rows the AI flagged that the regex missed, with the note text,
   so I can see what kind of identifier slipped through a pattern match.

4. Use AI_REDACT to produce a redacted version of KYC_NOTES. Show ten before-and-after
   pairs including at least three that contained PII.

5. Rewrite sql/deploy/02_investor_extract_to_vendor.sql properly:
   - enumerate columns explicitly instead of SELECT *
   - drop the direct identifier columns entirely — Meridian needs account-level units and
     fund, not investor identity
   - use the redacted notes if notes are needed at all, and if they are not, omit them
   - parameterise the schema and the reporting date
   Explain in a comment at the top of the file what changed and why.

6. Write me a one-paragraph summary I could send to compliance stating what was exposed,
   how many records, and what the fix was.""",
)

render_explanation(
    "Why a regex is not enough, and what the numbers show",
    """
Step 1 exists so that step 3 means something. Without a baseline, "the AI found PII" is a claim;
with one, you can say how much a pattern match would have missed and point at the examples.

A regex catches formatted identifiers — an email has an `@`, a phone number has a predictable
shape. It does not catch:

- a person's name in a sentence, which has no distinguishing format
- a partial identifier described rather than written, like a reference to the last digits of a
  government ID
- a street address embedded in prose
- a beneficiary or joint account holder named in passing

Around 46% of the notes in this dataset carry some identifier. A pattern match on emails and
phone numbers finds a good portion and misses roughly 80 rows, almost all of them names in
prose. Those are the rows worth reading aloud.

**Why the mix matters.** If every note contained PII, "flag everything" would score perfectly
and the exercise would prove nothing. The dataset is deliberately mixed so that precision is a
real constraint — over-flagging is a cost, because a reviewer who is told everything is sensitive
stops reviewing.

**On `AI_REDACT` versus a masking policy.** They solve different problems and CI needs both. A
masking policy is deterministic, enforced at query time, and the right control for a column you
know holds an email address. `AI_REDACT` handles the case a masking policy cannot express: a
free-text column where the identifier's location is not known in advance. Use policies for
structured PII and `AI_REDACT` for prose.

**The finding is the process, not the file.** The interesting sentence for compliance is not
"we redacted the notes". It is that a `SELECT *` written years ago silently widened an outbound
extract as columns were added, and nobody noticed until a skill checked for it. The fix is
enumerating columns; the control is the check running every time.
""",
)

st.space("small")

render_checkpoint(
    "scripts/checkpoints/after_session_02.sql",
    "Prompt 4.1 needs the reconciliation from Session 2. If you do not have "
    "`V_VENDOR_RECON_RESIDUALS`, run this first — it creates it in about 30 seconds. "
    "Prompt 4.2 needs nothing from Session 2 and can be done in either order.",
)

st.space("small")

render_key_concepts([
    {
        "term": "AI_CLASSIFY",
        "definition": "Assigns each row to one of a set of labels you define, in SQL. Best where "
                      "the input is text and the decision is a judgement. Not a replacement for "
                      "a deterministic rule when a deterministic rule exists — it is for the "
                      "long tail the rule does not cover.",
    },
    {
        "term": "AI_REDACT",
        "definition": "Removes personal identifiers from free text. Complements masking policies "
                      "rather than replacing them: use a policy for a column you know holds an "
                      "identifier, and AI_REDACT for prose where you cannot predict where the "
                      "identifier will be.",
    },
    {
        "term": "Evidence assembly",
        "definition": "Giving a classifier a description a human could also reason from, instead "
                      "of raw numbers. \"Residual 74.8 bps, distribution paid on the last "
                      "business day, no other flows\" classifies well. \"74.8\" does not. This is "
                      "feature engineering, and it is most of the work.",
    },
    {
        "term": "Triage versus truth",
        "definition": "An AI classification ranks and routes; the deterministic calculation "
                      "decides. Inverting this — treating a classification as the finding — "
                      "produces something less reliable than the CASE statement it replaced.",
    },
    {
        "term": "Non-determinism in SQL",
        "definition": "An AI function inside a query is a sampled model call. Two runs over "
                      "identical rows can return different labels, which breaks the assumption "
                      "that a view returns the same answer twice. Session 5 addresses this "
                      "directly.",
    },
])

st.space("small")

render_what_you_built([
    "`BREAK_TRIAGE` — reconciliation residuals classified by likely root cause with reasoning and confidence",
    "Evidence that the same classification run twice does not always agree",
    "`KYC_PII_SCAN` — every free-text note classified for PII, with the identifier type",
    "A measured comparison showing what a regex baseline missed, and why",
    "A rewritten outbound vendor extract with columns enumerated, identifiers dropped, and the schema parameterised",
    "A compliance-ready summary of what was exposed and what the fix was",
], session_num=4)
