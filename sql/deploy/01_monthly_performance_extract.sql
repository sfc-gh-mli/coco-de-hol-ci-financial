-- Monthly fund performance extract for the investment committee pack.
-- Author: (inherited, original author no longer at CI)
-- Runs on the last business day of each month.
--
-- NOTE: this script is deliberately non-compliant. It is the review target for the
-- deployment-checklist skill built in Session 3. Do not "fix" it before then.

CREATE OR REPLACE TABLE CI_SANDBOX.DE_HOL_SHARED.monthlyPerfExtract AS
SELECT
    *
FROM CI_SANDBOX.DE_HOL_SHARED.VENDOR_FUND_PERFORMANCE_MONTHLY v
WHERE v.PERIOD_END_DATE >= '2025-01-01'
  AND v.PERIOD_END_DATE <= '2025-12-31'
  AND v.FUND_CODE IN ('CIF-CAD-EQ-01','CIF-GLB-EQ-02','CIF-BAL-60-03','CIF-FIX-IN-04','CIF-USD-EQ-05','CIF-ALT-LS-06')
;

-- enrich with fund details
CREATE OR REPLACE TABLE CI_SANDBOX.DE_HOL_SHARED.monthlyPerfExtract_final AS
SELECT
    a.*,
    b.FUND_NAME,
    b.ASSET_CLASS,
    b.MGMT_FEE_BPS + b.ADMIN_FEE_BPS AS TotalFeeBps,
    CASE WHEN a.EXCESS_RETURN_PCT > 0 THEN 'OUTPERFORM' ELSE 'UNDERPERFORM' END AS perf_flag,
    CURRENT_TIMESTAMP() AS load_ts
FROM CI_SANDBOX.DE_HOL_SHARED.monthlyPerfExtract a,
     CI_SANDBOX.DE_HOL_SHARED.FUND_MASTER b
WHERE a.FUND_CODE = b.FUND_CODE
;

-- committee wants the year-to-date figure recomputed here rather than trusting the vendor
SELECT
    FUND_CODE,
    SUM(NET_RETURN_PCT) AS ytd_net_return_pct
FROM CI_SANDBOX.DE_HOL_SHARED.monthlyPerfExtract_final
WHERE TO_CHAR(PERIOD_END_DATE, 'YYYY') = '2025'
GROUP BY FUND_CODE
ORDER BY 2 DESC
;
