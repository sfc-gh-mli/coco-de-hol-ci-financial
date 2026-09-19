# Naming conventions

## Case and format

- `snake_case` for everything: file names, model names, columns, aliases, CTE names.
- No `camelCase`, no `PascalCase`, no spaces, no hyphens.
- Names are nouns or noun phrases, not verb phrases. `monthly_performance_extract`, not
  `extract_monthly_performance`.

**Severity:** MEDIUM. Inconsistent naming is a maintenance cost rather than a correctness
problem — but it is the rule most often broken and the cheapest to fix.

## Prefixes by layer

| Layer | Prefix | Example |
|---|---|---|
| Staging | `stg_` | `stg_holdings_valued` |
| Dimension | `dim_` | `dim_fund` |
| Fact | `fact_` | `fact_fund_performance_monthly` |
| Intermediate | `int_` | `int_nav_daily` |
| View (non-dbt) | `vw_` | `vw_units_recon` |

A model with no recognisable layer prefix is a MEDIUM finding — it makes the DAG unreadable at a
glance.

## Column suffixes

These carry meaning and are not optional:

| Suffix | Use for | Example |
|---|---|---|
| `_pct` | Percentages, stored as percent so 1.5 means 1.5% | `net_return_pct` |
| `_bps` | Basis points | `net_resid_bps` |
| `_cad` | Currency amounts in Canadian dollars | `amount_cad` |
| `_ts` | Timestamps | `load_ts` |
| `_date` | Dates | `period_end_date` |
| `_id` | Surrogate or system identifiers | `security_id` |
| `_code` | Natural keys and business codes | `fund_code` |
| `_flag` | Booleans, or `Y`/`N` where a boolean is not available | `current_flag` |

A percentage column without `_pct` is a HIGH finding when the value is client-facing. The
percent-versus-decimal ambiguity is a factor-of-100 error waiting to happen, and it has reached
production at other firms.

## Abbreviations

- Spell words out. `performance`, not `perf`. `quantity`, not `qty`.
- Exceptions, because they are unambiguous in this domain: `nav`, `fx`, `pnl`, `ytd`, `mtd`,
  `bps`, `pct`, `id`.
- Never invent an abbreviation that is not already in CI's glossary.

**Severity:** LOW, except where the abbreviation is ambiguous. `mgmt_fee` is fine. `mf` is a
MEDIUM finding because it could be management fee or mutual fund.

## Aliases

- Table aliases are meaningful: `hold`, `px`, `fx`, not `a`, `b`, `c`.
- Single-letter aliases are a MEDIUM finding in any query with more than two tables. They are the
  reason nobody can review a six-table join.
- Alias every column in a `SELECT` that involves an expression. An unnamed computed column
  produces a generated name that downstream code will depend on.
