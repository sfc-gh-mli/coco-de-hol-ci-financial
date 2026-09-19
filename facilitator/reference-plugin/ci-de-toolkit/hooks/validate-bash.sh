#!/usr/bin/env bash
#
# PreToolUse hook --- blocks dbt commands that target production.
#
# At CI, dbt Cloud runs the project from Bitbucket on a schedule. A production dbt run from a
# laptop bypasses code review, bypasses the CI pipeline, and is not reproducible.
#
# This is a hook rather than a line in AGENTS.md on purpose. An instruction asks the agent to
# comply; a hook makes compliance unnecessary. It fires BEFORE the command executes, which also
# means it works when dbt is not installed at all --- the guardrail does not depend on the tool
# being present.
#
# Cortex Code passes the tool input as JSON on stdin. Exit 0 allows, exit 2 blocks with the
# message on stderr.

set -uo pipefail

INPUT="$(cat)"

# Pull out the command. Try jq first, then fall back to grep.
#
# The fallback triggers whenever jq yields nothing --- not only when jq is missing. jq being
# installed but failing on unexpected input would otherwise leave COMMAND empty, and an empty
# COMMAND means "allow", which would let a production run through. A guardrail must not
# fail open because a parser had a bad day.
COMMAND=""
if command -v jq >/dev/null 2>&1; then
    COMMAND="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // .command // empty' 2>/dev/null)"
fi
if [ -z "${COMMAND:-}" ]; then
    COMMAND="$(printf '%s' "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' \
        | head -1 | sed 's/.*:[[:space:]]*"//; s/"$//')"
fi

# Genuinely nothing to inspect. Allow, rather than blocking every command in the session --- a
# hook that blocks everything when it cannot read its input gets disabled, which is worse than
# no hook. Anything containing a command string reaches the checks below via the grep fallback.
if [ -z "${COMMAND:-}" ]; then
    exit 0
fi

# Only dbt commands are in scope.
case "$COMMAND" in
    *dbt*) ;;
    *) exit 0 ;;
esac

# --target prod, -t prod, and the common variants. Tolerates = or space, and matches
# prod/production/prd as whole words so --target production_mirror is still caught.
if printf '%s' "$COMMAND" | grep -Eqi -- '(--target|-t)[[:space:]=]+(prod|production|prd)([[:space:]]|$)'; then
    cat >&2 <<'MSG'
BLOCKED: production dbt runs are not permitted from a local machine.

At CI Financial, dbt Cloud runs this project from Bitbucket on a schedule. Running dbt against
production locally bypasses code review and the CI pipeline, and the result is not reproducible.

What to do instead:
  - Test against your own schema:   dbt build --target sandbox --project-dir dbt/
  - Verify the numbers in Snowflake by materialising the compiled SQL
  - Commit to a feature/ branch and open a PR --- dbt Cloud will run it

If you genuinely need a production run outside the schedule, that is a dbt Cloud job triggered
by someone with production access, not a laptop command.
MSG
    exit 2
fi

# Also block --full-refresh against production, which is more destructive than a normal run.
if printf '%s' "$COMMAND" | grep -Eqi -- '--full-refresh' \
   && printf '%s' "$COMMAND" | grep -Eqi -- 'prod'; then
    echo "BLOCKED: --full-refresh against production would rebuild tables from scratch. Use dbt Cloud." >&2
    exit 2
fi

exit 0
