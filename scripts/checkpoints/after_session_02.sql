-- =====================================================================================
-- CHECKPOINT: after Session 2
-- =====================================================================================
-- Purpose
--   Puts an attendee back on the main line if they did not finish reverse-engineering the
--   vendor methodology. Creates the confirmed seven-rule reconciliation directly, so
--   Sessions 4 and 5 can start clean.
--
-- This is a catch-up path, not the lesson. It contains the answers. Do not hand it out
-- before Session 2 is over.
--
-- Usage
--   1. Replace {{CI_SANDBOX_DB}} with the sandbox database name.
--   2. Replace DE_HOL_XX with the attendee's own schema.
--   3. Run all statements.
--
-- Runtime: a few seconds. Creates three views, no tables.
-- =====================================================================================

USE DATABASE {{CI_SANDBOX_DB}};
USE SCHEMA DE_HOL_XX;


-- -------------------------------------------------------------------------------------
-- RULE 1 --- daily NAV, valuing foreign holdings at the PRIOR business day's FX rate.
--
-- The LAG is essential rather than cosmetic: joining FX on the same date would silently
-- drop the first business day of January, because its prior business day falls in
-- December 2024.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW V_FUND_NAV_DAILY AS
WITH fx_lagged AS (
    SELECT
        rate_date,
        from_currency,
        LAG(rate) OVER (PARTITION BY from_currency ORDER BY rate_date) AS rate_prior_day
    FROM {{CI_SANDBOX_DB}}.DE_HOL_SHARED.FX_RATES_DAILY
    WHERE to_currency = 'CAD'
)
SELECT
    h.fund_code,
    h.as_of_date,
    SUM(h.quantity * p.close_price_local * f.rate_prior_day) AS nav_cad
FROM {{CI_SANDBOX_DB}}.DE_HOL_SHARED.HOLDINGS_DAILY h
JOIN {{CI_SANDBOX_DB}}.DE_HOL_SHARED.PRICES_DAILY p
     ON  p.security_id = h.security_id
     AND p.price_date  = h.as_of_date
JOIN fx_lagged f
     ON  f.from_currency = p.currency
     AND f.rate_date     = h.as_of_date
WHERE f.rate_prior_day IS NOT NULL
GROUP BY h.fund_code, h.as_of_date;


-- -------------------------------------------------------------------------------------
-- RULES 2 through 7 plus the December performance-fee crystallisation.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW V_VENDOR_RECON AS
WITH nav AS (
    SELECT
        fund_code,
        as_of_date,
        nav_cad,
        DATE_TRUNC('month', as_of_date) AS period
    FROM V_FUND_NAV_DAILY
),

-- Month boundaries and the average daily NAV that rule 4 divides by.
month_bounds AS (
    SELECT
        fund_code,
        period,
        MIN(as_of_date) AS period_start_date,
        MAX(as_of_date) AS period_end_date,
        COUNT(*)        AS business_days,
        AVG(nav_cad)    AS avg_daily_nav
    FROM nav
    GROUP BY fund_code, period
),

-- Ending NAV, and beginning NAV as the prior month's ending NAV. December 2024 is present
-- in the data purely so that January 2025 has a beginning NAV to reference.
monthly_nav AS (
    SELECT
        b.fund_code,
        b.period,
        b.period_start_date,
        b.period_end_date,
        b.business_days,
        b.avg_daily_nav,
        n.nav_cad                                                              AS ending_nav,
        LAG(n.nav_cad) OVER (PARTITION BY b.fund_code ORDER BY b.period)       AS beginning_nav
    FROM month_bounds b
    JOIN nav n
         ON  n.fund_code  = b.fund_code
         AND n.as_of_date = b.period_end_date
),

-- RULE 2 --- subscriptions and redemptions are external flows; distributions are not.
-- Distributions are added back to ending market value instead.
flows AS (
    SELECT
        fund_code,
        DATE_TRUNC('month', flow_date) AS period,
        SUM(CASE WHEN flow_type = 'SUBSCRIPTION' THEN amount_cad ELSE 0 END) AS subscriptions,
        SUM(CASE WHEN flow_type = 'REDEMPTION'   THEN amount_cad ELSE 0 END) AS redemptions,
        SUM(CASE WHEN flow_type = 'DISTRIBUTION' THEN amount_cad ELSE 0 END) AS distributions
    FROM {{CI_SANDBOX_DB}}.DE_HOL_SHARED.CASH_FLOWS
    GROUP BY fund_code, DATE_TRUNC('month', flow_date)
),

-- RULE 3 --- Modified Dietz. Each external flow is weighted by the fraction of the month
-- remaining after it lands. Distributions are excluded from the weighted-flow term.
weighted_flows AS (
    SELECT
        c.fund_code,
        DATE_TRUNC('month', c.flow_date) AS period,
        SUM(
            CASE WHEN c.flow_type = 'SUBSCRIPTION' THEN  c.amount_cad
                 WHEN c.flow_type = 'REDEMPTION'   THEN -c.amount_cad
                 ELSE 0
            END
            * (DAY(b.period_end_date) - DAY(c.flow_date)) / DAY(b.period_end_date)::FLOAT
        ) AS weighted_flow
    FROM {{CI_SANDBOX_DB}}.DE_HOL_SHARED.CASH_FLOWS c
    JOIN month_bounds b
         ON  b.fund_code = c.fund_code
         AND b.period    = DATE_TRUNC('month', c.flow_date)
    GROUP BY c.fund_code, DATE_TRUNC('month', c.flow_date)
),

-- RULES 4 and 5 --- management and administration fees are the only expenses deducted from
-- net return. OTHER_EXPENSE is carried separately because it belongs in the expense ratio
-- but not in net return.
expenses AS (
    SELECT
        fund_code,
        DATE_TRUNC('month', accrual_date) AS period,
        SUM(mgmt_fee_accrued + admin_fee_accrued) AS fees_accrued,
        SUM(other_expense)                        AS other_accrued
    FROM {{CI_SANDBOX_DB}}.DE_HOL_SHARED.FUND_EXPENSES_DAILY
    GROUP BY fund_code, DATE_TRUNC('month', accrual_date)
),

-- Compound each index's daily returns within the month. EXP(SUM(LN(...))) is the standard
-- Snowflake idiom for a product aggregate.
index_monthly AS (
    SELECT
        index_code,
        DATE_TRUNC('month', return_date) AS period,
        EXP(SUM(LN(1 + total_return_pct / 100.0))) - 1 AS monthly_return
    FROM {{CI_SANDBOX_DB}}.DE_HOL_SHARED.INDEX_RETURNS_DAILY
    GROUP BY index_code, DATE_TRUNC('month', return_date)
),

-- RULE 6 --- blended benchmarks are rebalanced monthly to target weights, and combined
-- arithmetically from each component's compounded monthly return. Single-index benchmarks
-- fall out of the same expression with a weight of 1.
benchmark_monthly AS (
    SELECT
        bc.benchmark_id,
        im.period,
        SUM(bc.weight * im.monthly_return) AS benchmark_return
    FROM {{CI_SANDBOX_DB}}.DE_HOL_SHARED.BENCHMARK_COMPONENTS bc
    JOIN index_monthly im
         ON im.index_code = bc.index_code
    GROUP BY bc.benchmark_id, im.period
),

-- Gross return, and net return before any performance fee.
base AS (
    SELECT
        mn.fund_code,
        mn.period,
        mn.period_end_date,
        mn.business_days,
        mn.beginning_nav,
        mn.ending_nav,
        mn.avg_daily_nav,
        fm.perf_fee_rate,
        COALESCE(fl.subscriptions, 0)  AS subscriptions,
        COALESCE(fl.redemptions, 0)    AS redemptions,
        COALESCE(fl.distributions, 0)  AS distributions,
        COALESCE(fl.subscriptions, 0) - COALESCE(fl.redemptions, 0) AS net_flows,
        COALESCE(wf.weighted_flow, 0)  AS weighted_flow,
        ex.fees_accrued,
        ex.other_accrued,
        bm.benchmark_return,

        -- RULE 3 numerator carries RULE 2's distribution add-back.
        (mn.ending_nav + COALESCE(fl.distributions, 0)
            - mn.beginning_nav
            - (COALESCE(fl.subscriptions, 0) - COALESCE(fl.redemptions, 0))
        ) / (mn.beginning_nav + COALESCE(wf.weighted_flow, 0)) AS gross_return,

        -- RULE 4 --- accrued fees over average daily NAV.
        ex.fees_accrued / mn.avg_daily_nav AS fee_drag
    FROM monthly_nav mn
    JOIN {{CI_SANDBOX_DB}}.DE_HOL_SHARED.FUND_MASTER fm
         ON fm.fund_code = mn.fund_code
    JOIN benchmark_monthly bm
         ON  bm.benchmark_id = fm.benchmark_id
         AND bm.period       = mn.period
    LEFT JOIN flows fl
         ON fl.fund_code = mn.fund_code AND fl.period = mn.period
    LEFT JOIN weighted_flows wf
         ON wf.fund_code = mn.fund_code AND wf.period = mn.period
    JOIN expenses ex
         ON ex.fund_code = mn.fund_code AND ex.period = mn.period
    WHERE mn.beginning_nav IS NOT NULL
      AND YEAR(mn.period_end_date) = 2025
),

-- Net return before the performance fee, and the running YTD it is assessed on.
pre_perf AS (
    SELECT
        base.*,
        gross_return - fee_drag AS net_return_before_perf_fee,
        EXP(SUM(LN(1 + gross_return - fee_drag)) OVER (
                PARTITION BY fund_code
                ORDER BY period
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) - 1
            AS ytd_net_before_perf_fee
    FROM base
),

-- The December performance-fee crystallisation. Applies to one fund, in one month.
-- This is why no single global formula reconciles all 72 rows.
with_perf AS (
    SELECT
        pre_perf.*,
        CASE
            WHEN perf_fee_rate > 0
                 AND MONTH(period_end_date) = 12
                 AND ytd_net_before_perf_fee > 0
            THEN perf_fee_rate * ytd_net_before_perf_fee
            ELSE 0
        END AS perf_fee_drag
    FROM pre_perf
),

final AS (
    SELECT
        fund_code,
        period,
        period_end_date,
        business_days,
        ROUND(beginning_nav, 2) AS beginning_nav,
        ROUND(ending_nav, 2)    AS ending_nav,
        ROUND(net_flows, 2)     AS net_flows,
        distributions,
        gross_return * 100                                   AS gross_return_pct,
        (net_return_before_perf_fee - perf_fee_drag) * 100    AS net_return_pct,
        benchmark_return * 100                               AS benchmark_return_pct,

        -- RULE 7 --- excess return is geometric, not the arithmetic difference.
        ((1 + net_return_before_perf_fee - perf_fee_drag) / (1 + benchmark_return) - 1) * 100
            AS excess_return_pct,

        -- RULE 5 --- OTHER_EXPENSE is excluded from net return but included here.
        ((fees_accrued + other_accrued) / avg_daily_nav) * (252.0 / business_days) * 100
            AS expense_ratio_pct,

        fee_drag * 100      AS fee_drag_pct,
        perf_fee_drag * 100 AS perf_fee_drag_pct
    FROM with_perf
)
SELECT
    f.*,
    EXP(SUM(LN(1 + net_return_pct / 100.0)) OVER (
            PARTITION BY fund_code
            ORDER BY period
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) * 100 - 100
        AS ytd_net_return_pct
FROM final f;


-- -------------------------------------------------------------------------------------
-- Residuals against the vendor's numbers. Every column should be within 0.01 bps for all
-- rows except CIF-ALT-LS-06 December, which is the deliberate performance-fee outlier.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW V_VENDOR_RECON_RESIDUALS AS
SELECT
    r.fund_code,
    r.period_end_date,
    (r.ending_nav         - t.ending_nav)                                  AS ending_nav_diff,
    (r.gross_return_pct   - t.gross_return_pct)     * 100                  AS gross_resid_bps,
    (r.net_return_pct     - t.net_return_pct)       * 100                  AS net_resid_bps,
    (r.benchmark_return_pct - t.benchmark_return_pct) * 100                AS bench_resid_bps,
    (r.excess_return_pct  - t.excess_return_pct)    * 100                  AS excess_resid_bps,
    (r.expense_ratio_pct  - t.expense_ratio_pct)    * 100                  AS expense_resid_bps,
    CASE
        WHEN ABS((r.net_return_pct - t.net_return_pct) * 100) < 0.01 THEN 'RECONCILED'
        ELSE 'BREAK'
    END AS status
FROM V_VENDOR_RECON r
JOIN {{CI_SANDBOX_DB}}.DE_HOL_SHARED.VENDOR_FUND_PERFORMANCE_MONTHLY t
     ON  t.fund_code       = r.fund_code
     AND t.period_end_date = r.period_end_date;


-- -------------------------------------------------------------------------------------
-- Confirm the checkpoint worked. Expect 71 RECONCILED and 1 BREAK.
-- -------------------------------------------------------------------------------------
SELECT
    status,
    COUNT(*)                        AS rows,
    ROUND(MAX(ABS(net_resid_bps)), 6) AS worst_net_resid_bps
FROM V_VENDOR_RECON_RESIDUALS
GROUP BY status
ORDER BY status;
