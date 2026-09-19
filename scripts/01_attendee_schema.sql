-- =====================================================================================
-- ATTENDEE SCHEMA --- run once per attendee, at least 3 days before the workshop
-- =====================================================================================
-- Each attendee needs somewhere to write: views, a stored procedure, an audit table, a
-- task. Nobody should be creating schemas during the lab.
--
-- Replace {{CI_SANDBOX_DB}}, {{CI_ROLE}} and XX (the attendee's initials), then run.
-- Repeat for every attendee. Two people must not share a schema --- Session 5 has them
-- creating objects with fixed names.
-- =====================================================================================

USE ROLE {{CI_ROLE}};
USE DATABASE {{CI_SANDBOX_DB}};

CREATE SCHEMA IF NOT EXISTS DE_HOL_XX
    COMMENT = 'Working schema for one Cortex Code DE HOL attendee. Safe to drop after the workshop.';

GRANT USAGE  ON SCHEMA DE_HOL_XX TO ROLE {{CI_ROLE}};
GRANT CREATE VIEW      ON SCHEMA DE_HOL_XX TO ROLE {{CI_ROLE}};
GRANT CREATE TABLE     ON SCHEMA DE_HOL_XX TO ROLE {{CI_ROLE}};
GRANT CREATE PROCEDURE ON SCHEMA DE_HOL_XX TO ROLE {{CI_ROLE}};
GRANT CREATE FUNCTION  ON SCHEMA DE_HOL_XX TO ROLE {{CI_ROLE}};
GRANT CREATE TASK      ON SCHEMA DE_HOL_XX TO ROLE {{CI_ROLE}};
GRANT CREATE STAGE     ON SCHEMA DE_HOL_XX TO ROLE {{CI_ROLE}};

-- Session 5 resumes a task. Without EXECUTE TASK on the account the attendee can create
-- the task but not start it. If your security posture does not allow this grant, that is
-- fine --- see facilitator/troubleshooting.md, "The task will not start". The task object
-- is the deliverable; the schedule is a bonus.
GRANT EXECUTE TASK ON ACCOUNT TO ROLE {{CI_ROLE}};


-- -------------------------------------------------------------------------------------
-- Confirm: the attendee can read shared data and write to their own schema.
-- -------------------------------------------------------------------------------------
USE SCHEMA DE_HOL_XX;

CREATE OR REPLACE TEMPORARY TABLE _WRITE_TEST AS
SELECT COUNT(*) AS shared_rows
FROM {{CI_SANDBOX_DB}}.DE_HOL_SHARED.VENDOR_FUND_PERFORMANCE_MONTHLY;

SELECT
    CURRENT_USER()    AS whoami,
    CURRENT_ROLE()    AS active_role,
    CURRENT_SCHEMA()  AS my_schema,
    shared_rows,
    CASE WHEN shared_rows = 72 THEN 'READY' ELSE 'SHARED DATA NOT LOADED' END AS status
FROM _WRITE_TEST;
