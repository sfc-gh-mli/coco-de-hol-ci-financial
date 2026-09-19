# Bundled skills worth knowing — a CI data engineer's shortlist

Cortex Code ships with skills that encode Snowflake-specific knowledge the base model does not
reliably have. You do not invoke most of them by name; the agent matches your request against
each skill's description and loads the relevant one.

The distinction that matters:

- **Bundled skills** carry Snowflake product knowledge — how storage lifecycle policies behave,
  what makes a dynamic table refresh incrementally, which `ACCOUNT_USAGE` view answers a cost
  question. Maintained by Snowflake, always available.
- **Custom skills** carry *your* conventions — CI's naming rules, CI's deployment checklist,
  CI's definition of done. Nobody else can write those for you. That is Session 3.

You do not need a skill for standard SQL, Python or dbt syntax. The model already knows those,
and a skill that re-teaches them only burns context.

---

## The shortlist

Ordered by how often a CI data engineer is likely to reach for them.

| Skill | Reach for it when | Why it earns its place here |
|---|---|---|
| `sql-author` | Writing or repairing any non-trivial SQL | Catches the traps that return a *wrong answer* rather than an error: join fanout, `NULL` comparison, integer division, `UNION` vs `UNION ALL`. Exactly the failure mode that matters when the output is a client-facing return figure. |
| `data-quality` | Standing up monitoring on fund, holdings or NAV tables | DMF attachment, health scoring, incident investigation. Turns "we think the feed is fine" into a measured assertion. |
| `lineage` | Before changing a shared column or deprecating a model | Answers "what breaks if I change this" and "where did this column come from". The question to ask *before* touching a model the committee pack depends on. |
| `workload-performance-analysis` | A query got slow, or you want clustering candidates | Spilling, partition pruning, cache hit rates, search-optimization candidates — read from `ACCOUNT_USAGE` rather than guessed. |
| `cost-intelligence` | Attributing warehouse credits to a pipeline or team | Credit usage by warehouse, user and service; budgets and resource monitors. Also covers Cortex AI spend, which becomes relevant once AI functions are in a pipeline. |
| `dynamic-tables` | Building incremental transformation outside dbt Cloud | Target lag, incremental vs full refresh, and why a refresh silently went full. Useful when a dbt schedule is the wrong granularity. |
| `snowflake-tasks` | Scheduling anything, including the validation procedure from Session 5 | Task graphs, `WHEN` conditions, stream triggers, and why a task auto-suspended. |
| `data-governance` | Classifying or masking investor data | PII classification, masking and row-access policies, tag-based policy. Directly relevant to the outbound vendor extract problem in Session 4. |
| `cortex-ai-function-studio` | Choosing or tuning an AI function | Which built-in function fits, how to structure a prompt, how to evaluate output. The reference behind Session 4. |
| `snowpark-python` | Python transforms | Flags the places Snowpark DataFrame semantics differ from pandas in ways that silently produce different numbers. |
| `skill-development` | Writing or auditing your own skills | Used live in Session 3. Also covers refactoring a skill that has grown too large. |
| `verification-skill` | Before a change lands | Read-only previews and structured verification of SQL and dbt changes. |

---

## Two worth knowing about, with a caveat

**`dbt-projects-on-snowflake`** — this one is about dbt deployed *as a Snowflake object* via the
`snow dbt` CLI (`EXECUTE DBT PROJECT`, `CREATE DBT PROJECT`). It is **not** about dbt Cloud.
Since CI runs dbt Cloud from Bitbucket, this skill is not your path, and asking for it will
send the agent down the wrong road. Named here specifically so you can set it aside.

For CI's workflow, treat dbt as ordinary code: the agent writes and reviews the model SQL, and
dbt Cloud executes it. No special skill needed.

**`migration-guide`** — worth knowing if any legacy Oracle or SQL Server logic is still in
scope. It handles source-dialect conversion properly rather than guessing at an equivalent.

---

## How to find out what applies

Rather than memorising the list, ask:

```
I need to <describe the task>. Which of your bundled skills apply here, and which
would send me down the wrong path given that CI runs dbt Cloud from Bitbucket?
```

The second half of that question is the useful part. Asking what *does not* apply surfaces the
`dbt-projects-on-snowflake` trap and anything similar.

---

## When to write a custom skill instead

The test is whether the knowledge is **yours**. If you catch yourself starting a prompt with
*"remember, we always..."*, that is a custom skill waiting to be written.

| Situation | Bundled or custom |
|---|---|
| How dynamic table refresh works | Bundled — Snowflake product behaviour |
| That CI prefixes staging models `stg_` | Custom — your convention |
| Which `ACCOUNT_USAGE` view holds query history | Bundled |
| That CI requires a PII review before any outbound extract | Custom |
| How to write a window function | Neither — the model knows |
| CI's pre-deployment checklist | Custom — Session 3 builds exactly this |

Keep custom skills under roughly 500 lines. When one grows past that, split the detail into a
`resources/` folder and let the skill point at the relevant file — which is the pattern
Session 3 demonstrates.
