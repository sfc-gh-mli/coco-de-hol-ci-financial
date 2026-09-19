# dbt project — CI EDW

This is a **starter project**, not CI's real dbt repo.

## How this maps to CI's actual setup

CI authors models locally in Cortex Code Desktop, commits to **Bitbucket**, and **dbt Cloud**
runs the project on a schedule. This directory stands in for that Bitbucket repo so Session 6
has something concrete to work in. To use it for real, point the remote at CI's repo and
migrate the `models/` directory across.

Because dbt Cloud owns execution, **in-lab verification happens with SQL in Snowflake**, not
with `dbt build`. Session 6 has Cortex Code materialise the compiled SELECT into your own
schema so you can check the numbers in the room, then stage the commit for dbt Cloud to pick up.

## Layout

```
dbt/
├── dbt_project.yml
├── profiles.yml.example        # local runs only; dbt Cloud holds its own connection config
└── models/
    ├── _sources.yml            # every raw reference goes through here
    ├── staging/
    │   └── stg_HoldingsValued.sql   # deliberately non-compliant — Session 3 review target
    └── marts/                  # you build fund_performance_monthly here in Session 6
```

## Conventions

Encoded in `AGENTS.md` (which you create in Session 1) and checked by the
`deployment-checklist` skill (which you build in Session 3):

- Model files and columns are `snake_case`.
- Raw tables are referenced through `{{ source() }}`, never by naming the database and schema
  inline.
- Database, schema and reporting year come from `vars` or `env_var`, never hardcoded.
- Every model's primary key carries `not_null` and `unique` tests.
- `dbt build`, not `dbt run`, so tests run with compilation.
- Feature branches follow `feature/<ticket>-<description>`; PRs are required before merge.

`models/staging/stg_HoldingsValued.sql` violates several of these on purpose. Leave it alone
until Session 3.

## Running locally (optional)

Only needed if you want `dbt build` to work in the room. Session 6 runs fine without it.

```bash
mkdir -p ~/.dbt && cp dbt/profiles.yml.example ~/.dbt/profiles.yml
# fill in the placeholders, then:
dbt debug --project-dir dbt/
dbt build --project-dir dbt/
```
