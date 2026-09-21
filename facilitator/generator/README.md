# Data generator

**You almost certainly do not need to run this.**

The dataset is already generated and committed:

```
data/source/         11 CSVs, ~51k rows
data/target/         vendor_fund_performance_monthly.csv (72 rows)
data/documents/      meridian_performance_methodology_2025.pdf
data/ci_fund_data.zip
```

Facilitator setup uses `scripts/00_facilitator_load_shared.sql` to load those files into
Snowflake. The generator is only here so the dataset is reproducible and auditable.

**Spoiler warning:** these scripts encode all seven answers to the Session 2 exercise.

---

## When you would run it

- You want to change the scenario — different funds, fee levels, date range, flow sizes.
- You want to add or alter one of the seven methodology rules.
- You want to confirm for yourself that the puzzle is still solvable before running the lab.
- You are adapting this workshop for a different customer.

## How to run it

Install the dependencies once:

```bash
python3 -m pip install -r facilitator/generator/requirements.txt
```

Then run from **anywhere** — both scripts resolve their output paths from the script's own
location, so they always write into this repo's `data/` directory regardless of your working
directory:

```bash
python3 facilitator/generator/generate_data.py --verify
python3 facilitator/generator/generate_vendor_doc.py
```

Runtime is about 10 seconds for the data and under a second for the PDF.

### What the flags do

| Command | Effect |
|---|---|
| `generate_data.py` | Write the CSVs. No checking. |
| `generate_data.py --verify` | Write the CSVs, then assert the puzzle is solvable. **Use this one.** |
| `generate_data.py --no-write` | Verify only, leaving the committed CSVs untouched. Useful for checking without a dirty working tree. |

## What `--verify` actually asserts

This is the part that matters if you change anything. It is not a smoke test — it checks that
the exercise still *works as a teaching exercise*:

- **Each rule is detectable.** Every residual falls in a band that is noticeable but small enough
  to be mistaken for rounding at first glance.
- **Each residual correlates with a driver an attendee would actually think to test** — FX moves,
  flow size and timing, business-day count, return magnitude — at |corr| above the threshold.
- **The discovery ladder is monotone.** Fixing rules in discovery order must shrink the mean
  absolute residual at every step, so attendees get feedback that they are converging. A
  regression here fails the run.
- **71 of 72 rows reconcile** to better than 0.01 bps once all seven rules are applied.
- **The December performance-fee row does not reconcile**, by at least 5 bps, so the outlier
  stays visible.
- **The investor PII mix is 30–60%**, so "flag everything" scores badly, and a regex baseline
  leaves a measurable gap for `AI_CLASSIFY` to close.

If you change the scenario and `--verify` fails, tune the volatility and flow magnitudes — not
the rules. The failure message names which property broke.

## Reproducibility

Seeded with `20260918`. Regenerating without code changes produces **byte-identical** output for
the 12 CSVs and the PDF:

```bash
python3 facilitator/generator/generate_data.py
python3 facilitator/generator/generate_vendor_doc.py
git status --short data/source data/target data/documents
```

Empty output means the committed data matches the generator exactly.

The PDF is reproducible only because `CREATION_DATE` is pinned in `generate_vendor_doc.py` —
fpdf otherwise stamps `datetime.now()` into `/CreationDate`, which made an unchanged
regeneration show up as a modified file.

**`data/ci_fund_data.zip` is the one exception.** The zip format records file modification times
in each entry, so rebuilding it always produces different bytes even when every file inside is
identical. Its *contents* are reproducible; the container is not. Rebuild it after regenerating:

```bash
cd data && rm -f ci_fund_data.zip && zip -qr ci_fund_data.zip source target documents
```

The zip is only a convenience bundle for attendees who want the data locally — nothing in the
lab loads from it, so a stale zip is a cosmetic problem rather than a correctness one.

## If you change the rules

Three places have to stay in step, and nothing enforces it automatically:

1. `generate_data.py` — the rule itself, in `build_target()`, and its naive counterpart in
   `_recompute()`.
2. `facilitator/SOLUTION.md` — the rule's description, proving SQL, and expected residual.
3. `scripts/checkpoints/after_session_02.sql` — the SQL implementation attendees fall back to.

Point 3 is the easiest to forget and the most damaging to miss: the checkpoint would silently
stop reconciling, and you would not find out until someone used it mid-session.

The vendor PDF in `generate_vendor_doc.py` also states seven claims, five of which contradict the
data on purpose. If you change a rule, check whether the corresponding claim still contradicts
it — the docstring lists which claim maps to which rule.
