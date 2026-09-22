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
    4,
    "AI Functions for Data Engineering",
    "10:20 AM",
    "15 min",
    "A PII scan over free-text advisor notes that proves the outbound vendor extract is unsafe, "
    "measured against a regex baseline, then fixed",
)

render_dependencies(
    requires="`SNOWFLAKE.CORTEX_USER` on your role. Nothing else — this session reads "
             "`INVESTOR_ACCOUNTS` from the shared schema, so it does not depend on Session 2 or "
             "Session 3 having finished.",
    unlocks="Session 5 resolves the non-determinism you are about to see in the AI output. "
            "Nothing else depends on this session.",
)

st.space("small")

render_technologies_used([
    {"name": "AI_CLASSIFY", "description": "Categorise rows against labels you define, in SQL", "icon": "label"},
    {"name": "AI_REDACT", "description": "Remove personal identifiers from free text", "icon": "visibility_off"},
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
you could diff. This session does one more, on a problem Session 3 just handed you.
""")

st.space("small")

render_prompt(
    "Prompt 4.1",
    "Prove the outbound vendor extract carries no investor PII",
    """The file sql/deploy/02_investor_extract_to_vendor.sql sends SELECT * from
INVESTOR_ACCOUNTS to Meridian every month. Let's quantify the exposure and then fix it
properly.

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
   how many records, and what the fix was.

7. Last thing, and do not fix it: re-run the exact same AI_CLASSIFY step from step 2 into a
   second table KYC_PII_SCAN_RUN2. Show me the count of notes where the two runs disagree,
   and two examples. I want to see it, not solve it.""",
)

st.info(
    "Step 7 is not a bug hunt — it is the setup for the next session. Note what you see and hold "
    "the question.",
    icon=":material/pin:",
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

render_explanation(
    "Take-home: the same pattern for reconciliation breaks",
    """
Nothing to build here — 15 minutes does not stretch that far — but this is the other obvious place
CI can use `AI_CLASSIFY`, and it is worth two minutes of thought before you leave.

You have a residual view from Session 2: a wall of numbers where a handful of fund-months are off
by a few basis points. Turning that into a **triage queue** means assembling a short text
description of the evidence for each break — *"residual 74.8 bps; a distribution was paid on the
last business day; no subscription or redemption this month"* — and classifying it against
categories you define: `FX_TIMING`, `FLOW_TIMING`, `FEE_BASIS`, `PERFORMANCE_FEE`, `NO_BREAK`.

Two things make the difference between that working and not working:

**Hand the model evidence, not the raw number.** `net_resid_bps = 74.8` gives it nothing to reason
from. The sentence above gives it something a person could also reason from. Feature engineering
for a classifier is still feature engineering, and it is most of the work.

**`AI_CLASSIFY` is for triage, not for truth.** A `CASE` statement over known thresholds is
faster, cheaper and deterministic, and for the breaks you already understand you should prefer it.
The classifier earns its place on the long tail — next month, when Meridian changes something and
the cause is not in your `CASE` statement. A threshold rule returns `UNKNOWN`; a classifier
returns a reasoned guess and a confidence, which is a better starting point for whoever has forty
rows to work through before a committee meeting.

What must not happen is the inversion: letting the classification stand as the finding. The
classifier ranks and routes; the SQL reconciliation decides. Get that backwards and you have built
something less reliable than the `CASE` statement you replaced.
""",
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
        "term": "Regex baseline",
        "definition": "Measuring a pattern match before reaching for an AI function, so the "
                      "comparison means something. Without a baseline, \"the AI found PII\" is a "
                      "claim. With one, you can say how many rows a regex missed and point at "
                      "them.",
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
    "`KYC_PII_SCAN` — every free-text advisor note classified for PII, with the identifier type",
    "A measured comparison showing what a regex baseline missed, and why",
    "A redacted version of the notes column, with before-and-after pairs",
    "A rewritten outbound vendor extract with columns enumerated, identifiers dropped, and the schema parameterised",
    "A compliance-ready summary of what was exposed and what the fix was",
    "Evidence that the same classification run twice does not always agree — the problem Session 5 solves",
], session_num=4)
