# Optimization and query patterns

Ordered by how much damage each one does.

## SELECT * in anything that persists

Enumerate columns in any `CREATE TABLE AS`, `CREATE VIEW`, dbt model, or extract.

`SELECT *` is acceptable only in genuinely ad-hoc exploration that is not committed.

**Severity:** MEDIUM normally. **HIGH** when the source table contains PII, or when the output
leaves CI — see `security-and-pii.md`. The failure mode is not performance, it is that the column
set silently widens as upstream tables gain columns. Nobody decides to leak a new column; they
just never decided not to.

## Implicit cross joins

```sql
-- finding
FROM table_a a, table_b b
WHERE a.key = b.key

-- required
FROM table_a a
JOIN table_b b ON a.key = b.key
```

**Severity:** MEDIUM. Behaviourally equivalent here, but one dropped `WHERE` clause away from a
cartesian product, and the reader cannot tell an intentional cross join from a forgotten
predicate.

## Non-sargable predicates

Do not wrap a function around a column you are filtering on — it prevents partition pruning and
forces a full scan.

```sql
-- finding
WHERE TO_CHAR(period_end_date, 'YYYY') = '2025'
WHERE YEAR(period_end_date) = 2025

-- required
WHERE period_end_date >= '2025-01-01'
  AND period_end_date <  '2026-01-01'
```

**Severity:** MEDIUM, or HIGH on a table over roughly 100 million rows.

## Aggregations over percentage columns

Summing or averaging a percentage column is almost always wrong.

```sql
-- finding: returns do not add
SELECT fund_code, SUM(net_return_pct) AS ytd_net_return_pct

-- required: returns compound
SELECT fund_code,
       (EXP(SUM(LN(1 + net_return_pct / 100.0))) - 1) * 100 AS ytd_net_return_pct
```

**Severity:** HIGH. This produces a plausible-looking number that is simply incorrect, and it
will not be caught by any test that only checks for nulls. A `SUM` over monthly returns
overstates a positive year and understates a negative one.

An unweighted `AVG` of percentages across funds or accounts is the same error: it needs to be
weighted by assets.

## Correlated subqueries in the SELECT list

A scalar subquery per output row usually belongs as a join or a window function. Rewrite it.

**Severity:** MEDIUM. LOW if the outer query is provably small.

## Divide by zero

Wrap any denominator that can be zero or null in `NULLIF`. But check the intent first: a
`NULLIF` added to silence an error, with no thought about what a null result means downstream,
is itself a MEDIUM finding. A comment saying `-- TODO: was throwing divide by zero, wrapped it
for now` is a signal that nobody established whether null is the right answer.

## FLOAT for money

Monetary columns in anything client-facing are `NUMBER(n,2)`, never `FLOAT`. Binary floating
point cannot represent decimal currency exactly, and the error accumulates across aggregation.

**Severity:** HIGH in client-facing output, LOW in an intermediate calculation.

## Clustering

Do not recommend a clustering key from the schema alone. Base it on the columns actually used in
`WHERE` and `JOIN` predicates across the real query population, and say which queries it would
help. Note that clustering has an ongoing maintenance cost, so it is not a free improvement.

**Severity:** LOW — an observation, not a defect.
