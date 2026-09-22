# Reconstructed Performance Methodology — Meridian Monthly Fund Performance File

**Subject:** `VENDOR_FUND_PERFORMANCE_MONTHLY`, reporting periods 2025-01 to 2025-12
**Vendor document under review:** MPA-METH-2025-04, version 4.2, effective 1 January 2025
**Prepared by:** CI Financial, Data Engineering
**Basis:** Reconstruction from the source files CI supplies to Meridian, in `CI_SANDBOX_DB.DE_HOL_SHARED`

---

## 1. Purpose and method

This document records the calculation rules that reproduce Meridian's delivered monthly
performance file, derived by reconstruction from the underlying source data rather than from
the methodology statement.

The method was: compute a candidate value, measure the residual against the delivered
figure, correlate that residual against candidate drivers, change exactly one rule, and
re-measure. Each rule below is stated with the SQL that establishes it and the residual
before and after the change. No rule was adopted because it seemed plausible; each was
adopted because it moved the residual and the preceding version did not reconcile.

Scope covered: `ENDING_NAV`, `BEGINNING_NAV`, `NET_FLOWS`, `GROSS_RETURN_PCT`,
`NET_RETURN_PCT`. Not reconstructed: `BENCHMARK_RETURN_PCT`, `EXCESS_RETURN_PCT`,
`EXPENSE_RATIO_PCT`, `YTD_NET_RETURN_PCT`.

All residuals are quoted as the reconstruction minus Meridian's delivered figure. "Exact"
means within 0.01 CAD for money and 1e-06 percentage points for returns — at or below
FLOAT representation noise for the magnitudes involved.

---

## 2. Reconstructed rules

### Rule 1 — Holdings are valued at same-day closing price

Quantity from `HOLDINGS_DAILY`, price from `PRICES_DAILY` on the same date. Lossless: all
30,972 holding rows price, none dropped. `PRICES_DAILY.CURRENCY` and
`SECURITY_MASTER.CURRENCY` never disagree.

**Residual:** not a change — this is the starting construction.

### Rule 2 — FX is applied at the PRIOR observation date, not the valuation date

This is the first substantive divergence from the methodology statement.

The first construction used same-day FX. Its residual was not random: in 11 of 12 months all
six funds carried the same sign, residual magnitude ranked perfectly with each fund's
non-CAD share of market value, and the residual correlated with the day-over-day USD/CAD
change at r = 0.72.

Correlating against the interaction of the two:

```sql
WITH fxd AS (
  SELECT rate_date, from_currency,
         (rate / LAG(rate) OVER (PARTITION BY from_currency ORDER BY rate_date) - 1) AS pct_rate
  FROM DE_HOL_SHARED.FX_RATES_DAILY WHERE to_currency = 'CAD'
),
expo AS (
  SELECT h.fund_code, h.as_of_date,
         SUM(IFF(p.currency='USD', h.quantity*p.close_price_local*fx.rate,0))
           / SUM(h.quantity*p.close_price_local*fx.rate) AS usd_share,
         SUM(IFF(p.currency='EUR', h.quantity*p.close_price_local*fx.rate,0))
           / SUM(h.quantity*p.close_price_local*fx.rate) AS eur_share
  FROM DE_HOL_SHARED.HOLDINGS_DAILY h
  JOIN DE_HOL_SHARED.PRICES_DAILY p
       ON p.security_id=h.security_id AND p.price_date=h.as_of_date
  JOIN DE_HOL_SHARED.FX_RATES_DAILY fx
       ON fx.rate_date=h.as_of_date AND fx.from_currency=p.currency AND fx.to_currency='CAD'
  GROUP BY 1,2
)
SELECT CORR(r.diff_bps, (e.usd_share*u.pct_rate + e.eur_share*eu.pct_rate)*10000)
FROM DE_HOL_1.nav_residual r
JOIN expo e  ON e.fund_code=r.fund_code AND e.as_of_date=r.period_end_date
JOIN fxd u   ON u.rate_date=r.period_end_date AND u.from_currency='USD'
JOIN fxd eu  ON eu.rate_date=r.period_end_date AND eu.from_currency='EUR';
-- returns exactly 1.0000
```

A correlation of exactly 1.0 against currency exposure multiplied by the one-day FX change
identifies the cause as an FX date offset of one observation. The rule:

```sql
CREATE OR REPLACE VIEW DE_HOL_1.v_fx_lagged AS
SELECT rate_date, from_currency, to_currency, rate,
       LAG(rate) OVER (PARTITION BY from_currency, to_currency ORDER BY rate_date) AS rate_prior
FROM DE_HOL_SHARED.FX_RATES_DAILY;

CREATE OR REPLACE VIEW DE_HOL_1.v_fund_nav_daily_v2 AS
SELECT h.fund_code, h.as_of_date,
       SUM(h.quantity * p.close_price_local * fx.rate_prior) AS nav_cad
FROM DE_HOL_SHARED.HOLDINGS_DAILY h
JOIN DE_HOL_SHARED.PRICES_DAILY p
     ON p.security_id=h.security_id AND p.price_date=h.as_of_date
JOIN DE_HOL_1.v_fx_lagged fx
     ON fx.rate_date=h.as_of_date AND fx.from_currency=p.currency AND fx.to_currency='CAD'
GROUP BY 1,2;
```

| | Max abs residual (CAD) | Max abs residual (bps) | Exact |
|---|---|---|---|
| Same-day FX | 2,095,318.55 | 60.75 | 0 / 72 |
| **Prior-day FX** | **0.0048** | **0.00** | **72 / 72** |

Note that price is same-day while FX is prior-day, so this is not a uniform one-day lag on
the whole valuation. The two inputs are drawn from different dates.

### Rule 3 — Reported NAV is gross of accrued fees

`ENDING_NAV` reconciles to undeducted market value. Deducting the same month's accrued
management and administration fees breaks the reconciliation and never recovers it.

```sql
SELECT COUNT_IF(ABS(end_nav - v_end) < 0.01)               AS nav_gross_exact,
       COUNT_IF(ABS((end_nav - exp_cal) - v_end) < 0.01)   AS nav_netoffees_exact,
       ROUND(MIN(ABS((end_nav - exp_cal) - v_end)),2)      AS netoffees_min_abs
FROM DE_HOL_1.v_perf_monthly;
-- 72, 0, 157604.47
```

| | Exact | Smallest abs residual |
|---|---|---|
| Gross market value | 72 / 72 | 0.0048 CAD |
| Less accrued fees | 0 / 72 | 157,604.47 CAD |

### Rule 4 — `BEGINNING_NAV` is the prior period's `ENDING_NAV`

Not an independent valuation. Equal to the prior row's `ENDING_NAV` in all 66 cases where a
predecessor exists. For January 2025 the anchor is 2024-12-31, confirmed exact to the cent
for all six funds. This is why the source extract carries a 2024-12-24 to 2024-12-31 tail:
it is required, not stray.

### Rule 5 — Period end is the last weekday of the month

Three of twelve period ends are not calendar month end: 2025-05-30, 2025-08-29, 2025-11-28,
each the Friday before a weekend month end. The source daily tables contain 267 dates
covering every weekday including 2024-12-25 and 2025-01-01, so the underlying calendar is
weekdays, not trading days.

Consequence: joins from the monthly file to source data must key on
`DATE_TRUNC('month', ...)`. A `LAST_DAY()` join silently fails on exactly those three
months. This was observed during reconstruction — an initial `LAST_DAY()` join reported
68/72 on `NET_FLOWS` purely from the three mismatched period ends.

### Rule 6 — `NET_FLOWS` is subscriptions less redemptions, distributions excluded

```sql
WITH cf AS (
  SELECT fund_code, DATE_TRUNC('month', flow_date) mo,
         SUM(IFF(flow_type='SUBSCRIPTION', amount_cad, 0)) sub,
         SUM(IFF(flow_type='REDEMPTION',   amount_cad, 0)) red,
         SUM(IFF(flow_type='DISTRIBUTION', amount_cad, 0)) dist
  FROM DE_HOL_SHARED.CASH_FLOWS GROUP BY 1,2
)
SELECT COUNT_IF(ABS(v.net_flows - (sub-red))      < 0.01) AS excl_dist,
       COUNT_IF(ABS(v.net_flows - (sub-red-dist)) < 0.01) AS incl_dist
FROM DE_HOL_SHARED.VENDOR_FUND_PERFORMANCE_MONTHLY v
LEFT JOIN cf ON cf.fund_code=v.fund_code
            AND cf.mo=DATE_TRUNC('month', v.period_end_date);
-- 72, 64
```

| | Exact |
|---|---|
| **Subscriptions − redemptions** | **72 / 72** |
| Less distributions | 64 / 72 |

`AMOUNT_CAD` is stored positive for all three flow types; the sign is carried by
`FLOW_TYPE`. 42 of 72 fund-months have no flows, so a `LEFT JOIN` with `COALESCE` is
required — an inner join drops 58% of the population. Distributions occur only on
2025-12-31, so an error in this rule would surface in December alone.

### Rule 7 — Distributions are added back to the return numerator

The first gross-return construction, `(end − begin − flow) / begin`, was exact for 36 of 42
zero-flow months. All 6 failures had a distribution in the month, and no zero-flow month
without a distribution failed.

| | Max abs residual (pp) | Exact |
|---|---|---|
| No distribution term | 1.285070 | 36 / 72 |
| **Plus distributions** | **0.310475** | **42 / 72** |

All 42 zero-flow months now reconcile. This confirms distributions are treated as
reinvested.

### Rule 8 — Flow timing enters the denominator (Modified Dietz)

The remaining 30 failures were exactly the months with a subscription or redemption. Moving
from a beginning-NAV denominator to a day-weighted denominator:

| | Max abs residual (pp) | Exact |
|---|---|---|
| Beginning NAV denominator | 0.310475 | 42 / 72 |
| **Beginning NAV + day-weighted flows** | **0.010685** | **63 / 72** |

### Rule 9 — Flow day-weights use calendar-month day counts

The 9 residual failures all had a single flow and all fell in June, September or December —
the three months *following* a short period end. Weighting by days between period ends gave
the wrong denominator for exactly those months; weighting by position within the calendar
month gave the right one.

```sql
-- weight = (days_in_month - day_of_month_of_flow) / days_in_month
COALESCE(SUM(
  (IFF(c.flow_type='SUBSCRIPTION', c.amount_cad, 0) - IFF(c.flow_type='REDEMPTION', c.amount_cad, 0))
  * (DAY(b.period_end_date) - DAY(c.flow_date)) / DAY(b.period_end_date)
), 0) AS wflow
```

| | Max abs residual (pp) | Exact |
|---|---|---|
| Period-end-to-period-end day count | 0.010685 | 63 / 72 |
| **Calendar-month day count** | **0.0000005** | **72 / 72** |

`GROSS_RETURN_PCT` is fully reconstructed:

```
gross_return_pct = (end_nav + distributions - begin_nav - net_flows)
                 / (begin_nav + day_weighted_flows) * 100
```

### Rule 10 — Net return deducts scheduled fees, by accrual-day count, on a 252-day year

The fee drag is not taken from booked accruals. It is:

```
drag_pct = accrual_days_in_month * (MGMT_FEE_BPS + ADMIN_FEE_BPS) / 100 / 252
```

where `accrual_days_in_month` is the count of `FUND_EXPENSES_DAILY` rows for the fund in the
calendar month (20 to 23). The implied drag values are exact simple fractions of the annual
scheduled rate, which is what pointed away from the booked accruals: for CIF-ALT-LS-06
(210 bps) the drag takes only the values 0.166667, 0.175000, 0.183333 and 0.191667,
corresponding to 20, 21, 22 and 23 days at 2.10 / 252 per day.

| | Exact |
|---|---|
| Actual accruals over beginning NAV | 0 / 72 |
| Actual accruals over average capital | 0 / 72 |
| **Scheduled fees × days / 252** | **71 / 72** |

The `FUND_EXPENSES_DAILY` amounts are used only for their row count, never their values.
`OTHER_EXPENSE` is not deducted at all: excluding it gives 71/72, including it gives 0/72.

---

## 3. Stated versus actual

Sixteen methodology claims were extracted from MPA-METH-2025-04 and assessed against the
reconstruction. Full detail, including the residual evidence for each, is in
`CI_SANDBOX_DB.DE_HOL_1.VENDOR_METHODOLOGY_CLAIMS`.

**Summary: 5 confirmed, 6 contradicted, 5 unverified.**

### Contradicted

| § | Vendor states | Data shows | Residual evidence |
|---|---|---|---|
| 2 | "market values are converted using the exchange rates prevailing on the valuation date" | FX is applied at the prior observation date. Prices are same-day; FX is not. | Same-day FX: 0/72 exact, max 60.75 bps. Prior-day FX: 72/72 exact, max 0.0048 CAD. Residual vs exposure × daily FX change: r = 1.0000 |
| 2 | "Net asset value is reported after accrual of all liabilities known to Meridian as at the valuation point, including accrued management and administration fees" | Reported NAV is gross of accrued fees | Gross: 72/72 exact. Net of accrued fees: 0/72, smallest residual 157,604 CAD |
| 3 | "returns on a time-weighted rate of return basis, which removes the effect of the timing and magnitude of external cash flows" | Modified Dietz. Flow timing and magnitude enter the denominator directly, so their effect is not removed. | Denominator without flow weighting: 42/72. With day-weighted flows: 72/72 at 5e-07 pp |
| 3 | "Returns are presented net of all fund operating expenses, including management fees, administration fees, and other ordinary operating costs borne by the fund" | Only scheduled management and administration fees are deducted. `OTHER_EXPENSE` is not. | Excluding OTHER_EXPENSE: 71/72 exact. Including it: 0/72 |
| 4 | "Where a mandate carries a performance fee, the fee is accrued monthly on the basis of performance measured to that month end" | No monthly accrual is present. A single deduction appears at year end. | CIF-ALT-LS-06: 11/12 months exact with zero performance fee. 2025-12-31 residual +0.133946 pp |
| 5 | "Excess return is presented as the fund return less the benchmark return for the corresponding period" | `EXCESS_RETURN_PCT` is not the difference between the two reported figures on the same row | Net − benchmark matches 10/72 at 2dp; gross − benchmark 2/72. Largest disagreement 0.9229 pp. Reported range (−10.23 to +10.13) exceeds either input's range |

### Confirmed

| § | Vendor states | Evidence |
|---|---|---|
| 2 | Market values struck daily at official closing prices | Same-day price reconciles; 30,972/30,972 holdings price with no loss |
| 3 | "External cash flows comprise subscriptions and redemptions" | 72/72 exact |
| 3 | "distributions are treated as reinvested at the distribution date" | Excluding from flows and adding to numerator fixes all 8 distribution months |
| 3 | "Gross returns... presented before the deduction of these amounts" | Gross reconciles with no fee term; net < gross in 72/72 |
| 4 | "fees are accrued in accordance with the fee schedule applicable to each mandate" | Scheduled bps reproduce the drag in 71/72. Note this is also the mechanism by which the §2 and §3 claims above fail |

### Unverified

Not tested in this exercise; no assertion is made either way.

| § | Claim |
|---|---|
| 3 | Compounding to quarterly, annual and since-inception figures (only monthly and YTD were delivered) |
| 4 | Expense ratio as total expenses over average net assets, annualised |
| 5 | Benchmark returns sourced from the index provider without adjustment |
| 5 | Blended benchmark components combined at investment-policy target weights |
| 5 | Blended benchmarks rebalanced monthly |

---

## 4. Open question for Meridian

**One fund-month does not reconcile: CIF-ALT-LS-06, period ending 2025-12-31.**

Every other fund-month in the file reconciles to machine precision on the rules above.

| Field | Value |
|---|---|
| Reconstructed gross return | 1.302731 % |
| Meridian gross return | 1.302731 % (exact) |
| Reconstructed net return | 1.111064 % |
| Meridian net return | 0.977118 % |
| **Unexplained deduction** | **0.133946 pp** |
| Accrual days in month | 23 |
| Scheduled fee drag applied | 0.191667 pp (23 × 2.10 / 252) |
| `PERF_FEE_RATE` on mandate | 0.15 |
| Benchmark return for the period | 4.410261 % |

Observations, offered without conclusion:

- Gross return agrees exactly, so the discrepancy is entirely within the fee deduction.
- CIF-ALT-LS-06 is the only mandate in the file with a non-zero `PERF_FEE_RATE`, and
  2025-12-31 is the only period where its net return departs from the scheduled-fee formula.
  The other 11 months for this mandate reconcile exactly with no performance fee applied.
- The mandate **underperformed** its stated benchmark in the period (gross 1.30% against
  benchmark 4.41%, i.e. −3.11 pp). We cannot construct an excess-return basis on which a
  performance fee would crystallise from this month's figures.
- The deduction divided by `PERF_FEE_RATE` is 0.892973. We have not been able to tie this to
  any figure in the delivered file or the source data, including the reported YTD net return
  of 0.759313 %.

**We have deliberately not adjusted the formula to absorb this residual.** Fitting a rule to
a single observation would have made the other 71 reconciliations unfalsifiable.

Requests:

1. Confirm whether a performance fee was crystallised for CIF-ALT-LS-06 in December 2025,
   and if so state the accrual basis, the measurement period, and the hurdle or high-water
   mark against which it was assessed.
2. If the fee is assessed annually rather than monthly, confirm that §4 of MPA-METH-2025-04
   should read accordingly, since it currently states monthly accrual.
3. Confirm the figure 0.892973 % or identify the quantity to which the 0.133946 pp
   deduction corresponds.

---

## 5. Points to raise on the methodology statement

Independent of the December question, four items in MPA-METH-2025-04 do not describe the
delivered file and we would ask Meridian to either correct the calculation or amend the
statement:

1. **§2, FX date.** The statement says valuation date; the file uses the prior observation.
   On this file that moved reported NAV by up to 60.75 bps, materially for the mandates with
   the largest non-CAD exposure (CIF-USD-EQ-05 at 95.5% and CIF-GLB-EQ-02 at 84.5%).
2. **§2, NAV basis.** The statement says NAV is net of accrued management and administration
   fees; the delivered figures are gross of them.
3. **§3, return basis.** The statement describes a time-weighted return that removes the
   effect of flow timing and magnitude. The delivered figures are Modified Dietz, in which
   flow timing and magnitude are inputs to the denominator. These are not the same basis and
   the distinction is material where flows are large relative to NAV.
4. **§3 versus §4, expense coverage.** §3 says returns are net of all fund operating
   expenses including other ordinary operating costs; §4 says fees are accrued per the fee
   schedule. The file follows §4. `OTHER_EXPENSE` is never deducted, so the two sections are
   not reconcilable as written.

Additionally, we note **§5's excess return definition** does not hold arithmetically against
the two columns delivered alongside it. We have not reconstructed either the benchmark or
excess return series, so we are not asserting which of the three columns is at issue — only
that they are mutually inconsistent as delivered.

---

## Appendix — Objects produced

All in `CI_SANDBOX_DB.DE_HOL_1`.

| Object | Contents |
|---|---|
| `V_FX_LAGGED` | FX rates with prior-observation rate |
| `V_FUND_NAV_DAILY` | Daily NAV, same-day FX (superseded, retained for the residual trail) |
| `V_FUND_NAV_DAILY_V2` | Daily NAV, prior-day FX — the reconciling construction |
| `PERF_BASE` | Fund-month NAV anchors, flows, distributions, expense windows |
| `V_PERF_MONTHLY` | Adds day-weighted flows, average capital, reconstructed gross return |
| `NAV_RESIDUAL` | Per-fund-month NAV residual in CAD and bps |
| `RETURN_RESIDUAL` | Per-fund-month gross and net return residuals |
| `VENDOR_DOC_PARSED` | `AI_PARSE_DOCUMENT` output for the methodology statement |
| `VENDOR_METHODOLOGY_CLAIMS` | 16 extracted claims with verdict, finding and residual evidence |
