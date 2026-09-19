# Parameterization

The test for every value in this file: **would this code run unchanged in sandbox and in
production?** If not, the value is configuration, not code.

## Database and schema names

Never name a database or schema inline in model SQL.

```sql
-- finding
FROM CI_SANDBOX.DE_HOL_SHARED.HOLDINGS_DAILY

-- required, in dbt
FROM {{ source('ci_shared', 'holdings_daily') }}

-- required, in plain SQL
FROM IDENTIFIER($source_schema || '.HOLDINGS_DAILY')
```

**Severity:** HIGH. A hardcoded database name is the single most common reason a model cannot be
promoted between environments without editing it — and editing SQL during a promotion is how
environments drift.

In dbt this also means the reference does not appear in the DAG, so lineage is wrong and
`dbt run --select +model` will not build the upstream dependency.

## Dates and reporting periods

```sql
-- finding
WHERE period_end_date BETWEEN '2025-01-01' AND '2025-12-31'
WHERE TO_CHAR(period_end_date, 'YYYY') = '2025'

-- required
WHERE period_end_date >= DATE_FROM_PARTS({{ var('reporting_year') }}, 1, 1)
  AND period_end_date <  DATE_FROM_PARTS({{ var('reporting_year') }} + 1, 1, 1)
```

**Severity:** HIGH. A hardcoded year is a silent failure: on 1 January the pipeline runs, succeeds,
and returns last year's data. Nothing alerts.

## Entity lists

```sql
-- finding
WHERE fund_code IN ('CIF-CAD-EQ-01','CIF-GLB-EQ-02','CIF-BAL-60-03',
                    'CIF-FIX-IN-04','CIF-USD-EQ-05','CIF-ALT-LS-06')

-- required
WHERE fund_code IN (SELECT fund_code FROM {{ source('ci_shared', 'fund_master') }})
-- or filter on an attribute: WHERE fm.is_active = TRUE
```

**Severity:** MEDIUM, HIGH if the list gates an outbound extract.

A hardcoded list of entities is correct on the day it is written and wrong the day CI launches a
fund. Worse, it fails silently — the new fund is simply absent. Derive the list, or filter on the
attribute that actually defines membership.

## Magic numbers

Named constants or vars, not literals buried in an expression. `252` appearing in a
business-day annualisation is acceptable with a comment; `0.15` appearing with no explanation is
a MEDIUM finding. Someone will need to know whether it is a fee rate, a threshold or a weight.

## Credentials, hostnames and connection strings

**Nothing of the sort belongs in the repo.** Not in code, not in a comment, not commented out,
not in a fixture.

- Credentials belong in a Snowflake secret, or in dbt Cloud's environment configuration.
- Hostnames and endpoints belong in configuration.
- Commenting out a credential does not remove it — it is in git history from the moment it is
  committed.

**Severity:** HIGH, always, with no exceptions and no follow-up ticket. This blocks deployment,
and the credential must be rotated because it has to be assumed compromised the moment it was
pushed.

Flag this even when the credential looks like a placeholder or a test value. The reviewer cannot
tell from reading the file, and the cost of asking is far lower than the cost of being wrong.
