# SOLUTION — the seven rules Meridian applied

**Facilitator only. Do not circulate before Session 2.**

This is the answer key for the reverse-engineering session. Everything under `facilitator/`
is spoiler material, including `generator/generate_data.py`, which computes the target by
applying these rules.

The target table is `VENDOR_FUND_PERFORMANCE_MONTHLY` — 72 rows, 6 funds × 12 months of 2025.
Applying all seven rules reproduces **71 of 72 rows to better than 0.0001 bps**. The 72nd row
is a deliberate outlier (see [The December outlier](#the-december-outlier)).

Run `python3 facilitator/generator/generate_data.py --no-write` at any time to re-verify that
the puzzle is still solvable and correctly ordered.

---

## Discovery order and expected residuals

Attendees should fix one rule at a time and watch the residual shrink. This is the ladder the
verifier asserts, measured as mean absolute residual on `NET_RETURN_PCT` with the December
outlier excluded:

| Step | Mean abs residual |
|---|---|
| Naive everything | 25.947 bps |
| + Rule 2 (distributions) | 16.462 bps |
| + Rule 1 (T-1 FX) | 2.646 bps |
| + Rule 3 (Modified Dietz) | 1.230 bps |
| + Rule 5 (other expense) | 0.909 bps |
| + Rule 4 (fee basis) | 0.000 bps |

Rules 6 and 7 act on `BENCHMARK_RETURN_PCT` and `EXCESS_RETURN_PCT`, so they sit outside the
net-return ladder.

**If a table is stuck**, the highest-value nudge is almost always: *"stop trying to match the
whole number — compute your version, join to theirs, and look at what the difference is
correlated with."* That single move unlocks the session. Resist giving the rule itself.

---

## Rule 1 — NAV uses the prior business day's FX

Foreign-currency holdings are converted at the **previous business day's** rate, not the
valuation date's rate. The vendor document claims the opposite (Section 2), which makes this
both a data finding and a documentation defect.

**Signature:** residual on `ENDING_NAV` correlates with the day-over-day FX move at about
`+0.72`. Median absolute residual ≈ **4.4 bps**, larger on the global and US funds, which carry
the most foreign currency.

**Proving SQL** — compare same-day FX against T-1 FX for one fund:

```sql
WITH fx_lagged AS (
    SELECT
        rate_date,
        from_currency,
        rate                                                   AS rate_same_day,
        LAG(rate) OVER (PARTITION BY from_currency ORDER BY rate_date) AS rate_prior_day
    FROM fx_rates_daily
),
valued AS (
    SELECT
        h.fund_code,
        h.as_of_date,
        SUM(h.quantity * p.close_price_local * f.rate_same_day)  AS nav_same_day_fx,
        SUM(h.quantity * p.close_price_local * f.rate_prior_day) AS nav_prior_day_fx
    FROM holdings_daily h
    JOIN prices_daily p
      ON p.security_id = h.security_id AND p.price_date = h.as_of_date
    JOIN fx_lagged f
      ON f.from_currency = p.currency AND f.rate_date = h.as_of_date
    GROUP BY 1, 2
)
SELECT
    v.fund_code,
    v.as_of_date,
    t.ending_nav,
    (v.nav_same_day_fx  / t.ending_nav - 1) * 10000 AS resid_same_day_bps,
    (v.nav_prior_day_fx / t.ending_nav - 1) * 10000 AS resid_prior_day_bps
FROM valued v
JOIN vendor_fund_performance_monthly t
  ON t.fund_code = v.fund_code AND t.period_end_date = v.as_of_date
ORDER BY v.fund_code, v.as_of_date;
```

`resid_prior_day_bps` collapses to ~0. `resid_same_day_bps` does not.

**Watch for:** attendees who inner-join FX on the same date lose the first January row entirely,
because the prior business day falls in December 2024. The calendar deliberately starts
2024-12-24 so the lag is available — but only if they use `LAG`, not an equi-join.

---

## Rule 2 — distributions are treated as reinvested

Distributions are added back to ending market value for return purposes. They are **not** an
external cash flow.

The trap is subtle and worth understanding before you steer anyone: subtracting the
distribution as an outflow *and* adding it back to ending NAV are algebraically identical, so
there is no wrong answer available by choosing between those two. The only way to get this
wrong is to **drop distributions entirely** — which is exactly what happens when someone
reproduces the reported `NET_FLOWS` column (which is subscriptions minus redemptions, with no
distribution component) and then reuses it as the flow term in the return formula.

**Signature:** the loudest rule in the lab. Median absolute residual ≈ **75 bps** in the eight
distribution months, and **0.000 bps** everywhere else. Only `CIF-BAL-60-03` and
`CIF-FIX-IN-04` pay distributions, quarterly, on the last business day of March, June,
September and December.

**Proving SQL** — show that reported `NET_FLOWS` excludes distributions:

```sql
SELECT
    t.fund_code,
    t.period_end_date,
    t.net_flows                                        AS vendor_reported,
    SUM(CASE WHEN c.flow_type = 'SUBSCRIPTION' THEN c.amount_cad
             WHEN c.flow_type = 'REDEMPTION'   THEN -c.amount_cad
             ELSE 0 END)                               AS subs_less_reds,
    SUM(CASE WHEN c.flow_type = 'DISTRIBUTION' THEN c.amount_cad ELSE 0 END)
                                                       AS distributions
FROM vendor_fund_performance_monthly t
LEFT JOIN cash_flows c
       ON c.fund_code = t.fund_code
      AND DATE_TRUNC('month', c.flow_date) = DATE_TRUNC('month', t.period_end_date)
GROUP BY 1, 2, 3
HAVING distributions > 0
ORDER BY 1, 2;
```

`vendor_reported` equals `subs_less_reds` exactly, and ignores `distributions`. That proves
distributions are handled somewhere other than the flow term.

This is the one rule the vendor document gets **right** (Section 3).

---

## Rule 3 — gross return is Modified Dietz, not daily-chained TWR

Each external flow is weighted by the fraction of the month remaining after it lands:

```
                 EMV + distributions − BMV − net_flows
gross_return = ─────────────────────────────────────────
                    BMV + Σ ( Fᵢ × (D − dᵢ) / D )
```

where `D` is the day-of-month of the period end, `dᵢ` is the day-of-month of flow `i`, and `Fᵢ`
is signed (subscriptions positive, redemptions negative). Distributions are excluded from the
weighted-flow term.

**Signature:** median absolute residual ≈ **3.9 bps** in months with a subscription or
redemption, and **0.0000 bps** in months without. Magnitude scales with flow size × how much
the fund moved that month (correlation ≈ `+0.58`) — a large flow into a flat month costs
nothing, which is why flow size alone correlates only weakly.

Flows are placed on days 8–22 on purpose. A flow on the first or last day of the month carries
a Modified Dietz weight near 1 or 0, where the two methods nearly agree.

**Note for the sharp-eyed:** Modified Dietz is a *money-weighted approximation*. The vendor
document (Section 3) claims a time-weighted rate of return. These are not the same thing, and
saying so is a legitimate finding — arguably the most commercially significant one in the lab,
since TWR is what the CFA Institute's GIPS standards contemplate for this presentation.

---

## Rule 4 — fees come off total accruals over average daily NAV

```
fee_drag = ( Σ MGMT_FEE_ACCRUED + Σ ADMIN_FEE_ACCRUED ) / average daily NAV for the month
```

Because accruals are struck daily on a 252-day basis, this lands near
`annual_rate × business_days_in_month / 252`, which is **not** `annual_rate / 12`.

**Signature:** the subtlest rule, and the one with the cleanest tell. Median absolute residual
≈ **0.9 bps**, correlating with the number of business days in the month at **`+0.97`**. A
month with 23 business days is over-charged by a naive `/12`; a 19-day month is under-charged.

**Proving SQL:**

```sql
SELECT
    e.fund_code,
    DATE_TRUNC('month', e.accrual_date)                AS period,
    COUNT(*)                                           AS business_days,
    SUM(e.mgmt_fee_accrued + e.admin_fee_accrued)      AS fees_accrued,
    AVG(n.nav_cad)                                     AS avg_daily_nav,
    SUM(e.mgmt_fee_accrued + e.admin_fee_accrued) / AVG(n.nav_cad) * 10000
                                                       AS fee_drag_bps,
    (f.mgmt_fee_bps + f.admin_fee_bps) / 12.0          AS naive_flat_bps
FROM fund_expenses_daily e
JOIN fund_master f ON f.fund_code = e.fund_code
JOIN <your_nav_view> n
      ON n.fund_code = e.fund_code AND n.as_of_date = e.accrual_date
GROUP BY 1, 2, f.mgmt_fee_bps, f.admin_fee_bps
ORDER BY 1, 2;
```

`fee_drag_bps` moves with `business_days`; `naive_flat_bps` is constant.

---

## Rule 5 — `OTHER_EXPENSE` is excluded from net return but included in the expense ratio

Net return deducts management and administration fees only. `OTHER_EXPENSE` is left out.
But `EXPENSE_RATIO_PCT` **includes** it:

```
expense_ratio = ( Σ MGMT + Σ ADMIN + Σ OTHER ) / avg daily NAV × ( 252 / business_days )
```

**Signature:** median absolute residual ≈ **1.8 bps**, and **100% one-sided** — always in the
same direction, because an omitted expense can only ever flatter the return. One-sidedness is
the tell: a timing or convention error produces residuals on both sides of zero.

This is an **internal inconsistency in the vendor's own output**, not merely an undocumented
choice. The same expense is in one column and out of the other. Section 3 of the methodology
statement claims returns are net of *all* fund operating expenses "including... other ordinary
operating costs", so the document and the data contradict each other directly.

Of the seven findings, this is the one most likely to matter to CI's finance and compliance
functions, and it is worth calling out explicitly in the debrief.

---

## Rule 6 — blended benchmarks rebalance monthly, arithmetically

For `BM-BLEND-6040` (60% `IDX-TSX`, 40% `IDX-FTSEBOND`), each component's daily returns are
compounded within the month **first**, then combined with static target weights:

```
benchmark_return = Σ ( wⱼ × monthly compounded return of component j )
```

Not a chained daily blend, and not a buy-and-hold blend whose weights drift intra-month.

**Signature:** fires **only** on `CIF-BAL-60-03`, the only fund on a blended benchmark. Median
absolute residual ≈ **1.0 bps** there, and **0.0000 bps** on every single-index fund. A rule
that fires on exactly one fund is a strong hint to segment by benchmark type.

The vendor document gets this one **right** (Section 5).

---

## Rule 7 — excess return is geometric

```
excess_return = ( 1 + net_return ) / ( 1 + benchmark_return ) − 1
```

Not `net_return − benchmark_return`.

**Signature:** second-order, so it hides in quiet months and shows up in loud ones. Maximum
absolute residual ≈ **92 bps**, correlating with the magnitude of the benchmark return at
`+0.93`. Attendees who test only a low-volatility month will conclude the arithmetic version
is correct.

The vendor document explicitly claims the arithmetic version (Section 5), so this is another
documented-versus-actual mismatch.

---

## The December outlier

`CIF-ALT-LS-06` is the only fund with a performance fee (`PERF_FEE_RATE = 0.15`). In **December
only**, an additional drag is applied:

```
perf_fee_drag = 0.15 × max(0, YTD net return before performance fee − 0%)
```

The fee crystallises **annually in December** on full-year performance. The vendor document
(Section 4) claims performance fees are accrued **monthly** — a fifth documentation mismatch.

**Signature:** that single row misses by **13.4 bps** while the other 71 reconcile to
0.00005 bps. A 260,000× difference in residual, sitting in one cell.

This exists to teach segmentation. There is no global formula that fits all 72 rows, so any
attendee who keeps tuning a single expression will keep failing. The correct move is to notice
that one fund-month is different in kind, exclude it, reconcile the other 71 cleanly, and
raise the outlier as a question rather than absorbing it into the formula.

**If a table forces the outlier to fit**, that is a teachable moment worth spending a minute
on: they will have produced a formula that reconciles perfectly and describes nothing.

---

## Stated versus actual — the Session 2 payoff

The methodology PDF makes seven substantive claims. Five are contradicted by the data:

| # | Vendor claim | Section | Verdict | What the data shows |
|---|---|---|---|---|
| 1 | "time-weighted rate of return" | 3 | **Contradicted** | Modified Dietz, a money-weighted approximation |
| 2 | "exchange rates prevailing on the valuation date" | 2 | **Contradicted** | Prior business day's rate |
| 3 | "net of all fund operating expenses" | 3 | **Contradicted** | `OTHER_EXPENSE` excluded from net return |
| 4 | "distributions are treated as reinvested" | 3 | Confirmed | Added back to EMV, excluded from flows |
| 5 | "blended benchmarks are rebalanced monthly" | 5 | Confirmed | Monthly arithmetic reweighting |
| 6 | "fund return less the benchmark return" | 5 | **Contradicted** | Geometric ratio |
| 7 | "performance fee accrued monthly" | 4 | **Contradicted** | Crystallised annually in December |

Two confirmations matter as much as the five contradictions. If everything in the document were
wrong, the exercise would read as a trick. The point is that vendor documentation is *partly*
reliable, and only reconciliation tells you which parts.

The deliverable from Session 2 is this table, generated by the attendees, with proving SQL
attached to each row. That is a document CI can send to Meridian.

---

## Facilitator quick reference

| Rule | Median resid | Correlates with | Fires on |
|---|---|---|---|
| 2 Distributions | 75 bps | distribution months | 8 rows, 2 funds |
| 1 T-1 FX | 4.4 bps | daily FX move (+0.72) | all rows, strongest on FX-heavy funds |
| 3 Modified Dietz | 3.9 bps | flow size × return (+0.58) | ~30 rows with flows |
| 5 Other expense | 1.8 bps | nothing — one-sided | all rows |
| 6 Blend rebalance | 1.0 bps | benchmark type | 12 rows, 1 fund |
| 4 Fee basis | 0.9 bps | business days in month (+0.97) | all rows |
| 7 Geometric excess | up to 92 bps | return magnitude (+0.93) | all rows, visible in volatile months |
| December outlier | 13.4 bps | — | 1 row |
