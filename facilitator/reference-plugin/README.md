# Reference plugin — answer key

**Facilitator only.** This is the finished `ci-de-toolkit` that attendees build in Session 3.

It lives here, under `facilitator/`, and **not** at `.cortex/plugins/` — deliberately. Cortex
Code auto-discovers plugins from `.cortex/plugins/` in a trusted workspace, so a finished plugin
sitting there would activate on day one and short-circuit the entire session.

## Using it

**During the workshop:** don't install it. If a table is stuck on the skill structure, show them
`skills/deployment-checklist/SKILL.md` and point out how short it is relative to the
`resources/` folder — that is usually the insight they are missing.

**After the workshop:** attendees can copy it into a real repo as a starting point:

```bash
cp -r facilitator/reference-plugin/ci-de-toolkit .cortex/plugins/
```

Then reopen the workspace, accept trust, and check Settings → Plugins.

## Contents

```
ci-de-toolkit/
├── .cortex-plugin/
│   ├── plugin.json                  # manifest: name, version, skills, agents, hooks
│   └── activation.md                # shown when the plugin activates
├── skills/deployment-checklist/
│   ├── SKILL.md                     # 61 lines — workflow and which resource to read when
│   └── resources/
│       ├── naming-conventions.md    # case, prefixes, column suffixes, abbreviations
│       ├── optimization.md          # SELECT *, cross joins, sargability, percentage aggregation
│       ├── parameterization.md      # hardcoded schemas, dates, entity lists, credentials
│       └── security-and-pii.md      # investor PII, outbound extracts, masking vs AI_REDACT
├── agents/
│   └── dbt-review.md                # autonomous reviewer, PASS/FAIL per category
└── hooks/
    ├── hooks.json                   # wires validate-bash.sh to PreToolUse, matcher "bash"
    └── validate-bash.sh             # blocks dbt --target prod
```

Note the proportions: `SKILL.md` is 61 lines and the resources total roughly 330. That ratio is
the point of the session. Inlining all of it would produce a ~400-line skill that loads the PII
rules every time someone reviews a staging view.

## Verified behaviour

The hook was tested across eleven cases. It blocks `--target prod`, `-t prod`,
`--target=production`, `--target prd`, and `--full-refresh` against anything matching `prod`. It
allows `--target sandbox`, `dbt debug`, and non-dbt commands.

Two properties worth knowing, because both are easy to get wrong:

- **It blocks with dbt not installed.** `PreToolUse` fires before execution, so the guardrail does
  not depend on the tool being present. This is what makes it demonstrable in Session 3 regardless
  of anyone's local setup.
- **It does not fail open.** An earlier version used `jq` when present and fell back to `grep`
  only when `jq` was missing — so `jq` installed but erroring left the command string empty, and
  an empty command means allow. It now falls back whenever extraction yields nothing. Tested with
  `jq` present, `jq` present-but-failing, and `jq` absent.

The subagent determines scope through five fallbacks, from explicit paths down to a glob over all
models, so an unreachable Bitbucket remote reduces what it reviews rather than stopping the run.

## If you want to extend it

The natural next resources, in rough order of value to CI:

- `resources/testing-standards.md` — what every model must assert, beyond the grain
- `resources/incremental-models.md` — when incremental is worth the complexity, and how to
  handle late-arriving data
- `resources/documentation.md` — what a model description has to contain to be useful

Add the file, then add one row to the routing table in `SKILL.md`. That is the whole change —
which is the maintainability argument for this structure, made concrete.
