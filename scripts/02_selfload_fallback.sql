-- =====================================================================================
-- FALLBACK: load the data yourself
-- =====================================================================================
-- Use this only if the facilitator's shared schema is unavailable and you need to load the
-- dataset into your own schema. The normal path is scripts/00_facilitator_load_shared.sql,
-- run once by the facilitator.
--
-- Replace {{CI_SANDBOX_DB}} and DE_HOL_XX, then run.
-- =====================================================================================

USE DATABASE {{CI_SANDBOX_DB}};
USE SCHEMA DE_HOL_XX;

CREATE OR REPLACE FILE FORMAT CSV_WITH_HEADER
    TYPE = CSV
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'NULL')
    EMPTY_FIELD_AS_NULL = TRUE
    DATE_FORMAT = 'YYYY-MM-DD';

CREATE STAGE IF NOT EXISTS MY_RAW_CSV FILE_FORMAT = CSV_WITH_HEADER;
CREATE STAGE IF NOT EXISTS MY_VENDOR_DOCS DIRECTORY = (ENABLE = TRUE);

-- Upload from the repo root. PUT needs a client that supports it --- the Snowflake CLI or a
-- driver session. Snowsight's stage UI works too (Data > Databases > ... > Stages > + Files).
--
--   snow stage copy data/source/*.csv     @{{CI_SANDBOX_DB}}.DE_HOL_XX.MY_RAW_CSV/
--   snow stage copy data/target/*.csv     @{{CI_SANDBOX_DB}}.DE_HOL_XX.MY_RAW_CSV/
--   snow stage copy data/documents/*.pdf  @{{CI_SANDBOX_DB}}.DE_HOL_XX.MY_VENDOR_DOCS/
--
-- Then confirm:  LIST @MY_RAW_CSV;   LIST @MY_VENDOR_DOCS;

-- Table DDL is identical to the shared schema. Rather than duplicate 150 lines here, clone
-- the structures from the facilitator script if the shared schema exists:
--
--   CREATE TABLE FUND_MASTER LIKE {{CI_SANDBOX_DB}}.DE_HOL_SHARED.FUND_MASTER;
--
-- If it does not exist, copy the CREATE TABLE block out of
-- scripts/00_facilitator_load_shared.sql --- it is the authoritative definition.

-- Schema-on-read alternative: skip DDL entirely and let Snowflake infer the columns.
-- Convenient for a fallback, but the inferred types are looser than the explicit DDL, so
-- prefer the explicit path when you have the choice.
CREATE OR REPLACE TABLE VENDOR_FUND_PERFORMANCE_MONTHLY
    USING TEMPLATE (
        SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
        FROM TABLE(
            INFER_SCHEMA(
                LOCATION => '@MY_RAW_CSV/vendor_fund_performance_monthly.csv',
                FILE_FORMAT => 'CSV_WITH_HEADER'
            )
        )
    );

COPY INTO VENDOR_FUND_PERFORMANCE_MONTHLY
    FROM @MY_RAW_CSV/vendor_fund_performance_monthly.csv
    MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;

SELECT COUNT(*) AS rows_loaded, 72 AS expected FROM VENDOR_FUND_PERFORMANCE_MONTHLY;
