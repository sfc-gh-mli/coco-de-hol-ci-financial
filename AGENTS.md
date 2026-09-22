# AGENTS.md

## Snowflake environment

- Database `CI_SANDBOX_DB`, warehouse `DOC_AI_WH`, role `DATA_ENGINEER`.
- `DE_HOL_SHARED` holds the source data and is **read only**. Never write to it.
- All objects you create go in `DE_HOL_1`.

## Conventions

- Model files, columns and aliases are `snake_case`.
- Reference raw tables through dbt's `_sources.yml` with `source()`. Never name the
  database and schema inline in model SQL.
- Database names, schema names, reporting dates and year boundaries are parameterised
  through dbt vars or `env_var`. Never hardcode them.
- Every model's primary key gets `not_null` and `unique` tests.
- Monetary columns are `NUMBER`, never `FLOAT`, in anything client-facing.
- Percentage columns are stored as percent (`1.5` means 1.5%) and suffixed `_pct`.

## Workflow

- dbt Cloud runs this project from Bitbucket on a schedule. Never run dbt against
  production locally, and never use `--target prod`.
- Use `dbt build`, not `dbt run`, so tests run alongside compilation.
- Feature branches are `feature/<ticket>-<description>`. PRs required before merge.
- In-lab verification happens with SQL in Snowflake, not with `dbt build`.

## Agent behaviour

- This project uses Cortex Code Desktop. Do not use the `cortex` CLI — write files directly.
- Before writing SQL against a table, `DESCRIBE` it rather than assuming column names.
