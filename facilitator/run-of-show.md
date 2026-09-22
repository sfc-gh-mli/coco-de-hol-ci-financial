# Run of show — CI Financial DE HOL

**2 hours 15 minutes. 9:00 AM to 11:15 AM. Toronto, in person.**

Six sessions, 15 prompts. Sessions 1–5 need only the Snowflake connection. Session 6 is the
only one that touches dbt Cloud and Bitbucket, and nothing depends on it.

---

## Before the day

| When | What | Why it matters |
|---|---|---|
| T−7 days | Get the sandbox account identifier and role from CI. Fill in the five placeholders (see repo README). | These are the only unknowns in the repo. |
| T−7 days | Email `docs/connect-coco-desktop.md` as a pre-read and ask attendees to install Cortex Code Desktop **and sign in** before arriving. | Connection setup is the single biggest time sink in a BYO-environment lab. |
| T−3 days | Run `scripts/00_facilitator_load_shared.sql` to load `DE_HOL_SHARED`. Confirm the attendee role can `SELECT` from it. | Six people racing `PUT` in the first 15 minutes will cost you the whole first session. |
| T−3 days | Run `scripts/01_attendee_schema.sql` once per attendee with their initials. | Nobody should be creating schemas during the lab. |
| T−3 days | Confirm the attendee role carries `SNOWFLAKE.CORTEX_USER` and that `AI_PARSE_DOCUMENT` / `AI_CLASSIFY` / `AI_REDACT` are available in the sandbox's region. | Session 4 and prompt 2.4 depend on this. See the fallback below. |
| T−1 day | Run the whole lab yourself against the sandbox. | Every unpleasant surprise you find now is one you do not find in front of the room. |
| T−1 day | Read `facilitator/SOLUTION.md` properly. | You will be steering on it live, under time pressure. |

---

## Minute by minute

| Time | Session | Your job |
|---|---|---|
| 9:00–9:05 | Welcome | Frame the scenario, not the technology. The question is *"can you defend these numbers?"* Do not mention AI Functions or plugins yet. |
| 9:05–9:25 | **1. Connect & Ground** | Get everyone connected and past the pre-flight check. **Announce the Session 6 decision here** (see below). Keep 1.3 brisk — the skills table is a reference, not a lecture. |
| 9:25–10:00 | **2. Reverse-Engineer** | The heart of the lab. Circulate. Do not give rules away. The one nudge worth repeating is in the box below. |
| 10:00–10:20 | **3. Custom Skills** | Watch for workspace-trust problems on 3.2. Have the sharing conversation — this is the part their manager cares most about. |
| 10:20–10:35 | **4. AI Functions** | Tight. Two prompts, 15 minutes. If 4.2 runs long, let it — the PII finding lands better than a rushed wrap. |
| 10:35–10:55 | **5. Determinism** | The payoff session. The run-it-twice contrast is the moment; make sure everyone actually sees it rather than reading about it. |
| 10:55–11:10 | **6. dbt (stretch)** | Hands-on or walkthrough, per your 9:05 announcement. |
| 11:10–11:15 | Wrap | Tie back to the four things their manager asked for. Named below. |

---

## The only nudge you should give in Session 2

> *"Stop trying to match the whole number. Compute your version, join it to theirs, and look at
> what the difference is correlated with."*

That single sentence unlocks the session without giving away a rule. Attendees who are stuck are
almost always trying to guess a formula rather than measure a residual. Say it as often as
needed; never name the rule.

If a table is genuinely blocked at 9:50, give them rule 2 (distributions) — it is the loudest
signal and finding it builds enough momentum to get the rest.

---

## The Session 6 decision point

At 9:10, after prompt 1.1, you will have the pre-flight output from every attendee. Decide then:

- **All green** (dbt installed, Bitbucket remote reachable) → Session 6 runs hands-on.
- **Mixed or red** → announce immediately that Session 6 will be a walkthrough you drive, and
  redistribute the 15 minutes: 10 minutes to Session 2, 5 minutes to Session 5.

Say the decision out loud at 9:10 either way. An attendee who spends the morning quietly
worrying whether their dbt setup will embarrass them in the last 15 minutes is not paying
attention to the first 100.

---

## If you are running long

Cut in this order. Every item is safe to cut — nothing downstream depends on any of them.

1. **Prompt 2.4** (the AI_EXTRACT claim diff). Costs 8 minutes. Painful to lose because it is
   the best moment in the lab, but it is additive to Session 2 rather than load-bearing.
2. **Session 6 entirely.** Costs 15 minutes. Already flagged as stretch.
3. **Session 4 entirely** (the PII classify and redact). Costs 15 minutes. It is now a single
   prompt, so there is no partial cut available — either run it or drop the session. If you are
   short by less than that, drop steps 4 and 7 (the redaction demo and the two-run comparison) and
   keep steps 1–3, which carry the finding. Losing step 7 costs Session 5 its concrete example of
   AI non-determinism, so mention it verbally instead.
4. **Prompt 1.3** (bundled skills tour) → point at `skills_reference/recommended-bundled-skills.md`
   and move on. Costs 5 minutes.

Do **not** cut Session 5. Determinism is one of the four things their manager explicitly asked
for, and it is the session that reframes everything before it.

## If you are ahead of schedule

- Have attendees run the full seven-rule reconciliation against all six funds rather than one.
- In Session 3, add a second resource file to the skill and show how the agent picks only the
  relevant one.
- In Session 5, actually run the bare-prompt contrast that the session only describes: in two fresh
  sessions, ask *"reconcile the vendor performance figures and tell me which fund-months break"*
  and diff the two answers against each other and against the procedure's output. This was cut from
  the prompts because it costs 5 minutes and needs two clean contexts, but it is the single most
  convincing demonstration in the lab if you have the time — the answers are usually both *right*
  and never the *same*.

---

## Fallback: AI Functions unavailable

If `AI_PARSE_DOCUMENT`, `AI_CLASSIFY` or `AI_REDACT` are not enabled in the sandbox region, or
the role lacks `SNOWFLAKE.CORTEX_USER`:

- **Prompt 2.4** → have attendees read the PDF and build the claim table by hand from
  `facilitator/SOLUTION.md`'s stated-versus-actual table. The finding is the same; only the
  extraction method changes.
- **Session 4** → run it as a facilitator demo from your own account, or skip and give the
  15 minutes to Sessions 2 and 5.

Test this at T−3 days. Finding out at 10:20 is avoidable.

---

## What to say in the wrap

Their manager asked for four things. Name each one and where it landed:

1. **Which skills help data engineers** → Session 1, and `skills_reference/recommended-bundled-skills.md`
   to take away. The point: bundled skills for Snowflake-specific knowledge, custom skills for
   CI's own conventions.
2. **Using the agent to write and run analysis code** → Session 2. The point: the agent was
   useful because it could *execute* — test a hypothesis, measure the residual, discard the
   hypothesis. It did not know the answer and never guessed it.
3. **Custom skills, and sharing them** → Session 3. The point: `resources/` keeps the skill
   maintainable, and committing it to Bitbucket means the team gets it with `git pull` — no install
   step. For rules that should span every repo, the Snowflake stage and account-catalog routes are
   in the session's sharing section.
4. **Determinism** → Session 5. The point: prompts are probabilistic; stored procedures are not.
   Move agreed logic into the database and the agent's job becomes invoking it, not recomputing it.

Then the honest closing point: they now have a documented, reproducible challenge to send
Meridian, built in under two hours, on data they already had. Five of the vendor's seven stated
methodology claims do not survive contact with that data.

---

## Artifacts attendees leave with

- `AGENTS.md` — CI conventions
- `docs/vendor_methodology_reconstructed.md` — seven rules with proving SQL
- `VENDOR_METHODOLOGY_CLAIMS` — stated-versus-actual diff
- `.snowflake/cortex/skills/deployment-checklist/` — skill + 4-file `resources/` folder
- `SP_VALIDATE_VENDOR_PERFORMANCE` + `VENDOR_RECON_RESULTS` + a scheduled task
- A dbt model on a feature branch (if Session 6 ran hands-on)

Tell them the repo stays public so they can re-run any of it. Point them at
`docs/connect-coco-desktop.md` for doing this against a real CI environment.
