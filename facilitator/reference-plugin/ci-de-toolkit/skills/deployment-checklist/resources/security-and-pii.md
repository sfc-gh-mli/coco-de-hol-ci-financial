# Security and investor PII

Read this whenever the code touches investor, account or advisor data, or produces anything that
leaves CI. When in doubt, read it — a false positive costs a reviewer a minute, a miss reaches a
third party.

## What counts as investor PII

**Direct identifiers**, in `INVESTOR_ACCOUNTS` and anything derived from it:

`INVESTOR_NAME`, `EMAIL`, `PHONE`, and any street address. `ACCOUNT_ID` is a direct identifier in
combination with anything else.

**Quasi-identifiers**, which re-identify in combination even though each is harmless alone:

`CITY` plus `PROVINCE` plus `ACCOUNT_OPEN_DATE` plus `UNITS_HELD` will single out a client in a
small fund. Do not treat these as safe because no single column names anyone.

**Free text is PII until proven otherwise.**

`KYC_NOTES` is advisor commentary. Identifiers appear mid-sentence, in prose, with no predictable
format: names, phone numbers, email addresses, partial government ID references, addresses,
named beneficiaries and joint account holders. A regex over email and phone patterns catches
roughly half and misses the rest.

Any free-text column is a HIGH finding in an outbound extract unless it has been explicitly
redacted or excluded.

**Advisor names** are employee PII. Lower sensitivity than client data, but still not for
external distribution.

## Outbound extracts

An extract is anything written to a stage, file, share, or table that a third party reads. CI
sends Meridian a monthly file, and Meridian's own contract requires it to be free of personal
information not needed for the service.

Rules:

1. **Columns are enumerated explicitly. `SELECT *` over a table containing PII is automatically
   HIGH.** Not MEDIUM — HIGH. The mechanism matters: nobody decides to send investor names to a
   vendor. Someone writes `SELECT *`, an upstream table gains a column, and the extract widens
   with no change to the code and no diff to review.

2. **Direct identifiers are dropped, not masked**, unless the recipient demonstrably needs them.
   A performance vendor needs account-level units and fund allocation. It does not need to know
   who the investor is.

3. **Free text is excluded, or redacted with `AI_REDACT`.** If notes are not needed, omit them —
   redaction is a control, not a reason to include data nobody asked for.

4. **Any change that widens the column set of an outbound extract is HIGH** and requires review
   regardless of what the new column contains.

## Masking policies versus AI_REDACT

They solve different problems and CI needs both. Recommending one where the other belongs is a
MEDIUM finding.

| Use | When |
|---|---|
| **Masking policy** | The column is known to hold an identifier — `EMAIL`, `PHONE`, `INVESTOR_NAME`. Deterministic, enforced at query time, role-aware. Always prefer this where it applies. |
| **`AI_REDACT`** | Free text where the identifier's position is not predictable — `KYC_NOTES`. The only option when a policy cannot express the rule. |

A masking policy is the stronger control because it is deterministic and cannot be bypassed by
querying differently. Use `AI_REDACT` only where a policy genuinely cannot do the job.

## Also flag

- PII in a `TEMPORARY` or `TRANSIENT` table without a comment explaining the lifecycle. Transient
  does not mean invisible.
- PII columns used as a join key where a surrogate key exists.
- Logging or `SELECT` output in a procedure that would write PII to a query history or an event
  table.
- Sample data, fixtures or test cases containing real-looking investor records.

## Severity

| Finding | Severity |
|---|---|
| Credential in the repo | HIGH — blocks deployment, rotate the credential |
| Direct identifier in an outbound extract | HIGH |
| `SELECT *` over a PII-bearing table | HIGH |
| Un-redacted free text in an outbound extract | HIGH |
| Quasi-identifier combination externally, without review | MEDIUM |
| Advisor name externally | MEDIUM |
| PII in a transient table, undocumented | LOW |

Any HIGH finding in this category means **DO NOT DEPLOY**. Do not offer a follow-up ticket as an
alternative, and do not soften the verdict because the fix looks small.
