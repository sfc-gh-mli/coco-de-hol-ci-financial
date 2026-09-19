-- =====================================================================================
-- CHECKPOINT: after Session 5
-- =====================================================================================
-- Purpose
--   Puts an attendee back on the main line if they did not finish the determinism session.
--   Creates the audit table and the deterministic validation procedure directly, so
--   Session 6 (dbt) can start clean.
--
-- Prerequisite
--   scripts/checkpoints/after_session_02.sql must have run first --- this procedure reads
--   V_VENDOR_RECON_RESIDUALS.
--
-- Usage
--   1. Replace {{CI_SANDBOX_DB}} with the sandbox database name.
--   2. Replace DE_HOL_XX with the attendee's own schema.
--   3. Run all statements.
-- =====================================================================================

USE DATABASE {{CI_SANDBOX_DB}};
USE SCHEMA DE_HOL_XX;


-- -------------------------------------------------------------------------------------
-- Audit table. One row per fund-month per run.
--
-- Note the deliberate split between RESULT columns and PROVENANCE columns. The result
-- columns are fully determined by the inputs and must be identical across runs. RUN_ID and
-- RUN_TS are provenance: they are supposed to differ every run, because that is how you
-- tell two runs apart. "Deterministic" means the answer is stable, not that the audit trail
-- is frozen.
-- -------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS VENDOR_RECON_RESULTS (
    -- provenance: expected to vary run to run
    RUN_ID              VARCHAR       NOT NULL,
    RUN_TS              TIMESTAMP_LTZ NOT NULL,
    RUN_BY              VARCHAR       NOT NULL,
    -- inputs
    PARAM_FUND_CODE     VARCHAR,
    PARAM_PERIOD_END    DATE,
    -- result: must be byte-identical for identical inputs
    FUND_CODE           VARCHAR       NOT NULL,
    PERIOD_END_DATE     DATE          NOT NULL,
    ENDING_NAV_DIFF     FLOAT,
    GROSS_RESID_BPS     FLOAT,
    NET_RESID_BPS       FLOAT,
    BENCH_RESID_BPS     FLOAT,
    EXCESS_RESID_BPS    FLOAT,
    EXPENSE_RESID_BPS   FLOAT,
    STATUS              VARCHAR       NOT NULL
);


-- -------------------------------------------------------------------------------------
-- The deterministic validation procedure.
--
-- This is the whole point of Session 5: the agreed calculation lives in the database, not
-- in a prompt. Given the same inputs it returns the same answer every time, and the answer
-- does not depend on who ran it or how they phrased the request.
--
-- Parameters are referenced with a leading colon inside the body. Without it Snowflake
-- treats P_FUND_CODE as a column identifier and raises "invalid identifier" --- the single
-- most common error when writing SQL stored procedures.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE SP_VALIDATE_VENDOR_PERFORMANCE(
    P_FUND_CODE  VARCHAR,
    P_PERIOD_END DATE
)
RETURNS VARCHAR
LANGUAGE SQL
COMMENT = 'Reconciles vendor-reported fund performance against CI-derived values. Pass ALL for every fund and NULL for every period. Writes one row per fund-month to VENDOR_RECON_RESULTS and returns a deterministic summary.'
AS
$$
DECLARE
    v_run_id      VARCHAR;
    v_reconciled  INTEGER;
    v_breaks      INTEGER;
    v_worst       FLOAT;
BEGIN
    v_run_id := UUID_STRING();

    INSERT INTO VENDOR_RECON_RESULTS (
        RUN_ID, RUN_TS, RUN_BY, PARAM_FUND_CODE, PARAM_PERIOD_END,
        FUND_CODE, PERIOD_END_DATE, ENDING_NAV_DIFF,
        GROSS_RESID_BPS, NET_RESID_BPS, BENCH_RESID_BPS,
        EXCESS_RESID_BPS, EXPENSE_RESID_BPS, STATUS
    )
    SELECT
        :v_run_id,
        CURRENT_TIMESTAMP(),
        CURRENT_USER(),
        :P_FUND_CODE,
        :P_PERIOD_END,
        r.fund_code,
        r.period_end_date,
        r.ending_nav_diff,
        r.gross_resid_bps,
        r.net_resid_bps,
        r.bench_resid_bps,
        r.excess_resid_bps,
        r.expense_resid_bps,
        r.status
    FROM V_VENDOR_RECON_RESIDUALS r
    WHERE (:P_FUND_CODE = 'ALL' OR r.fund_code = :P_FUND_CODE)
      AND (:P_PERIOD_END IS NULL OR r.period_end_date = :P_PERIOD_END);

    SELECT COUNT(*) INTO :v_reconciled
    FROM VENDOR_RECON_RESULTS
    WHERE RUN_ID = :v_run_id AND STATUS = 'RECONCILED';

    SELECT COUNT(*) INTO :v_breaks
    FROM VENDOR_RECON_RESULTS
    WHERE RUN_ID = :v_run_id AND STATUS = 'BREAK';

    SELECT COALESCE(MAX(ABS(NET_RESID_BPS)), 0) INTO :v_worst
    FROM VENDOR_RECON_RESULTS
    WHERE RUN_ID = :v_run_id;

    -- The return value deliberately excludes RUN_ID and the timestamp so that two runs over
    -- the same inputs produce a byte-identical string. That is the property Session 5
    -- demonstrates.
    RETURN 'reconciled=' || :v_reconciled
        || ' breaks='    || :v_breaks
        || ' worst_net_resid_bps=' || TO_VARCHAR(ROUND(:v_worst, 4));
END;
$$;


-- -------------------------------------------------------------------------------------
-- Confirm determinism. Both calls must return an identical string.
-- Expected: reconciled=71 breaks=1 worst_net_resid_bps=13.xxxx
-- -------------------------------------------------------------------------------------
CALL SP_VALIDATE_VENDOR_PERFORMANCE('ALL', NULL);
CALL SP_VALIDATE_VENDOR_PERFORMANCE('ALL', NULL);


-- Same result columns across the two runs, different provenance. Expect ZERO rows: every
-- fund-month produced exactly one distinct result regardless of which run it came from.
SELECT
    FUND_CODE,
    PERIOD_END_DATE,
    COUNT(DISTINCT STATUS)                    AS distinct_statuses,
    COUNT(DISTINCT ROUND(NET_RESID_BPS, 10))  AS distinct_residuals,
    COUNT(DISTINCT RUN_ID)                    AS runs
FROM VENDOR_RECON_RESULTS
GROUP BY FUND_CODE, PERIOD_END_DATE
HAVING COUNT(DISTINCT STATUS) > 1
    OR COUNT(DISTINCT ROUND(NET_RESID_BPS, 10)) > 1
ORDER BY FUND_CODE, PERIOD_END_DATE;
