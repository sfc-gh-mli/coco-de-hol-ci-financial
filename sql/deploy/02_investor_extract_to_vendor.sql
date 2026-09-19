-- Investor account extract supplied to Meridian Performance Analytics each month.
-- Author: (inherited)
--
-- NOTE: this script is deliberately non-compliant. It is the second review target for the
-- deployment-checklist skill built in Session 3, and it is the one with a real problem.
-- Do not "fix" it before then.

-- outbound vendor file
CREATE OR REPLACE TABLE CI_SANDBOX.DE_HOL_SHARED.VendorExtract_Accounts AS
SELECT
    ia.*,
    fm.FUND_NAME,
    fm.BENCHMARK_ID
FROM CI_SANDBOX.DE_HOL_SHARED.INVESTOR_ACCOUNTS ia
LEFT JOIN CI_SANDBOX.DE_HOL_SHARED.FUND_MASTER fm ON ia.FUND_CODE = fm.FUND_CODE
WHERE ia.ACCOUNT_OPEN_DATE < '2025-12-31'
;

-- quick sanity check before we hand the file over
SELECT COUNT(*) FROM CI_SANDBOX.DE_HOL_SHARED.VendorExtract_Accounts;

-- units reconciliation against holdings
-- TODO: this was throwing a divide by zero in November, wrapped it for now
CREATE OR REPLACE VIEW CI_SANDBOX.DE_HOL_SHARED.vw_UnitsRecon AS
SELECT
    e.FUND_CODE,
    SUM(e.UNITS_HELD) AS total_units,
    SUM(e.UNITS_HELD) / NULLIF(COUNT(DISTINCT e.ACCOUNT_ID), 0) AS avg_units_per_account,
    (SELECT SUM(QUANTITY) FROM CI_SANDBOX.DE_HOL_SHARED.HOLDINGS_DAILY h
      WHERE h.FUND_CODE = e.FUND_CODE AND h.AS_OF_DATE = '2025-12-31') AS total_quantity
FROM CI_SANDBOX.DE_HOL_SHARED.VendorExtract_Accounts e
GROUP BY e.FUND_CODE
;

-- connection details for the SFTP drop, kept here so the job is self-contained
-- host: sftp.meridian-analytics.example.com  user: ci_outbound  pw: Wint3r2025!drop
