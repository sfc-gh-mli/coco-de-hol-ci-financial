-- =====================================================================================
-- PRE-FLIGHT: AI functions
-- =====================================================================================
-- Confirms the sandbox can run everything Session 4 and prompt 2.4 depend on. Run this at
-- least 3 days before the workshop, as the attendee role, so there is time to fix anything.
--
-- WHY THIS CALLS THE FUNCTIONS INSTEAD OF CHECKING GRANTS
--   IS_DATABASE_ROLE_IN_SESSION('SNOWFLAKE.CORTEX_USER') can return FALSE on an account
--   where every AI function works fine -- access is often inherited through a path that
--   function does not reflect. Asserting on the grant produces false failures and sends you
--   chasing a problem you do not have. So the grant is reported as CONTEXT only, and the
--   verdict comes from whether each function actually executes.
--
-- Errors are caught per check, so one missing function does not stop the rest. You get a
-- single report with a verdict per lab step.
--
-- Replace {{CI_SANDBOX_DB}} and {{CI_ROLE}}, then run all statements.
-- =====================================================================================

USE ROLE {{CI_ROLE}};
USE DATABASE {{CI_SANDBOX_DB}};
USE SCHEMA DE_HOL_SHARED;


-- -------------------------------------------------------------------------------------
-- Informational context. None of this is a pass/fail gate -- read it alongside the report.
-- -------------------------------------------------------------------------------------
SELECT
    CURRENT_USER()                                              AS whoami,
    CURRENT_ROLE()                                              AS active_role,
    CURRENT_REGION()                                            AS region,
    CURRENT_WAREHOUSE()                                         AS warehouse,
    IS_DATABASE_ROLE_IN_SESSION('SNOWFLAKE.CORTEX_USER')        AS cortex_user_visible,
    IS_DATABASE_ROLE_IN_SESSION('SNOWFLAKE.CORTEX_AGENT_USER')  AS cortex_agent_user_visible;

-- Cross-region inference. AI_PARSE_DOCUMENT and AI_EXTRACT are native in a limited set of
-- regions; everywhere else they need this enabled. If the value is DISABLED and a check
-- below fails on region grounds, an ACCOUNTADMIN can run:
--     ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';
SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION' IN ACCOUNT;


-- -------------------------------------------------------------------------------------
-- Run the checks. Each one calls the real function and catches its own errors.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE TEMPORARY TABLE AI_PREFLIGHT_RESULTS (
    SEQ         NUMBER,
    CHECK_NAME  VARCHAR,
    NEEDED_BY   VARCHAR,
    VERDICT     VARCHAR,
    DETAIL      VARCHAR
);

DECLARE
    v_text    VARCHAR;
    v_variant VARIANT;
BEGIN
    -- 1 -- AI_COMPLETE, the baseline. If this fails, nothing else will work and the cause
    -- is almost always a missing SNOWFLAKE.CORTEX_USER grant.
    BEGIN
        SELECT AI_COMPLETE('claude-4-sonnet', 'Reply with exactly: OK') INTO :v_text;
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (1, 'AI_COMPLETE (baseline)', 'Everything', 'PASS', 'returned: ' || :v_text);
    EXCEPTION WHEN OTHER THEN
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (1, 'AI_COMPLETE (baseline)', 'Everything', 'FAIL',
             'Grant SNOWFLAKE.CORTEX_USER to the role. Error: ' || SQLERRM);
    END;

    -- 2 -- Structured output with an enforced response schema. Session 5 uses this to pin
    -- the SHAPE of an AI response as one rung on the determinism ladder.
    BEGIN
        SELECT AI_COMPLETE(
                   model => 'claude-4-sonnet',
                   prompt => 'Classify for PII: "Spoke with the client at (416) 555-0199."',
                   response_format => {
                       'type': 'json',
                       'schema': {
                           'type': 'object',
                           'properties': {
                               'verdict':    {'type': 'string'},
                               'confidence': {'type': 'number'}
                           },
                           'required': ['verdict', 'confidence']
                       }
                   }
               ) INTO :v_text;
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (2, 'AI_COMPLETE structured output', 'Session 5 (prompt 5.2)', 'PASS',
             'returned: ' || LEFT(:v_text, 120));
    EXCEPTION WHEN OTHER THEN
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (2, 'AI_COMPLETE structured output', 'Session 5 (prompt 5.2)', 'FAIL',
             'Prompt 5.2 falls back to discussing the pattern. Error: ' || SQLERRM);
    END;

    -- 3 -- AI_CLASSIFY. Used for the PII scan in Session 4.
    BEGIN
        SELECT AI_CLASSIFY('Spoke with the client at (416) 555-0199 to confirm.',
                           ['CONTAINS_PII', 'NO_PII']):labels[0]::VARCHAR
        INTO :v_text;
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (3, 'AI_CLASSIFY', 'Session 4 (prompt 4.1)',
             IFF(:v_text = 'CONTAINS_PII', 'PASS', 'PASS (unexpected label)'),
             'classified as: ' || :v_text);
    EXCEPTION WHEN OTHER THEN
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (3, 'AI_CLASSIFY', 'Session 4 (prompt 4.1)', 'FAIL',
             'Session 4 becomes a facilitator demo. Error: ' || SQLERRM);
    END;

    -- 4 -- AI_REDACT. Used to prove the outbound vendor extract can be made safe.
    BEGIN
        SELECT AI_REDACT('Call Priya Singh at (416) 555-0199 or priya@example-mail.ca')
        INTO :v_text;
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (4, 'AI_REDACT', 'Session 4 (prompt 4.1)', 'PASS', 'returned: ' || :v_text);
    EXCEPTION WHEN OTHER THEN
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (4, 'AI_REDACT', 'Session 4 (prompt 4.1)', 'FAIL',
             'Prompt 4.1 can still classify, but not redact. Error: ' || SQLERRM);
    END;

    -- 5 -- AI_EXTRACT. Pulls the vendor's stated claims out of prose.
    BEGIN
        SELECT AI_EXTRACT(
                   text => 'Returns are time-weighted and presented net of all fees.',
                   responseFormat => [['basis', 'What return basis is stated?']]
               ):response:basis::VARCHAR
        INTO :v_text;
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (5, 'AI_EXTRACT', 'Session 2 (prompt 2.4)', 'PASS', 'extracted: ' || :v_text);
    EXCEPTION WHEN OTHER THEN
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (5, 'AI_EXTRACT', 'Session 2 (prompt 2.4)', 'FAIL',
             'Build the claim table by hand instead. Error: ' || SQLERRM);
    END;

    -- 6 -- AI_PARSE_DOCUMENT against the actual staged PDF. This is the check most likely to
    -- fail, because it needs both the function AND script 00 to have uploaded the file.
    BEGIN
        SELECT TO_VARCHAR(
                   AI_PARSE_DOCUMENT(
                       TO_FILE('@{{CI_SANDBOX_DB}}.DE_HOL_SHARED.VENDOR_DOCS',
                               'meridian_performance_methodology_2025.pdf'),
                       {'mode': 'LAYOUT'}
                   ):content
               ) INTO :v_text;
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (6, 'AI_PARSE_DOCUMENT on staged PDF', 'Session 2 (prompt 2.4)',
             IFF(:v_text ILIKE '%time-weighted%', 'PASS', 'PASS (content unexpected)'),
             'parsed ' || LENGTH(:v_text) || ' chars; contains "time-weighted": '
             || IFF(:v_text ILIKE '%time-weighted%', 'yes', 'NO -- check the right file was uploaded'));
    EXCEPTION WHEN OTHER THEN
        INSERT INTO AI_PREFLIGHT_RESULTS VALUES
            (6, 'AI_PARSE_DOCUMENT on staged PDF', 'Session 2 (prompt 2.4)', 'FAIL',
             'Either the function is unavailable, or the PDF is not staged. Run LIST @VENDOR_DOCS to tell which. Error: '
             || SQLERRM);
    END;

    RETURN 'checks complete -- see the report below';
END;


-- -------------------------------------------------------------------------------------
-- THE REPORT
-- -------------------------------------------------------------------------------------
SELECT SEQ, CHECK_NAME, NEEDED_BY, VERDICT, DETAIL
FROM AI_PREFLIGHT_RESULTS
ORDER BY SEQ;


-- -------------------------------------------------------------------------------------
-- VERDICT
-- -------------------------------------------------------------------------------------
SELECT
    COUNT_IF(VERDICT LIKE 'PASS%')  AS passed,
    COUNT_IF(VERDICT = 'FAIL')      AS failed,
    CASE
        WHEN COUNT_IF(VERDICT = 'FAIL') = 0
            THEN 'READY -- Session 4 and prompt 2.4 will run as written'
        WHEN COUNT_IF(VERDICT = 'FAIL' AND SEQ = 1) > 0
            THEN 'BLOCKED -- AI_COMPLETE itself fails. Grant SNOWFLAKE.CORTEX_USER to the attendee role, then re-run'
        ELSE 'PARTIAL -- some functions unavailable. See facilitator/run-of-show.md, "Fallback: AI Functions unavailable"'
    END AS verdict
FROM AI_PREFLIGHT_RESULTS;


-- -------------------------------------------------------------------------------------
-- If check 6 failed, run this to tell a missing file apart from a missing function.
-- Expect exactly one row: meridian_performance_methodology_2025.pdf
-- -------------------------------------------------------------------------------------
-- LIST @{{CI_SANDBOX_DB}}.DE_HOL_SHARED.VENDOR_DOCS;
