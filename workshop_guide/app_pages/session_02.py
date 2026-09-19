from pathlib import Path

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

_DATA = Path(__file__).resolve().parent.parent.parent / "data"

render_session_header(
    2,
    "Reverse-Engineer the Vendor Dataset",
    "9:25 AM",
    "35 min",
    "A reconstructed methodology for the vendor's performance figures, with proving SQL per "
    "rule, and a diff against what the vendor says it does",
)

render_dependencies(
    requires="A working Snowflake connection and `AGENTS.md` from Session 1.",
    unlocks="Session 5 wraps the reconciliation you build here in a stored procedure. "
            "Session 6 turns it into a dbt model. A checkpoint script covers you either way.",
)

st.space("small")

render_technologies_used([
    {"name": "Code execution", "description": "The agent runs SQL, measures residuals, and discards its own hypotheses", "icon": "play_circle"},
    {"name": "Residual analysis", "description": "Reading what a difference correlates with, instead of guessing formulas", "icon": "insights"},
    {"name": "AI_PARSE_DOCUMENT / AI_EXTRACT", "description": "Turning a prose PDF into structured claims you can diff", "icon": "auto_awesome"},
])

st.space("small")

st.markdown("#### The situation")

with st.container(border=True):
    st.markdown("""
Meridian Performance Analytics returns `VENDOR_FUND_PERFORMANCE_MONTHLY` every month: 72 rows,
six funds, twelve months of 2025. NAV, gross and net returns, benchmark returns, excess returns,
expense ratios.

Those numbers go to clients, to the investment committee, and into regulatory filings. CI has
to be able to defend every one of them.

What CI has to work with:

- **11 source tables** in `DE_HOL_SHARED` — the same holdings, prices, FX rates, cash flows and
  fee accruals CI sends Meridian each day.
- **A three-page methodology statement** describing how the numbers are produced. It is
  confident, prose-heavy, and vague in exactly the places that matter.

Nobody at CI knows the formulas. The person who onboarded Meridian has left.
""")

col1, col2 = st.columns(2)
with col1:
    _pdf = _DATA / "documents" / "meridian_performance_methodology_2025.pdf"
    if _pdf.exists():
        st.download_button(
            ":material/download: Meridian methodology statement (PDF)",
            data=_pdf.read_bytes(),
            file_name=_pdf.name,
            mime="application/pdf",
            use_container_width=True,
        )
with col2:
    _zip = _DATA / "ci_fund_data.zip"
    if _zip.exists():
        st.download_button(
            ":material/download: Full dataset (CSV + PDF)",
            data=_zip.read_bytes(),
            file_name=_zip.name,
            mime="application/zip",
            use_container_width=True,
        )

st.caption(
    "The data is already loaded in `DE_HOL_SHARED` — these downloads are for reference and for "
    "re-running any of this later. The PDF is also staged at `@DE_HOL_SHARED.VENDOR_DOCS` for "
    "prompt 2.4."
)

st.space("small")

render_prompt(
    "Prompt 2.1",
    "Profile both sides before computing anything",
    """I need to reverse-engineer how a vendor produced a monthly performance dataset.

The target is {{CI_SANDBOX_DB}}.DE_HOL_SHARED.VENDOR_FUND_PERFORMANCE_MONTHLY.
The source tables CI sends the vendor are the other tables in that same schema.

Before computing any returns:

1. DESCRIBE the target and every source table. Report the grain of each.
2. For the target, profile each numeric column: min, max, mean, and how many distinct
   values. Note anything that looks like a unit convention (percent vs decimal).
3. Work out which source tables must feed which target column, based on structure alone.
   State what is IMPLIED, and be explicit about what you cannot determine yet.
4. Check the date coverage of every source table. Flag anything that does not line up with
   the target's 2025 reporting periods, and tell me why you think it is there.
5. Reconcile the reported NET_FLOWS column against CASH_FLOWS. Tell me exactly what it
   does and does not appear to include.

Do not attempt to reproduce any return figure yet. I want the map first.""",
)

render_explanation(
    "Why profiling first is not a warm-up exercise",
    """
Two of the five steps above will pay off directly, and it is worth knowing which before you
move on.

**Step 4 — date coverage.** The source tables start before January 2025. That is not sloppy
data preparation; it is there because something in the calculation needs a day that falls
outside the reporting period. If you notice it now, you will save yourself a confusing half
hour later. If you inner-join on the reporting period, you will silently drop a row and the
residual will look like a calculation error rather than a join error.

**Step 5 — `NET_FLOWS`.** The target reports a flow figure. `CASH_FLOWS` has three flow types.
Whether `NET_FLOWS` equals all three, or some of them, is a directly checkable fact — no
return maths required — and the answer constrains everything downstream.

More generally: the agent is good at this and it is cheap. Establishing the grain and unit
conventions up front prevents the whole class of errors where a residual turns out to be a
factor of 100, or a fanned-out join, rather than a methodology difference.
""",
)

st.space("small")

render_prompt(
    "Prompt 2.2",
    "First hypothesis, and its residual",
    """Now reproduce ENDING_NAV, the simplest target column, from source data.

Start with the obvious construction: for each fund and date, value every holding at that
day's closing price, convert to CAD at that day's FX rate, and sum.

Then, and this is the important part:

1. Create a view in my DE_HOL_XX schema holding your computed daily NAV.
2. Join your month-end values to the target's ENDING_NAV.
3. Give me a RESIDUAL TABLE, not a verdict: one row per fund-month, with your value, the
   vendor's value, the difference in dollars, and the difference in basis points.
4. Report the distribution of the residual — min, max, median, and how it varies by fund.

Do not tell me whether it matches. Do not adjust anything to make it match. I want to see
the residual and decide for myself what it is telling us.""",
)

st.info(
    "**Resist the agent's instinct to conclude.** If it reports \"the values broadly match with "
    "minor rounding differences\", push back: ask for the residual table. The habit being built "
    "here is measuring the gap, not assessing it.",
    icon=":material/psychology:",
)

render_explanation(
    "Residual, not verdict",
    """
This is the single most transferable technique in the workshop, and it is why code execution
matters rather than just code generation.

An agent asked *"is my calculation right?"* will give you an opinion. An agent asked *"compute
both and show me the difference"* gives you evidence. The difference in outcome is large,
because a residual has structure and an opinion does not.

A residual that is:

- **constant across all rows** → a units or scaling difference
- **zero for most rows, large for a few** → a conditional rule that only applies sometimes
- **proportional to something else** → that something is in the formula
- **always the same sign** → an omitted term, not a timing difference
- **random noise at machine precision** → you have it right

You are about to get the third of these. The residual on `ENDING_NAV` is small — a few basis
points — which is exactly the range where it is tempting to call it rounding and move on. It is
not rounding. Basis points on a $735 million fund is real money, and more importantly, the
pattern in those basis points tells you what the vendor did.
""",
)

st.space("small")

render_prompt(
    "Prompt 2.3",
    "Read the signature, then iterate",
    """The residual is not random. Let's find out what it is correlated with.

For the NAV residual from the last step, test each of these candidate drivers and report
the correlation coefficient for each:
- the day-over-day change in each FX rate
- the proportion of each fund's market value held in non-CAD securities
- the size of any cash flow that month
- which fund it is

Then form a hypothesis about what the vendor did differently, change ONE thing, and
re-measure. Report the residual before and after.

Repeat that loop until the NAV residual is at machine precision. Then do the same for
GROSS_RETURN_PCT and NET_RETURN_PCT, using the same discipline:
- compute your version
- measure the residual
- correlate the residual against candidate drivers (flow size, flow timing within the
  month, number of business days in the month, whether a distribution was paid, the
  magnitude of the return itself)
- change one thing, re-measure

For every rule you establish, show me the SQL that proves it and the residual before and
after. If a fund-month will not reconcile no matter what you try, leave it and tell me
which one — do not bend the formula to fit it.""",
)

st.warning(
    "**One rule at a time.** If the agent changes three things at once and the residual "
    "improves, you have learned nothing about which of the three was right. Make it re-measure "
    "after each single change.",
    icon=":material/warning:",
)

render_explanation(
    "What you are likely to find, and the one row that will not fit",
    """
There are several distinct methodology choices buried in these numbers, and they differ in
magnitude by more than two orders of magnitude. The loud ones are easy; the quiet ones need the
correlation step.

Expect the residual to shrink in stages rather than collapse at once. That staging is the
feedback loop — each time you fix one rule, the next one becomes visible underneath it.

**The correlations are the whole game.** A residual that tracks the daily FX move tells you
something about *when* the vendor priced currency. A residual that appears only in months with
a mid-month cash flow tells you something about *how* flows are weighted. A residual that
tracks the number of business days in the month tells you something about the fee basis. None
of that is guessable. All of it is measurable.

**One fund-month will not reconcile.** This is deliberate, and how you handle it matters more
than whether you explain it.

The wrong move is to keep adjusting the formula until all 72 rows fit. You can get there, and
what you will have is an expression that reconciles perfectly and describes nothing real.

The right move is to notice that one row is different *in kind*, exclude it, reconcile the
other 71 cleanly, and raise the outlier as a question for the vendor. Segmenting before
generalising is the skill; a single global formula that fits every row of real-world vendor
data usually means you have overfitted.

If you find yourself adding a term that applies to exactly one fund in exactly one month,
stop — that is not a rule, that is a finding.
""",
)

st.space("small")

render_prompt(
    "Prompt 2.4",
    "Extract the vendor's stated claims, then diff against reality",
    """Now let's check what the vendor SAYS it does against what we just proved it does.

The methodology statement is staged at @{{CI_SANDBOX_DB}}.DE_HOL_SHARED.VENDOR_DOCS as
meridian_performance_methodology_2025.pdf.

1. Use AI_PARSE_DOCUMENT to read the PDF into text.
2. Use AI_EXTRACT to pull out every substantive METHODOLOGY CLAIM — statements about how a
   number is calculated. Ignore boilerplate: purpose, scope, limitations, contact details,
   version history. For each claim capture: the section it came from, the claim in the
   vendor's own words, and which target column it governs.
3. Materialise the result as a table VENDOR_METHODOLOGY_CLAIMS in my DE_HOL_XX schema.
4. Add a column for the verdict, and fill it in from what we established in the previous
   step: CONFIRMED where the data agrees with the claim, CONTRADICTED where it does not.
   For each CONTRADICTED row, record what the data actually shows and the residual
   magnitude that proves it.
5. Write docs/vendor_methodology_reconstructed.md containing:
   - the reconstructed methodology, one section per rule, with the proving SQL and the
     residual before and after
   - the stated-versus-actual table
   - the fund-month that does not reconcile, written up as an open question for Meridian

Be precise in the wording of the contradictions. This document is going to the vendor.""",
)

render_explanation(
    "Why this is the payoff, and what to do with the result",
    """
Up to now you have been doing arithmetic. This step turns it into something CI can act on.

**Why an AI function rather than reading it yourself.** You could read three pages. You cannot
read three hundred, and CI has more than one vendor. The pattern — unstructured document to
structured claims to a diff against measured reality — scales in a way that careful reading does
not. `AI_EXTRACT` does the part that does not scale; the reconciliation you already did is the
part that gives the extraction something to be checked against.

That combination is the point. An LLM reading a methodology document and summarising it is
mildly useful. An LLM reading a methodology document and having its claims automatically checked
against 72 reconciled rows of data is a control.

**Expect the document to be partly right.** Not everything in it is wrong. Some claims will hold
up. That matters: if vendor documentation were uniformly unreliable you could ignore it, and if
it were uniformly reliable you would not need to check. It is neither, and only reconciliation
tells you which parts to trust.

**Watch for the internal inconsistency.** At least one of the vendor's own output columns is
computed on a different basis than another column that is supposed to be related to it. That is
not an undocumented choice — it is a defect in their output, and it is the finding most likely
to matter to CI's finance and compliance functions.

**The deliverable is not the reconciliation.** It is the document. A reconciliation lives in
someone's session history; a document with proving SQL per claim goes to the vendor, to
compliance, and into the file for the next person who asks where these numbers come from.
""",
)

st.space("small")

render_checkpoint(
    "scripts/checkpoints/after_session_02.sql",
    "If you did not finish, this creates the confirmed reconciliation directly — the NAV view, "
    "the full monthly reconciliation, and a residual view. Replace the two placeholders and run "
    "it. Takes about 30 seconds and puts you exactly where the next sessions expect you.\n\n"
    "It contains the answers, so save it for after you have stopped working on this.",
)

st.space("small")

render_key_concepts([
    {
        "term": "Residual analysis",
        "definition": "Computing your own version of a number, subtracting the reference, and "
                      "reading the structure of what is left. The residual's pattern — constant, "
                      "conditional, proportional, one-sided — points at the cause. Far more "
                      "reliable than asking whether two numbers look close.",
    },
    {
        "term": "Time-weighted vs money-weighted return",
        "definition": "A time-weighted return strips out the effect of cash flow timing, "
                      "measuring the mandate. A money-weighted return includes it, measuring the "
                      "investor's experience. **Modified Dietz** is a money-weighted "
                      "approximation that weights each flow by the fraction of the period "
                      "remaining. It is often described loosely as time-weighted, which matters "
                      "because GIPS contemplates true time-weighting for this kind of "
                      "presentation.",
    },
    {
        "term": "Geometric vs arithmetic excess return",
        "definition": "Arithmetic is `fund − benchmark`. Geometric is `(1+fund)/(1+benchmark) − 1`. "
                      "They differ by a second-order term, so they agree in quiet months and "
                      "diverge in volatile ones — which is why testing a single low-volatility "
                      "month will lead you to the wrong conclusion.",
    },
    {
        "term": "Average daily NAV",
        "definition": "The mean of each day's NAV across the period, as opposed to the opening or "
                      "closing value. Used as a fee and expense-ratio denominator because it "
                      "reflects the assets actually under management through the period rather "
                      "than a single snapshot.",
    },
    {
        "term": "Overfitting a reconciliation",
        "definition": "Adding terms until every row matches. A formula that reconciles 100% of "
                      "real vendor data usually encodes an accident rather than a rule. Segment "
                      "first: reconcile the rows that share a mechanism, and treat the rest as "
                      "findings.",
    },
])

st.space("small")

render_what_you_built([
    "A daily NAV view in your own schema that reproduces the vendor's valuation basis",
    "A reconciliation that agrees with 71 of 72 vendor rows to machine precision",
    "`VENDOR_METHODOLOGY_CLAIMS` — the vendor's stated claims, extracted from a PDF and marked confirmed or contradicted",
    "`docs/vendor_methodology_reconstructed.md` — the methodology, the proving SQL, and the open question",
    "One documented fund-month that does not reconcile, correctly left unexplained rather than absorbed",
], session_num=2)
