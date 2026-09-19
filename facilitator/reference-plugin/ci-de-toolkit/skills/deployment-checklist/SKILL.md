---
name: deployment-checklist
description: Run CI Financial's pre-deployment review over SQL or dbt code. Use when asked to review code before deploying, check whether something is ready to ship, run a pre-deployment or pre-merge check, or code review SQL or a dbt model.
---

# CI Pre-Deployment Review

Review code against CI's standards and report findings. **Never modify the code** — this skill
produces a review, not a fix. If asked to fix the findings, confirm first and treat it as a
separate task.

## Workflow

1. **Establish scope.** Identify the files to review. If the request is ambiguous, ask rather
   than guessing — reviewing the wrong files wastes the reviewer's time and erodes trust in the
   output.

2. **Read the relevant rules.** Do not rely on general knowledge of good SQL. Read the resource
   files that apply to the code in front of you:

   | Read this | When the code |
   |---|---|
   | `resources/naming-conventions.md` | Always |
   | `resources/optimization.md` | Always |
   | `resources/parameterization.md` | Always |
   | `resources/security-and-pii.md` | Touches investor, account or advisor data, OR produces an extract that leaves CI |

   Read `security-and-pii.md` whenever there is any doubt. A false positive costs a reviewer a
   minute; a miss goes to a vendor.

3. **Check each file** against the rules in those resources.

4. **Report findings** as a single table, ordered by severity then file:

   | File | Line | Category | Severity | Current code | Required fix |
   |---|---|---|---|---|---|

   - **Category** is one of NAMING, OPTIMIZATION, PARAMETERIZATION, SECURITY.
   - **Severity** is HIGH, MEDIUM or LOW. Use the severity guidance in each resource file
     rather than your own judgement.
   - **Required fix** must be specific to this code. "Use better naming" is not a fix;
     "rename `monthlyPerfExtract` to `monthly_performance_extract`" is.
   - Quote the actual offending code, not a paraphrase.

5. **Summarise and recommend.** Counts by severity, then an explicit verdict:

   - **DO NOT DEPLOY** — any HIGH finding.
   - **DEPLOY WITH FOLLOW-UP** — MEDIUM findings only. List what must be ticketed.
   - **APPROVED** — LOW findings or none.

   State the verdict plainly. Do not soften it, and do not bury it under the findings table.

## Rules for this review

- Report every instance, not just the first of each kind. Three hardcoded schema names are
  three findings.
- If a file is clean in a category, say so explicitly. Silence reads as an oversight.
- Flag anything suspicious that is not covered by the resource files, under the closest
  category, and note that the rules do not yet cover it. That is how the rules improve.
- Do not comment on formatting or whitespace unless a resource file calls for it.
