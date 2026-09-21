# Cortex Code Data Engineering HOL — CI Financial

A 2 hour 15 minute hands-on lab. Attendees use **Cortex Code Desktop** against **CI Financial's
own sandbox** to reverse-engineer a third-party vendor's fund performance calculations, encode
CI's deployment standards as a shareable skill, apply AI functions to document extraction and PII
detection, and make the whole thing reproducible with a stored procedure.

No trial accounts. No Openflow. Sessions 1 through 5 need nothing but a Snowflake connection.

**Toronto, ON — 9:00 AM to 11:15 AM**

---

## The scenario

CI Financial sends daily holdings, prices, FX rates and cash flows to a performance vendor,
"Meridian Performance Analytics". Meridian returns monthly NAV, returns, benchmark and excess
figures — 72 rows covering six funds across 2025 — plus a three-page methodology statement that
is confident, prose-heavy, and vague where it matters.

Nobody at CI can reproduce those numbers. The lab is about being able to defend them.

The dataset is built so the target **is genuinely reverse-engineerable**: seven specific
undocumented methodology choices, discoverable in order by measuring residuals and reading what
they correlate with. Applying all seven reproduces **71 of 72 rows to better than 0.0001 bps**.
The 72nd is a deliberate outlier that teaches segmentation.

Of the vendor's seven stated claims, **five are contradicted by the data**.

---

## Sessions

| # | Session | Time | Prompts | Needs |
|---|---|---|---|---|
| 1 | Connect & Ground | 20 min | 3 | Snowflake |
| 2 | Reverse-Engineer the Vendor Dataset | 35 min | 4 | Snowflake |
| 3 | Custom Skills & Sharing | 20 min | 2 | Local files only |
| 4 | AI Functions for Data Engineering | 15 min | 2 | Snowflake + `CORTEX_USER` |
| 5 | Determinism | 20 min | 2 | Snowflake |
| 6 | dbt to Production **(stretch)** | 15 min | 2 | dbt Cloud + Bitbucket |

**Session 6 is deliberately last and deliberately isolated.** It is the only session touching dbt
Cloud or Bitbucket, and nothing depends on it. If that tooling is not ready, it runs as a
walkthrough and the first five sessions are unaffected. Sessions 2 and 5 each have a checkpoint
script so falling behind costs nothing later.

This ordering is intentional: dbt is CI's toolchain, not one of the four things their manager
asked to see. Those four — which bundled skills help, using the agent to write and run analysis,
building and sharing custom skills, and determinism — all land in Sessions 1 through 5.

---

## Repository layout

```
├── workshop_guide/              # the Streamlit app attendees follow
│   ├── streamlit_app.py
│   ├── components.py
│   ├── app_pages/               # home, getting_started, agenda, session_01..06
│   ├── static/                  # fonts and logos
│   └── _test_all_pages.py       # smoke test: renders every page, checks the completion mechanic
├── data/
│   ├── source/                  # 11 source CSVs (~51k rows)
│   ├── target/                  # the vendor's monthly performance table (72 rows)
│   ├── documents/               # Meridian's methodology statement (PDF)
│   └── ci_fund_data.zip         # everything above, bundled
├── scripts/
│   ├── 00_facilitator_load_shared.sql   # run once, 3 days ahead
│   ├── 01_attendee_schema.sql           # run once per attendee
│   ├── 02_selfload_fallback.sql
│   └── checkpoints/                     # catch-up scripts for Sessions 2 and 5
├── sql/deploy/                  # deliberately non-compliant SQL — Session 3's review target
├── dbt/                         # starter project standing in for CI's Bitbucket repo
├── docs/connect-coco-desktop.md # pre-read: SSO connection setup
├── skills_reference/            # curated bundled-skill shortlist for CI
└── facilitator/                 # ANSWER KEY — do not circulate
    ├── SOLUTION.md              # the seven rules, with proving SQL per rule
    ├── run-of-show.md           # minute by minute, cut order, decision points
    ├── troubleshooting.md
    ├── generator/               # the data generator (encodes the seven rules)
    └── reference-plugin/        # the finished ci-de-toolkit plugin
```

> **`facilitator/` is spoiler material.** It contains the answers, including the generator that
> produces the target by applying the seven rules. The repo is public, so anyone determined can
> read it — but keeping it in one clearly-labelled directory means nobody stumbles into it.

---

## Placeholders to fill in

Five values are unknown until CI provides them. They are deliberately left as markers rather than
guessed, so a wrong value cannot hide in plain sight.

| Placeholder | What it is |
|---|---|
| `{{CI_ACCOUNT_IDENTIFIER}}` | Sandbox account identifier, `orgname-accountname` |
| `{{CI_USERNAME}}` | Attendee's SSO login |
| `{{CI_ROLE}}` | Role attendees use |
| `{{CI_WAREHOUSE}}` | Warehouse attendees use |
| `{{CI_SANDBOX_DB}}` | Sandbox database |

Find every occurrence with:

```bash
grep -rn '{{CI_' --include='*.py' --include='*.sql' --include='*.md' --include='*.yml' .
```

Attendee schemas follow `DE_HOL_<INITIALS>`; shared data lives in `DE_HOL_SHARED`.

---

## Facilitator setup

> **The dataset is already generated and committed.** You do not need to run the generator —
> `data/source/`, `data/target/` and `data/documents/` are in the repo. Step 2 loads those files
> straight into Snowflake.

1. **Fill in the five placeholders.**
2. **Load the shared schema** — `scripts/00_facilitator_load_shared.sql`, at least 3 days ahead.
   Upload the committed CSVs and the PDF to the stages it creates, then run the `COPY INTO`
   statements. The script has the upload commands and a row-count check.
3. **Create attendee schemas** — `scripts/01_attendee_schema.sql`, once per attendee.
4. **Confirm AI functions work** in the sandbox region and that the role has
   `SNOWFLAKE.CORTEX_USER`. Session 4 and prompt 2.4 need it; `run-of-show.md` has the fallback.
5. **Send `docs/connect-coco-desktop.md`** as a pre-read.
6. **Read `facilitator/SOLUTION.md`** and run the lab yourself once.

### Optional: regenerating the dataset

Only needed if you are changing the scenario or the methodology rules, or you want to confirm the
puzzle still holds. See `facilitator/generator/README.md` for the detail.

```bash
python3 -m pip install -r facilitator/generator/requirements.txt

# Runs from any directory --- output paths resolve from the script's own location.
python3 facilitator/generator/generate_data.py --verify
python3 facilitator/generator/generate_vendor_doc.py
```

`--verify` asserts the exercise still works: each rule detectable, each residual correlated with
a driver an attendee would test, the discovery ladder monotone, 71 of 72 rows reconciling, and the
December outlier still visible. Use `--no-write` to check without touching the committed CSVs.

---

## Running the app

```bash
cd workshop_guide
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python 'streamlit>=1.51.0'
.venv/bin/streamlit run streamlit_app.py
```

Streamlit 1.51+ is required (the app uses `st.space()`), which needs Python 3.10+.

Smoke test:

```bash
cd workshop_guide && .venv/bin/python _test_all_pages.py
```

Deploy to Streamlit Community Cloud by pointing a new app at `workshop_guide/streamlit_app.py`.

---

## What was verified

| Check | Result |
|---|---|
| Puzzle solvability — all seven rules detectable and correctly ordered | Automated in `--verify` |
| Reconciliation: 71 of 72 rows | Worst residual 0.00005 bps |
| December outlier stays unreconciled | 13.4 bps, ~260,000x the others |
| Reconciliation SQL numerics | Validated in Snowflake against hand-derived values to 10 dp |
| Stored procedure determinism | Two runs, identical results, distinct provenance |
| Production-safety hook | 11 cases; blocks with dbt absent; does not fail open without `jq` |
| All 9 app pages | Render with zero exceptions |
| Sessions 1–5 dbt independence | No dbt or git execution dependency |

---

## Credits

Built on the [Cortex Code HOL template](https://github.com/sfc-gh-obenning/coco-hol-template),
with content patterns from the
[Data Engineering with CoCo guide](https://www.snowflake.com/en/developers/guides/data-engineering-with-coco/)
and the [Air Canada DE HOL](https://github.com/sfc-gh-snotebaert/ac-coco-de-hol).

All data is synthetic. "Meridian Performance Analytics" is fictional. The funds, securities,
investors and advisors do not exist.
