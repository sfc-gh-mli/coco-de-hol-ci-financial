-- =====================================================================================
-- FACILITATOR SETUP --- run once, at least 3 days before the workshop
-- =====================================================================================
-- Creates the shared read-only schema every attendee reads from, loads the 11 source
-- tables plus the vendor target, and stages the vendor methodology PDF for AI_PARSE_DOCUMENT.
--
-- WHY A SHARED SCHEMA
--   Six people racing PUT in the first fifteen minutes will cost you the whole first
--   session. Load once, grant SELECT, and let attendees spend the lab on the actual work.
--   Attendees write only to their own DE_HOL_<INITIALS> schema.
--
-- BEFORE YOU RUN
--   Replace these placeholders throughout:
--     {{CI_SANDBOX_DB}}   the sandbox database
--     {{CI_ROLE}}         the role attendees will use
--     {{CI_WAREHOUSE}}    the warehouse attendees will use
--
-- This script is idempotent. Re-running it reloads the data from scratch.
-- =====================================================================================

USE ROLE {{CI_ROLE}};
USE WAREHOUSE {{CI_WAREHOUSE}};
USE DATABASE {{CI_SANDBOX_DB}};

CREATE SCHEMA IF NOT EXISTS DE_HOL_SHARED
    COMMENT = 'Read-only source data for the Cortex Code Data Engineering HOL. Attendees read from here and write to their own DE_HOL_<INITIALS> schema.';

USE SCHEMA DE_HOL_SHARED;


-- -------------------------------------------------------------------------------------
-- Stages and file format
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE FILE FORMAT CSV_WITH_HEADER
    TYPE = CSV
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'NULL')
    EMPTY_FIELD_AS_NULL = TRUE
    DATE_FORMAT = 'YYYY-MM-DD';

CREATE STAGE IF NOT EXISTS RAW_CSV
    FILE_FORMAT = CSV_WITH_HEADER
    COMMENT = 'Landing stage for the HOL source CSVs.';

-- DIRECTORY must be enabled so AI_PARSE_DOCUMENT can resolve the staged PDF in Session 2.
CREATE STAGE IF NOT EXISTS VENDOR_DOCS
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Vendor-supplied documents. Read by AI_PARSE_DOCUMENT in Session 2.';


-- =====================================================================================
-- UPLOAD THE FILES  --- do this now, before continuing past this point
-- =====================================================================================
-- Option A --- Snowflake CLI (recommended, scriptable):
--
--   cd <repo root>
--   snow stage copy data/source/*.csv @{{CI_SANDBOX_DB}}.DE_HOL_SHARED.RAW_CSV/
--   snow stage copy data/target/*.csv @{{CI_SANDBOX_DB}}.DE_HOL_SHARED.RAW_CSV/
--   snow stage copy data/documents/*.pdf @{{CI_SANDBOX_DB}}.DE_HOL_SHARED.VENDOR_DOCS/
--
-- Option B --- Snowsight UI:
--   Data > Databases > {{CI_SANDBOX_DB}} > DE_HOL_SHARED > Stages > RAW_CSV > "+ Files",
--   then upload every file from data/source/ and data/target/. 
-- Repeat for the stage VENDOR_DOCS and updload the Meridian PDF from data/documents/.
--
-- Confirm before continuing --- expect 12 CSVs and 1 PDF:
--   LIST @RAW_CSV;
--   LIST @VENDOR_DOCS;
-- =====================================================================================


-- -------------------------------------------------------------------------------------
-- Tables --- these mirror the CSV headers exactly, in column order
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE FUND_MASTER (
    FUND_CODE       VARCHAR      COMMENT 'Natural key. Format CIF-<mandate>-<nn>.',
    FUND_NAME       VARCHAR,
    ASSET_CLASS     VARCHAR,
    BASE_CURRENCY   VARCHAR      COMMENT 'Reporting currency. CAD for every fund in this dataset.',
    MGMT_FEE_BPS    NUMBER(6,2)  COMMENT 'Annual management fee in basis points.',
    ADMIN_FEE_BPS   NUMBER(6,2)  COMMENT 'Annual administration fee in basis points.',
    PERF_FEE_RATE   FLOAT        COMMENT 'Performance fee as a decimal rate. Zero for all but one fund.',
    BENCHMARK_ID    VARCHAR,
    INCEPTION_DATE  DATE
) COMMENT = 'Fund reference data, one row per mandate.';

CREATE OR REPLACE TABLE BENCHMARK_MASTER (
    BENCHMARK_ID    VARCHAR,
    BENCHMARK_NAME  VARCHAR,
    IS_BLEND        VARCHAR COMMENT 'Y for multi-component benchmarks.'
) COMMENT = 'Benchmark reference data.';

CREATE OR REPLACE TABLE BENCHMARK_COMPONENTS (
    BENCHMARK_ID        VARCHAR,
    INDEX_CODE          VARCHAR,
    WEIGHT              FLOAT   COMMENT 'Target weight. Single-index benchmarks carry weight 1.',
    REBALANCE_FREQUENCY VARCHAR
) COMMENT = 'Benchmark composition. Blends have one row per component.';

CREATE OR REPLACE TABLE SECURITY_MASTER (
    SECURITY_ID     NUMBER,
    TICKER          VARCHAR,
    SECURITY_NAME   VARCHAR,
    SECTOR          VARCHAR,
    CURRENCY        VARCHAR COMMENT 'Local trading currency. CAD, USD or EUR.',
    ASSET_TYPE      VARCHAR
) COMMENT = 'Security reference data.';

CREATE OR REPLACE TABLE HOLDINGS_DAILY (
    FUND_CODE       VARCHAR,
    AS_OF_DATE      DATE,
    SECURITY_ID     NUMBER,
    QUANTITY        FLOAT   COMMENT 'Units held at the close of AS_OF_DATE, after any same-day flow.'
) COMMENT = 'Daily position snapshots. Grain: fund x date x security.';

CREATE OR REPLACE TABLE PRICES_DAILY (
    SECURITY_ID         NUMBER,
    PRICE_DATE          DATE,
    CLOSE_PRICE_LOCAL   FLOAT COMMENT 'Closing price in the security local currency, not CAD.',
    CURRENCY            VARCHAR
) COMMENT = 'Daily closing prices in local currency. Grain: security x date.';

CREATE OR REPLACE TABLE FX_RATES_DAILY (
    RATE_DATE       DATE,
    FROM_CURRENCY   VARCHAR,
    TO_CURRENCY     VARCHAR,
    RATE            FLOAT COMMENT 'Units of TO_CURRENCY per one unit of FROM_CURRENCY.'
) COMMENT = 'Daily FX rates including a CAD-to-CAD identity row so joins need no special casing. Starts 2024-12-24 so that January 2025 has a prior business day available.';

CREATE OR REPLACE TABLE CASH_FLOWS (
    FUND_CODE   VARCHAR,
    FLOW_DATE   DATE,
    FLOW_TYPE   VARCHAR COMMENT 'SUBSCRIPTION, REDEMPTION or DISTRIBUTION.',
    AMOUNT_CAD  FLOAT   COMMENT 'Always positive. FLOW_TYPE carries the direction.'
) COMMENT = 'External cash flows and income distributions. Note that distributions are recorded here but are not necessarily treated as external flows for return purposes.';

CREATE OR REPLACE TABLE FUND_EXPENSES_DAILY (
    FUND_CODE           VARCHAR,
    ACCRUAL_DATE        DATE,
    MGMT_FEE_ACCRUED    FLOAT,
    ADMIN_FEE_ACCRUED   FLOAT,
    OTHER_EXPENSE       FLOAT COMMENT 'Custody, audit, legal and other ordinary operating costs.'
) COMMENT = 'Daily expense accruals struck on that day NAV. Grain: fund x date.';

CREATE OR REPLACE TABLE INDEX_RETURNS_DAILY (
    INDEX_CODE          VARCHAR,
    RETURN_DATE         DATE,
    TOTAL_RETURN_PCT    FLOAT COMMENT 'Daily total return in PERCENT, so 1.5 means 1.5 percent.'
) COMMENT = 'Daily index total returns. Grain: index x date.';

CREATE OR REPLACE TABLE INVESTOR_ACCOUNTS (
    ACCOUNT_ID          VARCHAR,
    FUND_CODE           VARCHAR,
    INVESTOR_NAME       VARCHAR,
    EMAIL               VARCHAR,
    PHONE               VARCHAR,
    CITY                VARCHAR,
    PROVINCE            VARCHAR,
    ADVISOR_NAME        VARCHAR,
    UNITS_HELD          FLOAT,
    ACCOUNT_OPEN_DATE   DATE,
    KYC_NOTES           VARCHAR COMMENT 'Free-text advisor notes. Some rows embed personal identifiers mid-sentence.'
) COMMENT = 'Retail investor accounts. Used in Session 4 to prove that outbound vendor extracts carry no investor PII.';

CREATE OR REPLACE TABLE VENDOR_FUND_PERFORMANCE_MONTHLY (
    FUND_CODE               VARCHAR,
    PERIOD_END_DATE         DATE    COMMENT 'Last business day of the reporting month.',
    BEGINNING_NAV           FLOAT,
    ENDING_NAV              FLOAT,
    NET_FLOWS               FLOAT   COMMENT 'As reported by the vendor. Check what it does and does not include.',
    GROSS_RETURN_PCT        FLOAT,
    NET_RETURN_PCT          FLOAT,
    BENCHMARK_RETURN_PCT    FLOAT,
    EXCESS_RETURN_PCT       FLOAT,
    EXPENSE_RATIO_PCT       FLOAT   COMMENT 'Annualised.',
    YTD_NET_RETURN_PCT      FLOAT
) COMMENT = 'THE TARGET. Produced by Meridian Performance Analytics from the source tables in this schema. The methodology is undocumented beyond a three-page prose statement. Grain: fund x month.';


-- -------------------------------------------------------------------------------------
-- Load
-- -------------------------------------------------------------------------------------
COPY INTO FUND_MASTER                     FROM @RAW_CSV/fund_master.csv;
COPY INTO BENCHMARK_MASTER                FROM @RAW_CSV/benchmark_master.csv;
COPY INTO BENCHMARK_COMPONENTS            FROM @RAW_CSV/benchmark_components.csv;
COPY INTO SECURITY_MASTER                 FROM @RAW_CSV/security_master.csv;
COPY INTO HOLDINGS_DAILY                  FROM @RAW_CSV/holdings_daily.csv;
COPY INTO PRICES_DAILY                    FROM @RAW_CSV/prices_daily.csv;
COPY INTO FX_RATES_DAILY                  FROM @RAW_CSV/fx_rates_daily.csv;
COPY INTO CASH_FLOWS                      FROM @RAW_CSV/cash_flows.csv;
COPY INTO FUND_EXPENSES_DAILY             FROM @RAW_CSV/fund_expenses_daily.csv;
COPY INTO INDEX_RETURNS_DAILY             FROM @RAW_CSV/index_returns_daily.csv;
COPY INTO INVESTOR_ACCOUNTS               FROM @RAW_CSV/investor_accounts.csv;
COPY INTO VENDOR_FUND_PERFORMANCE_MONTHLY FROM @RAW_CSV/vendor_fund_performance_monthly.csv;

ALTER STAGE VENDOR_DOCS REFRESH;


-- -------------------------------------------------------------------------------------
-- Grants --- attendees read, never write
-- -------------------------------------------------------------------------------------
GRANT USAGE ON SCHEMA DE_HOL_SHARED              TO ROLE {{CI_ROLE}};
GRANT SELECT ON ALL TABLES IN SCHEMA DE_HOL_SHARED TO ROLE {{CI_ROLE}};
GRANT USAGE ON FILE FORMAT CSV_WITH_HEADER       TO ROLE {{CI_ROLE}};
GRANT READ ON STAGE VENDOR_DOCS                  TO ROLE {{CI_ROLE}};


-- -------------------------------------------------------------------------------------
-- Verify the load. Every ACTUAL must equal EXPECTED.
-- -------------------------------------------------------------------------------------
SELECT 'FUND_MASTER' AS table_name, COUNT(*) AS actual, 6 AS expected FROM FUND_MASTER
UNION ALL SELECT 'BENCHMARK_MASTER',      COUNT(*),     5 FROM BENCHMARK_MASTER
UNION ALL SELECT 'BENCHMARK_COMPONENTS',  COUNT(*),     6 FROM BENCHMARK_COMPONENTS
UNION ALL SELECT 'SECURITY_MASTER',       COUNT(*),    60 FROM SECURITY_MASTER
UNION ALL SELECT 'HOLDINGS_DAILY',        COUNT(*), 30972 FROM HOLDINGS_DAILY
UNION ALL SELECT 'PRICES_DAILY',          COUNT(*), 16020 FROM PRICES_DAILY
UNION ALL SELECT 'FX_RATES_DAILY',        COUNT(*),   801 FROM FX_RATES_DAILY
UNION ALL SELECT 'CASH_FLOWS',            COUNT(*),    38 FROM CASH_FLOWS
UNION ALL SELECT 'FUND_EXPENSES_DAILY',   COUNT(*),  1602 FROM FUND_EXPENSES_DAILY
UNION ALL SELECT 'INDEX_RETURNS_DAILY',   COUNT(*),  1068 FROM INDEX_RETURNS_DAILY
UNION ALL SELECT 'INVESTOR_ACCOUNTS',     COUNT(*),   420 FROM INVESTOR_ACCOUNTS
UNION ALL SELECT 'VENDOR_FUND_PERFORMANCE_MONTHLY', COUNT(*), 72 FROM VENDOR_FUND_PERFORMANCE_MONTHLY
ORDER BY table_name;

-- The staged PDF must be visible to AI_PARSE_DOCUMENT. Expect exactly one row.
LIST @VENDOR_DOCS;
