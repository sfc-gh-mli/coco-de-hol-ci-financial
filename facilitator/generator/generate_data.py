#!/usr/bin/env python3
"""Generate the CI Financial fund performance dataset for the Cortex Code DE HOL.

SPOILER WARNING
---------------
This script IS the answer key. It generates the vendor target table by applying the
seven undocumented methodology rules that attendees are asked to reverse-engineer in
Session 2. Do not share this file (or anything else under facilitator/) with attendees
before the session.

Usage
-----
    python3 generate_data.py              # write CSVs to ../../data/
    python3 generate_data.py --verify     # regenerate, then assert the puzzle is solvable

The --verify mode is the important one. It implements the *naive* version of each rule
and asserts that:
  * each naive hypothesis leaves a residual large enough to notice but small enough to
    look like a rounding problem at first glance,
  * each residual is strongly correlated with the driver an attendee would spot,
  * applying rules 1-4 in order monotonically shrinks the residual, and
  * applying all seven reproduces the target to < 0.01 bps on 71 of 72 rows.

If a signature is undetectable, tune the volatility and flow magnitudes below --- not
the rules themselves.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260918
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Calendar. We deliberately start in late December 2024 so that:
#   * January has a prior-month ending NAV to use as its beginning NAV, and
#   * the T-1 FX rule has a prior business day available for the first 2025 date.
# An attendee who inner-joins FX on the same date silently loses the first day.
CAL_START = "2024-12-24"
CAL_END = "2025-12-31"
YEAR = 2025

TRADING_DAYS_PER_YEAR = 252

# The alternative fund's performance fee crystallises in December on YTD net return above
# this hurdle (0% = a simple positive-return fee, common for alt mandates). It exists to
# create exactly one row that no global formula reconciles.
PERF_FEE_HURDLE = 0.0

# --------------------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------------------

FUNDS = [
    # code,               name,                                asset_class,     ccy,  mgmt, admin, perf, benchmark,  init_nav
    ("CIF-CAD-EQ-01", "CI Canadian Core Equity Fund", "Canadian Equity", "CAD", 185, 22, 0.00, "BM-CAD-EQ", 412_500_000),
    ("CIF-GLB-EQ-02", "CI Global Equity Growth Fund", "Global Equity", "CAD", 235, 28, 0.00, "BM-GLB-EQ", 268_000_000),
    ("CIF-BAL-60-03", "CI Balanced 60/40 Portfolio", "Balanced", "CAD", 205, 25, 0.00, "BM-BLEND-6040", 735_000_000),
    ("CIF-FIX-IN-04", "CI Canadian Fixed Income Fund", "Fixed Income", "CAD", 115, 18, 0.00, "BM-CAD-FI", 521_000_000),
    ("CIF-USD-EQ-05", "CI US Large Cap Fund", "US Equity", "CAD", 215, 26, 0.00, "BM-US-EQ", 344_000_000),
    # The only fund with a performance fee. Crystallizes in December --- this is the
    # deliberate outlier that stops any single global formula from reconciling all 72 rows.
    ("CIF-ALT-LS-06", "CI Alternative Long/Short Fund", "Alternative", "CAD", 175, 35, 0.15, "BM-CAD-EQ", 96_500_000),
]

BENCHMARKS = [
    ("BM-CAD-EQ", "S&P/TSX Composite Total Return", "N"),
    ("BM-GLB-EQ", "MSCI World Total Return (CAD)", "N"),
    ("BM-CAD-FI", "FTSE Canada Universe Bond", "N"),
    ("BM-US-EQ", "S&P 500 Total Return (CAD)", "N"),
    ("BM-BLEND-6040", "60/40 Canadian Balanced Blend", "Y"),
]

# The blend is the interesting one: two components, rebalanced monthly.
BENCHMARK_COMPONENTS = [
    ("BM-CAD-EQ", "IDX-TSX", 1.00, "N/A"),
    ("BM-GLB-EQ", "IDX-MSCIW", 1.00, "N/A"),
    ("BM-CAD-FI", "IDX-FTSEBOND", 1.00, "N/A"),
    ("BM-US-EQ", "IDX-SP500", 1.00, "N/A"),
    ("BM-BLEND-6040", "IDX-TSX", 0.60, "MONTHLY"),
    ("BM-BLEND-6040", "IDX-FTSEBOND", 0.40, "MONTHLY"),
]

# index code, annual drift, annual vol
INDICES = [
    ("IDX-TSX", 0.082, 0.132),
    ("IDX-MSCIW", 0.095, 0.148),
    ("IDX-FTSEBOND", 0.034, 0.052),
    ("IDX-SP500", 0.104, 0.162),
]

SECTORS = [
    "Financials", "Energy", "Materials", "Industrials", "Technology",
    "Health Care", "Consumer Staples", "Consumer Discretionary",
    "Utilities", "Communication Services", "Real Estate", "Government",
]

# Each fund draws its holdings from a currency mix. Foreign-currency weight is what
# makes the T-1 FX rule (rule 1) visible, so the global/US funds carry most of it.
FUND_CCY_MIX = {
    "CIF-CAD-EQ-01": {"CAD": 0.92, "USD": 0.08, "EUR": 0.00},
    "CIF-GLB-EQ-02": {"CAD": 0.18, "USD": 0.52, "EUR": 0.30},
    "CIF-BAL-60-03": {"CAD": 0.74, "USD": 0.19, "EUR": 0.07},
    "CIF-FIX-IN-04": {"CAD": 0.96, "USD": 0.04, "EUR": 0.00},
    "CIF-USD-EQ-05": {"CAD": 0.05, "USD": 0.95, "EUR": 0.00},
    "CIF-ALT-LS-06": {"CAD": 0.55, "USD": 0.34, "EUR": 0.11},
}

N_SECURITIES = 60
HOLDINGS_PER_FUND = 20
N_INVESTOR_ACCOUNTS = 420

# Investor account data. This exists for the AI Functions session: CI must be able to prove
# that nothing it sends Meridian carries investor PII. KYC_NOTES is deliberately messy free
# text --- some rows are clean, some carry names, phone numbers, emails, or SIN fragments
# buried mid-sentence, which is exactly the shape AI_CLASSIFY and AI_REDACT are for.
FIRST_NAMES = [
    "Amrita", "Benoit", "Chen", "Dmitri", "Eleanor", "Farah", "Gordon", "Hyun",
    "Isabelle", "Jaswinder", "Katarzyna", "Liam", "Mariana", "Nkechi", "Oliver",
    "Priya", "Quentin", "Rosalie", "Sunil", "Tobias", "Uma", "Viktor", "Wenjun", "Yasmin",
]
LAST_NAMES = [
    "Bhattacharya", "Tremblay", "Okonkwo", "MacLeod", "Petrov", "Nakamura", "Silva",
    "Kowalski", "Dubois", "Ferreira", "Singh", "O'Brien", "Larsen", "Haddad",
    "Rossi", "Vandenberg", "Choi", "Mensah", "Novak", "Castellanos",
]
ADVISORS = [
    "R. Whitfield", "M. Delacroix", "T. Ferraro", "A. Osei", "J. Lindqvist", "S. Rahman",
]
CITIES = [
    ("Toronto", "ON"), ("Mississauga", "ON"), ("Calgary", "AB"), ("Vancouver", "BC"),
    ("Montreal", "QC"), ("Halifax", "NS"), ("Winnipeg", "MB"), ("Ottawa", "ON"),
]


# --------------------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------------------

def business_days() -> pd.DatetimeIndex:
    return pd.bdate_range(CAL_START, CAL_END)


def make_securities(rng) -> pd.DataFrame:
    rows = []
    for i in range(N_SECURITIES):
        ccy = ["CAD", "USD", "EUR"][i % 3] if i < 45 else rng.choice(["CAD", "USD", "EUR"])
        asset_type = "BOND" if i >= 48 else "EQUITY"
        rows.append({
            "SECURITY_ID": 10_001 + i,
            "TICKER": f"{'BND' if asset_type == 'BOND' else 'EQ'}{i + 1:03d}.{ccy}",
            "SECURITY_NAME": f"{'Bond Series' if asset_type == 'BOND' else 'Equity Holding'} {i + 1:03d}",
            "SECTOR": "Government" if asset_type == "BOND" else SECTORS[i % 11],
            "CURRENCY": ccy,
            "ASSET_TYPE": asset_type,
        })
    return pd.DataFrame(rows)


def make_prices(rng, dates, securities) -> pd.DataFrame:
    frames = []
    for _, sec in securities.iterrows():
        is_bond = sec["ASSET_TYPE"] == "BOND"
        vol = rng.uniform(0.04, 0.07) if is_bond else rng.uniform(0.15, 0.30)
        drift = rng.uniform(0.02, 0.05) if is_bond else rng.uniform(0.03, 0.14)
        p0 = rng.uniform(95, 105) if is_bond else rng.uniform(18, 240)
        n = len(dates)
        dt = 1.0 / TRADING_DAYS_PER_YEAR
        shocks = rng.normal((drift - 0.5 * vol ** 2) * dt, vol * np.sqrt(dt), n)
        path = p0 * np.exp(np.cumsum(shocks))
        frames.append(pd.DataFrame({
            "SECURITY_ID": sec["SECURITY_ID"],
            "PRICE_DATE": dates,
            "CLOSE_PRICE_LOCAL": np.round(path, 4),
            "CURRENCY": sec["CURRENCY"],
        }))
    return pd.concat(frames, ignore_index=True)


def make_fx(rng, dates) -> pd.DataFrame:
    """USD->CAD and EUR->CAD daily rates.

    Daily vol is tuned so a one-day FX move is ~0.35%. Combined with foreign-currency
    weights of 30-95%, that makes the T-1 FX convention (rule 1) show up in ending NAV
    at roughly 10-30 bps --- noticeable, but easy to mistake for rounding.
    """
    rows = []
    for pair, start, daily_vol in (("USD", 1.3520, 0.0035), ("EUR", 1.4630, 0.0038)):
        shocks = rng.normal(0.0, daily_vol, len(dates))
        path = start * np.exp(np.cumsum(shocks))
        for d, r in zip(dates, path):
            rows.append({
                "RATE_DATE": d,
                "FROM_CURRENCY": pair,
                "TO_CURRENCY": "CAD",
                "RATE": round(float(r), 6),
            })
    # CAD->CAD identity, so an attendee can join uniformly without special-casing.
    for d in dates:
        rows.append({"RATE_DATE": d, "FROM_CURRENCY": "CAD", "TO_CURRENCY": "CAD", "RATE": 1.0})
    return pd.DataFrame(rows)


def make_index_returns(rng, dates) -> pd.DataFrame:
    rows = []
    for code, drift, vol in INDICES:
        dt = 1.0 / TRADING_DAYS_PER_YEAR
        r = rng.normal(drift * dt, vol * np.sqrt(dt), len(dates))
        for d, x in zip(dates, r):
            rows.append({
                "INDEX_CODE": code,
                "RETURN_DATE": d,
                "TOTAL_RETURN_PCT": round(float(x) * 100, 8),
            })
    return pd.DataFrame(rows)


def assign_holdings(rng, securities) -> dict:
    """Pick which securities each fund holds, honouring its currency mix."""
    by_ccy = {c: securities[securities["CURRENCY"] == c]["SECURITY_ID"].tolist()
              for c in ("CAD", "USD", "EUR")}
    out = {}
    for code, *_ in FUNDS:
        mix = FUND_CCY_MIX[code]
        picks, weights = [], []
        for ccy, target_w in mix.items():
            if target_w <= 0:
                continue
            n = max(1, int(round(HOLDINGS_PER_FUND * target_w)))
            chosen = rng.choice(by_ccy[ccy], size=min(n, len(by_ccy[ccy])), replace=False)
            raw = rng.uniform(0.6, 1.4, len(chosen))
            raw = raw / raw.sum() * target_w
            picks.extend(int(s) for s in chosen)
            weights.extend(raw.tolist())
        w = np.array(weights)
        out[code] = (picks, w / w.sum())
    return out


def make_cash_flows(rng, fund_code, dates_2025) -> pd.DataFrame:
    """Subscriptions/redemptions clustered mid-month, plus quarterly distributions for two funds.

    Flows land on days 8-22 of the month on purpose. Modified Dietz weights a flow by the
    fraction of the month remaining, so a mid-month flow is exactly where Modified Dietz and
    naive daily chaining diverge most (rule 3).
    """
    rows = []
    months = sorted({(d.year, d.month) for d in dates_2025})
    # 5 subscription/redemption events per fund per year: leaves ~5 of 12 months with a
    # flow, so "the residual is zero except in months with flows" is a clean signature.
    flow_months = rng.choice(len(months), size=5, replace=False)
    for mi in flow_months:
        y, m = months[mi]
        candidates = [d for d in dates_2025 if d.year == y and d.month == m and 8 <= d.day <= 22]
        if not candidates:
            continue
        d = candidates[rng.integers(0, len(candidates))]
        is_sub = rng.random() < 0.6
        rows.append({
            "FUND_CODE": fund_code,
            "FLOW_DATE": d,
            "FLOW_TYPE": "SUBSCRIPTION" if is_sub else "REDEMPTION",
            "AMOUNT_CAD": None,
            "_pct": float(rng.uniform(0.035, 0.115)),
        })
    if fund_code in ("CIF-BAL-60-03", "CIF-FIX-IN-04"):
        for m in (3, 6, 9, 12):
            candidates = [d for d in dates_2025 if d.month == m]
            if not candidates:
                continue
            d = candidates[-1]  # paid on the last business day of the quarter
            rows.append({
                "FUND_CODE": fund_code,
                "FLOW_DATE": d,
                "FLOW_TYPE": "DISTRIBUTION",
                "AMOUNT_CAD": None,
                "_pct": float(rng.uniform(0.006, 0.013)),
            })
    return pd.DataFrame(rows)


def simulate_fund(rng, fund, dates, price_lookup, fx_lookup, holdings_map):
    """Walk a fund forward day by day, producing holdings, daily NAV, and realised flows.

    RULE 1 lives here: NAV on date t values foreign holdings at the *prior* business day's
    FX rate. Everything downstream inherits it.
    """
    code, name, asset_class, ccy, mgmt, admin, perf, bm, init_nav = fund
    sec_ids, weights = holdings_map[code]

    dates_2025 = [d for d in dates if d.year == YEAR]
    planned = make_cash_flows(rng, code, dates_2025)
    planned_by_date = {}
    for _, r in planned.iterrows():
        planned_by_date.setdefault(r["FLOW_DATE"], []).append(r)

    # Seed quantities on the first calendar date using that date's own FX (day 0 has no prior).
    d0 = dates[0]
    qty = {}
    for sid, w in zip(sec_ids, weights):
        px, sec_ccy = price_lookup[(sid, d0)]
        fx = fx_lookup[(sec_ccy, d0)]
        qty[sid] = (init_nav * w) / (px * fx)

    holdings_rows, nav_rows, flow_rows = [], [], []

    def nav_on(date, prior_date):
        """Value holdings at date's prices and prior_date's FX. This is rule 1."""
        total = 0.0
        for sid, q in qty.items():
            px, sec_ccy = price_lookup[(sid, date)]
            fx = fx_lookup[(sec_ccy, prior_date)]
            total += q * px * fx
        return total

    for i, d in enumerate(dates):
        prior = dates[i - 1] if i > 0 else d
        nav_pre = nav_on(d, prior)

        for r in planned_by_date.get(d, []):
            amount = round(nav_pre * r["_pct"], 2)
            if r["FLOW_TYPE"] == "SUBSCRIPTION":
                scale = 1.0 + amount / nav_pre
            else:  # REDEMPTION and DISTRIBUTION both take cash out of the fund
                scale = 1.0 - amount / nav_pre
            for sid in qty:
                qty[sid] *= scale
            flow_rows.append({
                "FUND_CODE": code,
                "FLOW_DATE": d,
                "FLOW_TYPE": r["FLOW_TYPE"],
                "AMOUNT_CAD": amount,
            })

        nav = nav_on(d, prior)
        nav_rows.append({"FUND_CODE": code, "AS_OF_DATE": d, "NAV_CAD": nav})
        for sid, q in qty.items():
            holdings_rows.append({
                "FUND_CODE": code,
                "AS_OF_DATE": d,
                "SECURITY_ID": sid,
                "QUANTITY": round(q, 6),
            })

    return (pd.DataFrame(holdings_rows), pd.DataFrame(nav_rows), pd.DataFrame(flow_rows))


def make_expenses(rng, nav_df, fund) -> pd.DataFrame:
    """Daily fee accruals computed on that day's NAV.

    Because accruals are daily on a 252-day basis, the *sum* of a month's accruals divided
    by average daily NAV comes out near annual_rate * business_days / 252 --- which differs
    from a naive annual_rate / 12. That difference is rule 4, and it correlates almost
    perfectly with the number of business days in the month.
    """
    code, name, asset_class, ccy, mgmt, admin, perf, bm, init_nav = fund
    other_bps = rng.uniform(14, 31)
    rows = []
    for _, r in nav_df.iterrows():
        nav = r["NAV_CAD"]
        rows.append({
            "FUND_CODE": code,
            "ACCRUAL_DATE": r["AS_OF_DATE"],
            "MGMT_FEE_ACCRUED": round(nav * (mgmt / 10_000) / TRADING_DAYS_PER_YEAR, 2),
            "ADMIN_FEE_ACCRUED": round(nav * (admin / 10_000) / TRADING_DAYS_PER_YEAR, 2),
            "OTHER_EXPENSE": round(nav * (other_bps / 10_000) / TRADING_DAYS_PER_YEAR
                                   * float(rng.uniform(0.85, 1.15)), 2),
        })
    return pd.DataFrame(rows)


def monthly_index_returns(index_returns: pd.DataFrame) -> pd.DataFrame:
    """Compound daily index returns within each month."""
    df = index_returns.copy()
    df["PERIOD"] = df["RETURN_DATE"].dt.to_period("M")
    df["GROWTH"] = 1.0 + df["TOTAL_RETURN_PCT"] / 100.0
    out = df.groupby(["INDEX_CODE", "PERIOD"])["GROWTH"].prod().reset_index()
    out["MONTHLY_RETURN"] = out["GROWTH"] - 1.0
    return out


def benchmark_monthly(index_monthly: pd.DataFrame) -> dict:
    """RULE 6: the blend is a monthly-rebalanced *arithmetic* weighted average of each
    component's compounded monthly return --- not a chained daily blend, and not a
    buy-and-hold blend whose weights drift."""
    comp = pd.DataFrame(BENCHMARK_COMPONENTS,
                        columns=["BENCHMARK_ID", "INDEX_CODE", "WEIGHT", "REBALANCE_FREQUENCY"])
    merged = comp.merge(index_monthly, on="INDEX_CODE")
    merged["WEIGHTED"] = merged["WEIGHT"] * merged["MONTHLY_RETURN"]
    agg = merged.groupby(["BENCHMARK_ID", "PERIOD"])["WEIGHTED"].sum().reset_index()
    return {(r["BENCHMARK_ID"], r["PERIOD"]): r["WEIGHTED"] for _, r in agg.iterrows()}


def build_target(nav_all, flows_all, expenses_all, bm_monthly) -> pd.DataFrame:
    """Apply all seven rules to produce the vendor's monthly performance table."""
    rows = []
    for fund in FUNDS:
        code, name, asset_class, ccy, mgmt, admin, perf, bm, init_nav = fund
        nav = nav_all[nav_all["FUND_CODE"] == code].sort_values("AS_OF_DATE").reset_index(drop=True)
        flows = flows_all[flows_all["FUND_CODE"] == code]
        exp = expenses_all[expenses_all["FUND_CODE"] == code]

        nav["PERIOD"] = nav["AS_OF_DATE"].dt.to_period("M")
        ytd_growth = 1.0
        ytd_bench_growth = 1.0

        for period in sorted(p for p in nav["PERIOD"].unique() if p.year == YEAR):
            month_nav = nav[nav["PERIOD"] == period]
            first_idx = month_nav.index[0]
            beginning_nav = float(nav.loc[first_idx - 1, "NAV_CAD"])
            ending_nav = float(month_nav.iloc[-1]["NAV_CAD"])

            days_in_month = len(month_nav)
            avg_daily_nav = float(month_nav["NAV_CAD"].mean())
            last_day = int(month_nav.iloc[-1]["AS_OF_DATE"].day)

            mf = flows[flows["FLOW_DATE"].dt.to_period("M") == period]
            subs = float(mf[mf["FLOW_TYPE"] == "SUBSCRIPTION"]["AMOUNT_CAD"].sum())
            reds = float(mf[mf["FLOW_TYPE"] == "REDEMPTION"]["AMOUNT_CAD"].sum())
            dists = float(mf[mf["FLOW_TYPE"] == "DISTRIBUTION"]["AMOUNT_CAD"].sum())

            # RULE 2: distributions are treated as reinvested, so they are added back to
            # ending NAV. The trap: the reported NET_FLOWS column is subs - reds, so an
            # attendee who reproduces NET_FLOWS correctly and then uses it as the flow term
            # drops the distribution from the numerator entirely and understates the return
            # by the full distribution yield.
            net_flows = subs - reds
            emv_adj = ending_nav + dists

            # RULE 3: Modified Dietz. Each flow is weighted by the fraction of the month
            # remaining after it lands.
            weighted_flow = 0.0
            for _, f in mf.iterrows():
                if f["FLOW_TYPE"] == "DISTRIBUTION":
                    continue
                signed = f["AMOUNT_CAD"] if f["FLOW_TYPE"] == "SUBSCRIPTION" else -f["AMOUNT_CAD"]
                day = int(f["FLOW_DATE"].day)
                weighted_flow += signed * (last_day - day) / last_day

            denom = beginning_nav + weighted_flow
            gross_return = (emv_adj - beginning_nav - net_flows) / denom

            # RULE 4: fees come off as total accrued fees over AVERAGE DAILY NAV.
            # RULE 5: OTHER_EXPENSE is excluded here but included in EXPENSE_RATIO_PCT below.
            me = exp[exp["ACCRUAL_DATE"].dt.to_period("M") == period]
            fee_accrued = float(me["MGMT_FEE_ACCRUED"].sum() + me["ADMIN_FEE_ACCRUED"].sum())
            other_accrued = float(me["OTHER_EXPENSE"].sum())
            fee_drag = fee_accrued / avg_daily_nav

            net_return = gross_return - fee_drag

            bench_return = float(bm_monthly[(bm, period)])

            # The December performance-fee crystallisation. This is the deliberate outlier:
            # one row that no single global formula reconciles.
            perf_fee_drag = 0.0
            if perf > 0 and period.month == 12:
                ytd_net_before = ytd_growth * (1.0 + net_return) - 1.0
                if ytd_net_before > PERF_FEE_HURDLE:
                    perf_fee_drag = perf * (ytd_net_before - PERF_FEE_HURDLE)
                    net_return -= perf_fee_drag

            # RULE 7: excess return is geometric, not arithmetic.
            excess_return = (1.0 + net_return) / (1.0 + bench_return) - 1.0

            expense_ratio = ((fee_accrued + other_accrued) / avg_daily_nav) * (
                TRADING_DAYS_PER_YEAR / days_in_month)

            ytd_growth *= (1.0 + net_return)
            ytd_bench_growth *= (1.0 + bench_return)

            rows.append({
                "FUND_CODE": code,
                "PERIOD_END_DATE": month_nav.iloc[-1]["AS_OF_DATE"],
                "BEGINNING_NAV": round(beginning_nav, 2),
                "ENDING_NAV": round(ending_nav, 2),
                "NET_FLOWS": round(net_flows, 2),
                "GROSS_RETURN_PCT": round(gross_return * 100, 6),
                "NET_RETURN_PCT": round(net_return * 100, 6),
                "BENCHMARK_RETURN_PCT": round(bench_return * 100, 6),
                "EXCESS_RETURN_PCT": round(excess_return * 100, 6),
                "EXPENSE_RATIO_PCT": round(expense_ratio * 100, 6),
                "YTD_NET_RETURN_PCT": round((ytd_growth - 1.0) * 100, 6),
            })
    return pd.DataFrame(rows)


def make_investor_accounts(rng, nav_all) -> pd.DataFrame:
    """Retail investor accounts with free-text KYC notes.

    Roughly 45% of the notes carry some form of personal identifier embedded in prose.
    The rest are clean. That mix matters: a lab where every row is PII teaches nothing about
    classification, because 'flag everything' scores perfectly.
    """
    clean_templates = [
        "Risk tolerance reviewed at annual check-in. No change to mandate.",
        "Client confirmed long-term horizon; rebalancing deferred to next quarter.",
        "KYC refresh completed. Suitability unchanged since prior review.",
        "Account flagged for systematic withdrawal plan review in Q3.",
        "Investment objective remains growth with moderate volatility tolerance.",
        "Spousal contribution limits discussed; no action required this period.",
        "Client declined leverage strategy. Documented in advisor file.",
        "Periodic review complete. Holdings consistent with stated objectives.",
    ]
    # Each template leaves a slot for an identifier so the PII sits mid-sentence rather than
    # in a tidy column --- a regex pass will miss most of these.
    pii_templates = [
        "Spoke with {name} on the phone at {phone} to confirm the rebalance instruction.",
        "Client asked that statements go to {email} instead of the address on file.",
        "{name} requested a call back; best reached at {phone} after 4pm ET.",
        "Verified identity against SIN ending {sin} before processing the transfer.",
        "Beneficiary updated to {name}, spouse, following marriage. Docs on file.",
        "Follow-up email sent to {email} summarising the fee discussion.",
        "{name} confirmed new mailing address at {street}, apartment access via buzzer.",
        "Joint account holder {name} co-signed; reached at {phone} for confirmation.",
    ]
    fund_codes = [f[0] for f in FUNDS]
    rows = []
    for i in range(N_INVESTOR_ACCOUNTS):
        first = FIRST_NAMES[int(rng.integers(0, len(FIRST_NAMES)))]
        last = LAST_NAMES[int(rng.integers(0, len(LAST_NAMES)))]
        name = f"{first} {last}"
        city, prov = CITIES[int(rng.integers(0, len(CITIES)))]
        email = f"{first.lower()}.{last.lower().replace(chr(39), '')}@example-mail.ca"
        phone = f"({int(rng.integers(204, 905))}) {int(rng.integers(200, 999))}-{int(rng.integers(1000, 9999))}"
        sin = f"{int(rng.integers(100, 999))}"
        street = f"{int(rng.integers(12, 4800))} {rng.choice(['Bay', 'King', 'Queen', 'Yonge', 'Dundas'])} St"

        if rng.random() < 0.45:
            note = pii_templates[int(rng.integers(0, len(pii_templates)))].format(
                name=name, phone=phone, email=email, sin=sin, street=street)
        else:
            note = clean_templates[int(rng.integers(0, len(clean_templates)))]

        fund_code = fund_codes[int(rng.integers(0, len(fund_codes)))]
        rows.append({
            "ACCOUNT_ID": f"ACCT-{100_000 + i}",
            "FUND_CODE": fund_code,
            "INVESTOR_NAME": name,
            "EMAIL": email,
            "PHONE": phone,
            "CITY": city,
            "PROVINCE": prov,
            "ADVISOR_NAME": ADVISORS[int(rng.integers(0, len(ADVISORS)))],
            "UNITS_HELD": round(float(rng.uniform(120, 48_000)), 4),
            "ACCOUNT_OPEN_DATE": pd.Timestamp("2016-01-04")
            + pd.Timedelta(days=int(rng.integers(0, 3200))),
            "KYC_NOTES": note,
        })
    return pd.DataFrame(rows)


def naive_nav_series(holdings, prices, fx) -> pd.DataFrame:
    """NAV valued at the SAME day's FX --- the naive alternative to rule 1.

    Used by --verify to show what an attendee gets before discovering the T-1 convention.
    """
    px = prices.rename(columns={"PRICE_DATE": "AS_OF_DATE"})
    m = holdings.merge(px, on=["SECURITY_ID", "AS_OF_DATE"])
    fx_same = fx.rename(columns={"RATE_DATE": "AS_OF_DATE", "FROM_CURRENCY": "CURRENCY"})
    m = m.merge(fx_same[["AS_OF_DATE", "CURRENCY", "RATE"]], on=["AS_OF_DATE", "CURRENCY"])
    m["MV"] = m["QUANTITY"] * m["CLOSE_PRICE_LOCAL"] * m["RATE"]
    out = m.groupby(["FUND_CODE", "AS_OF_DATE"])["MV"].sum().reset_index()
    return out.rename(columns={"MV": "NAV_CAD"})


def generate():
    rng = np.random.default_rng(SEED)
    dates = business_days()

    securities = make_securities(rng)
    prices = make_prices(rng, dates, securities)
    fx = make_fx(rng, dates)
    index_returns = make_index_returns(rng, dates)

    price_lookup = {(r.SECURITY_ID, r.PRICE_DATE): (r.CLOSE_PRICE_LOCAL, r.CURRENCY)
                    for r in prices.itertuples()}
    fx_lookup = {(r.FROM_CURRENCY, r.RATE_DATE): r.RATE for r in fx.itertuples()}

    holdings_map = assign_holdings(rng, securities)

    holdings_frames, nav_frames, flow_frames, expense_frames = [], [], [], []
    for fund in FUNDS:
        h, n, f = simulate_fund(rng, fund, dates, price_lookup, fx_lookup, holdings_map)
        holdings_frames.append(h)
        nav_frames.append(n)
        flow_frames.append(f)
        expense_frames.append(make_expenses(rng, n, fund))

    holdings = pd.concat(holdings_frames, ignore_index=True)
    nav_all = pd.concat(nav_frames, ignore_index=True)
    flows = pd.concat(flow_frames, ignore_index=True).sort_values(["FUND_CODE", "FLOW_DATE"])
    expenses = pd.concat(expense_frames, ignore_index=True)

    idx_monthly = monthly_index_returns(index_returns)
    bm_monthly = benchmark_monthly(idx_monthly)

    target = build_target(nav_all, flows, expenses, bm_monthly)

    fund_master = pd.DataFrame([{
        "FUND_CODE": c, "FUND_NAME": n, "ASSET_CLASS": a, "BASE_CURRENCY": cc,
        "MGMT_FEE_BPS": m, "ADMIN_FEE_BPS": ad, "PERF_FEE_RATE": p,
        "BENCHMARK_ID": b, "INCEPTION_DATE": pd.Timestamp("2019-01-02"),
    } for c, n, a, cc, m, ad, p, b, _ in FUNDS])

    benchmark_master = pd.DataFrame(BENCHMARKS,
                                    columns=["BENCHMARK_ID", "BENCHMARK_NAME", "IS_BLEND"])
    benchmark_components = pd.DataFrame(
        BENCHMARK_COMPONENTS,
        columns=["BENCHMARK_ID", "INDEX_CODE", "WEIGHT", "REBALANCE_FREQUENCY"])

    return {
        "source": {
            "FUND_MASTER": fund_master,
            "BENCHMARK_MASTER": benchmark_master,
            "BENCHMARK_COMPONENTS": benchmark_components,
            "SECURITY_MASTER": securities,
            "HOLDINGS_DAILY": holdings,
            "PRICES_DAILY": prices,
            "FX_RATES_DAILY": fx,
            "CASH_FLOWS": flows,
            "FUND_EXPENSES_DAILY": expenses,
            "INDEX_RETURNS_DAILY": index_returns,
            "INVESTOR_ACCOUNTS": make_investor_accounts(rng, nav_all),
        },
        "target": {"VENDOR_FUND_PERFORMANCE_MONTHLY": target},
        "_internal": {"nav": nav_all, "bm_monthly": bm_monthly, "idx_monthly": idx_monthly,
                      "dates": dates, "fx": fx, "prices": prices,
                      "nav_naive": naive_nav_series(holdings, prices, fx)},
    }


def write_csvs(bundle):
    src = OUT_DIR / "source"
    tgt = OUT_DIR / "target"
    src.mkdir(parents=True, exist_ok=True)
    tgt.mkdir(parents=True, exist_ok=True)
    for name, df in bundle["source"].items():
        df.to_csv(src / f"{name.lower()}.csv", index=False, date_format="%Y-%m-%d")
    for name, df in bundle["target"].items():
        df.to_csv(tgt / f"{name.lower()}.csv", index=False, date_format="%Y-%m-%d")
    total = sum(len(d) for d in bundle["source"].values())
    print(f"wrote {len(bundle['source'])} source tables ({total:,} rows) to {src}")
    for name, df in bundle["target"].items():
        print(f"wrote target {name} ({len(df)} rows) to {tgt}")


# --------------------------------------------------------------------------------------
# Verification --- is the puzzle actually solvable?
# --------------------------------------------------------------------------------------

def _naive_ending_nav(bundle):
    """Rule 1 naive: value foreign holdings at the SAME day's FX instead of T-1."""
    holdings = bundle["source"]["HOLDINGS_DAILY"]
    prices = bundle["source"]["PRICES_DAILY"]
    fx = bundle["source"]["FX_RATES_DAILY"]
    target = bundle["target"]["VENDOR_FUND_PERFORMANCE_MONTHLY"]

    px = prices.rename(columns={"PRICE_DATE": "AS_OF_DATE"})
    m = holdings.merge(px, on=["SECURITY_ID", "AS_OF_DATE"])
    fx_same = fx.rename(columns={"RATE_DATE": "AS_OF_DATE", "FROM_CURRENCY": "CURRENCY"})
    m = m.merge(fx_same[["AS_OF_DATE", "CURRENCY", "RATE"]], on=["AS_OF_DATE", "CURRENCY"])
    m["MV"] = m["QUANTITY"] * m["CLOSE_PRICE_LOCAL"] * m["RATE"]
    nav = m.groupby(["FUND_CODE", "AS_OF_DATE"])["MV"].sum().reset_index()

    eom = target[["FUND_CODE", "PERIOD_END_DATE", "ENDING_NAV"]].rename(
        columns={"PERIOD_END_DATE": "AS_OF_DATE"})
    j = eom.merge(nav, on=["FUND_CODE", "AS_OF_DATE"])
    j["RESID_BPS"] = (j["MV"] / j["ENDING_NAV"] - 1.0) * 10_000
    return j


def _fx_change(bundle):
    fx = bundle["source"]["FX_RATES_DAILY"]
    usd = fx[fx["FROM_CURRENCY"] == "USD"].sort_values("RATE_DATE").reset_index(drop=True)
    usd["FX_CHG_BPS"] = usd["RATE"].pct_change() * 10_000
    return usd[["RATE_DATE", "FX_CHG_BPS"]].rename(columns={"RATE_DATE": "AS_OF_DATE"})


def _recompute(bundle, rules):
    """Recompute the target with a chosen subset of rules applied.

    rules is a set drawn from {1,2,3,4,5,6,7}. Omitting a rule uses the naive alternative
    an attendee would reach for first. Rule 1 is handled by the caller because it changes
    the NAV series itself.
    """
    nav_all = bundle["_internal"]["nav"] if 1 in rules else bundle["_internal"]["nav_naive"]
    flows = bundle["source"]["CASH_FLOWS"]
    expenses = bundle["source"]["FUND_EXPENSES_DAILY"]
    idx_monthly = bundle["_internal"]["idx_monthly"]
    index_returns = bundle["source"]["INDEX_RETURNS_DAILY"]

    if 6 in rules:
        bm = benchmark_monthly(idx_monthly)
    else:
        # Naive: blend the daily component returns, then chain the blended daily series.
        comp = pd.DataFrame(BENCHMARK_COMPONENTS,
                            columns=["BENCHMARK_ID", "INDEX_CODE", "WEIGHT", "REBALANCE_FREQUENCY"])
        d = comp.merge(index_returns, on="INDEX_CODE")
        d["W_RET"] = d["WEIGHT"] * d["TOTAL_RETURN_PCT"] / 100.0
        daily = d.groupby(["BENCHMARK_ID", "RETURN_DATE"])["W_RET"].sum().reset_index()
        daily["PERIOD"] = daily["RETURN_DATE"].dt.to_period("M")
        daily["G"] = 1.0 + daily["W_RET"]
        agg = daily.groupby(["BENCHMARK_ID", "PERIOD"])["G"].prod().reset_index()
        bm = {(r["BENCHMARK_ID"], r["PERIOD"]): r["G"] - 1.0 for _, r in agg.iterrows()}

    rows = []
    for fund in FUNDS:
        code, name, ac, ccy, mgmt, admin, perf, bmid, init_nav = fund
        nav = nav_all[nav_all["FUND_CODE"] == code].sort_values("AS_OF_DATE").reset_index(drop=True)
        nav["PERIOD"] = nav["AS_OF_DATE"].dt.to_period("M")
        f = flows[flows["FUND_CODE"] == code]
        e = expenses[expenses["FUND_CODE"] == code]

        for period in sorted(p for p in nav["PERIOD"].unique() if p.year == YEAR):
            mn = nav[nav["PERIOD"] == period]
            i0 = mn.index[0]
            bnav = float(nav.loc[i0 - 1, "NAV_CAD"])
            enav = float(mn.iloc[-1]["NAV_CAD"])
            days = len(mn)
            avg_nav = float(mn["NAV_CAD"].mean())
            last_day = int(mn.iloc[-1]["AS_OF_DATE"].day)

            mf = f[f["FLOW_DATE"].dt.to_period("M") == period]
            subs = float(mf[mf["FLOW_TYPE"] == "SUBSCRIPTION"]["AMOUNT_CAD"].sum())
            reds = float(mf[mf["FLOW_TYPE"] == "REDEMPTION"]["AMOUNT_CAD"].sum())
            dists = float(mf[mf["FLOW_TYPE"] == "DISTRIBUTION"]["AMOUNT_CAD"].sum())

            if 2 in rules:
                net_flows, emv = subs - reds, enav + dists
            else:
                # Naive: distributions are ignored. This is what happens when you match the
                # reported NET_FLOWS column (subs - reds) and never notice the DISTRIBUTION
                # rows in CASH_FLOWS. Note that subtracting them as an outflow *and* adding
                # them to ending NAV is algebraically identical to the correct treatment ---
                # the only way to get this wrong is to drop them.
                net_flows, emv = subs - reds, enav

            if 3 in rules:
                wf = 0.0
                for _, r in mf.iterrows():
                    if r["FLOW_TYPE"] == "DISTRIBUTION" and 2 in rules:
                        continue
                    signed = r["AMOUNT_CAD"] if r["FLOW_TYPE"] == "SUBSCRIPTION" else -r["AMOUNT_CAD"]
                    wf += signed * (last_day - int(r["FLOW_DATE"].day)) / last_day
                gross = (emv - bnav - net_flows) / (bnav + wf)
            else:
                # Naive: chain daily returns, treating each day's flow as occurring at open.
                navs = mn["NAV_CAD"].tolist()
                dts = mn["AS_OF_DATE"].tolist()
                prev = bnav
                g = 1.0
                for dt_, nv in zip(dts, navs):
                    day_flow = 0.0
                    dist_today = 0.0
                    dd = mf[mf["FLOW_DATE"] == dt_]
                    for _, r in dd.iterrows():
                        if r["FLOW_TYPE"] == "SUBSCRIPTION":
                            day_flow += r["AMOUNT_CAD"]
                        elif r["FLOW_TYPE"] == "REDEMPTION":
                            day_flow -= r["AMOUNT_CAD"]
                        elif 2 in rules:
                            dist_today += r["AMOUNT_CAD"]
                    g *= (nv + dist_today) / (prev + day_flow)
                    prev = nv
                gross = g - 1.0

            me = e[e["ACCRUAL_DATE"].dt.to_period("M") == period]
            fee_acc = float(me["MGMT_FEE_ACCRUED"].sum() + me["ADMIN_FEE_ACCRUED"].sum())
            other_acc = float(me["OTHER_EXPENSE"].sum())

            if 4 in rules:
                fee_drag = fee_acc / avg_nav
            else:
                # Naive: flat annual rate divided by 12.
                fee_drag = (mgmt + admin) / 10_000 / 12
            if 5 not in rules:
                fee_drag += other_acc / avg_nav

            net = gross - fee_drag
            bench = float(bm[(bmid, period)])

            if 7 in rules:
                excess = (1.0 + net) / (1.0 + bench) - 1.0
            else:
                excess = net - bench

            rows.append({
                "FUND_CODE": code, "PERIOD_END_DATE": mn.iloc[-1]["AS_OF_DATE"],
                "GROSS_RETURN_PCT": gross * 100, "NET_RETURN_PCT": net * 100,
                "BENCHMARK_RETURN_PCT": bench * 100, "EXCESS_RETURN_PCT": excess * 100,
                "DAYS_IN_MONTH": days,
                "HAS_FLOW": len(mf[mf["FLOW_TYPE"].isin(["SUBSCRIPTION", "REDEMPTION"])]) > 0,
                "HAS_DIST": dists > 0,
                "FLOW_PCT": (subs + reds) / bnav * 100,
            })
    return pd.DataFrame(rows)


def _resid(bundle, rules, col="NET_RETURN_PCT"):
    calc = _recompute(bundle, rules)
    tgt = bundle["target"]["VENDOR_FUND_PERFORMANCE_MONTHLY"]
    j = calc.merge(tgt[["FUND_CODE", "PERIOD_END_DATE", col]],
                   on=["FUND_CODE", "PERIOD_END_DATE"], suffixes=("_calc", "_tgt"))
    j["RESID_BPS"] = (j[f"{col}_calc"] - j[f"{col}_tgt"]) * 100
    return j


def _is_dec_outlier(df):
    return (df["FUND_CODE"] == "CIF-ALT-LS-06") & (df["PERIOD_END_DATE"].dt.month == 12)


def verify(bundle) -> int:
    failures = []
    print("\n" + "=" * 78)
    print("PUZZLE VERIFICATION")
    print("=" * 78)

    def check(label, ok, detail):
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}: {detail}")
        if not ok:
            failures.append(label)

    # ---- Rule 1: T-1 FX -------------------------------------------------------------
    print("\nRule 1 --- NAV uses T-1 FX")
    nv = _naive_ending_nav(bundle)
    mag = nv["RESID_BPS"].abs()
    check("detectable", 1.0 <= mag.median() <= 60.0,
          f"median |residual| = {mag.median():.2f} bps (want 1-60)")
    fxc = _fx_change(bundle)
    corr_df = nv.merge(fxc, on="AS_OF_DATE")
    c = corr_df["RESID_BPS"].corr(corr_df["FX_CHG_BPS"])
    check("correlated with FX move", abs(c) > 0.70, f"corr = {c:+.3f} (want |corr| > 0.70)")

    # ---- Rule 2: distributions reinvested -------------------------------------------
    print("\nRule 2 --- distributions treated as reinvested")
    r2 = _resid(bundle, {1, 3, 4, 5, 6, 7})
    r2 = r2[~_is_dec_outlier(r2)]
    dist_mag = r2[r2["HAS_DIST"]]["RESID_BPS"].abs()
    nodist_mag = r2[~r2["HAS_DIST"]]["RESID_BPS"].abs()
    check("fires only in distribution months",
          dist_mag.median() > 20.0 and nodist_mag.median() < 1.0,
          f"dist months median {dist_mag.median():.1f} bps vs "
          f"non-dist {nodist_mag.median():.3f} bps")
    check("distribution months exist", len(dist_mag) >= 6, f"{len(dist_mag)} rows")

    # ---- Rule 3: Modified Dietz -----------------------------------------------------
    print("\nRule 3 --- Modified Dietz, not daily chaining")
    r3 = _resid(bundle, {1, 2, 4, 5, 6, 7})
    r3 = r3[~_is_dec_outlier(r3)]
    flow_mag = r3[r3["HAS_FLOW"]]["RESID_BPS"].abs()
    noflow_mag = r3[~r3["HAS_FLOW"]]["RESID_BPS"].abs()
    check("detectable in flow months", 0.5 <= flow_mag.median() <= 200.0,
          f"flow months median |residual| = {flow_mag.median():.2f} bps")
    check("quiet in no-flow months", noflow_mag.median() < 0.5,
          f"no-flow median = {noflow_mag.median():.4f} bps")
    fl = r3[r3["HAS_FLOW"]].copy()
    # The gap between Modified Dietz and daily chaining scales with flow size *and* with how
    # much the fund moved over the month --- a flow into a flat month costs you nothing.
    fl["DRIVER"] = fl["FLOW_PCT"].abs() * fl["GROSS_RETURN_PCT"].abs()
    c3 = fl["RESID_BPS"].abs().corr(fl["DRIVER"])
    check("scales with flow size x return", abs(c3) > 0.40,
          f"corr = {c3:+.3f} (want > 0.40)")

    # ---- Rule 4: fees on average daily NAV ------------------------------------------
    print("\nRule 4 --- fees on average daily NAV over actual accrual days")
    r4 = _resid(bundle, {1, 2, 3, 5, 6, 7})
    r4 = r4[~_is_dec_outlier(r4)]
    m4 = r4["RESID_BPS"].abs()
    check("detectable", m4.median() >= 0.3, f"median |residual| = {m4.median():.2f} bps")
    c4 = r4["RESID_BPS"].corr(r4["DAYS_IN_MONTH"])
    check("correlated with business-day count", abs(c4) > 0.70,
          f"corr = {c4:+.3f} (want |corr| > 0.70)")

    # ---- Rule 5: other_expense excluded from net return -----------------------------
    print("\nRule 5 --- OTHER_EXPENSE excluded from net return")
    r5 = _resid(bundle, {1, 2, 3, 4, 6, 7})
    r5 = r5[~_is_dec_outlier(r5)]
    m5 = r5["RESID_BPS"].abs()
    check("detectable", m5.median() > 1.0, f"median |residual| = {m5.median():.2f} bps")
    check("one-sided (always a drag)", (r5["RESID_BPS"] < 0).mean() > 0.95,
          f"{(r5['RESID_BPS'] < 0).mean() * 100:.0f}% of rows negative")

    # ---- Rule 6: monthly-rebalanced blend -------------------------------------------
    print("\nRule 6 --- blended benchmark rebalances monthly (arithmetic)")
    r6 = _resid(bundle, {1, 2, 3, 4, 5, 7}, col="BENCHMARK_RETURN_PCT")
    blend = r6[r6["FUND_CODE"] == "CIF-BAL-60-03"]
    nonblend = r6[r6["FUND_CODE"] != "CIF-BAL-60-03"]
    check("fires only on the blended benchmark",
          blend["RESID_BPS"].abs().median() > 1.0
          and nonblend["RESID_BPS"].abs().median() < 0.01,
          f"blend median {blend['RESID_BPS'].abs().median():.2f} bps vs "
          f"single-index {nonblend['RESID_BPS'].abs().median():.4f} bps")

    # ---- Rule 7: geometric excess return --------------------------------------------
    print("\nRule 7 --- excess return is geometric")
    r7 = _resid(bundle, {1, 2, 3, 4, 5, 6}, col="EXCESS_RETURN_PCT")
    r7 = r7[~_is_dec_outlier(r7)]
    m7 = r7["RESID_BPS"].abs()
    check("detectable somewhere", m7.max() > 2.0, f"max |residual| = {m7.max():.2f} bps")
    tgt = bundle["target"]["VENDOR_FUND_PERFORMANCE_MONTHLY"]
    j7 = r7.merge(tgt[["FUND_CODE", "PERIOD_END_DATE", "BENCHMARK_RETURN_PCT"]],
                  on=["FUND_CODE", "PERIOD_END_DATE"], suffixes=("", "_t"))
    c7 = j7["RESID_BPS"].abs().corr(j7["BENCHMARK_RETURN_PCT_t"].abs())
    check("grows with return magnitude", abs(c7) > 0.40, f"corr = {c7:+.3f}")

    # ---- Monotone convergence over the net-return rules ------------------------------
    # Rules 6 and 7 act on the benchmark and excess columns, not net return, so the net
    # return ladder covers rules 1-5 only. Ordered by residual magnitude, which is the
    # order an attendee actually discovers them in.
    print("\nConvergence --- fixing rules in discovery order must shrink the residual")
    print("  (mean absolute residual on NET_RETURN_PCT, December outlier excluded)")
    ladder = [
        ("naive everything", set()),
        ("+ rule 2 (distributions)", {2}),
        ("+ rule 1 (T-1 FX)", {2, 1}),
        ("+ rule 3 (Modified Dietz)", {2, 1, 3}),
        ("+ rule 5 (other expense)", {2, 1, 3, 5}),
        ("+ rule 4 (fee basis)", {2, 1, 3, 5, 4}),
    ]
    prev = None
    for label, rules in ladder:
        r = _resid(bundle, rules)
        r = r[~_is_dec_outlier(r)]
        mean_abs = r["RESID_BPS"].abs().mean()
        arrow = "" if prev is None else ("  v" if mean_abs < prev else "  ^ REGRESSION")
        print(f"    {label:<28} mean |residual| = {mean_abs:9.3f} bps{arrow}")
        if prev is not None and mean_abs > prev:
            failures.append(f"convergence regressed at {label}")
        prev = mean_abs

    # ---- Full reconciliation --------------------------------------------------------
    print("\nFull reconciliation --- all seven rules")
    full = _resid(bundle, {1, 2, 3, 4, 5, 6, 7})
    outlier = full[_is_dec_outlier(full)]
    clean = full[~_is_dec_outlier(full)]
    worst = clean["RESID_BPS"].abs().max()
    check("71 of 72 rows reconcile to < 0.01 bps", worst < 0.01,
          f"worst clean |residual| = {worst:.6f} bps across {len(clean)} rows")
    check("December performance-fee row does NOT reconcile",
          outlier["RESID_BPS"].abs().max() > 5.0,
          f"outlier |residual| = {outlier['RESID_BPS'].abs().max():.1f} bps "
          f"({outlier.iloc[0]['FUND_CODE']} Dec)")

    # ---- Investor PII mix (AI Functions session) -------------------------------------
    print("\nInvestor PII --- AI_CLASSIFY / AI_REDACT material")
    inv = bundle["source"]["INVESTOR_ACCOUNTS"]
    notes = inv["KYC_NOTES"]
    # A note carries PII if it embeds a name, phone, email, SIN fragment or street address.
    has_pii = notes.str.contains(r"@|\(\d{3}\)|SIN ending|apartment|co-signed|Beneficiary",
                                 regex=True)
    rate = has_pii.mean()
    check("PII mix is genuinely mixed", 0.30 <= rate <= 0.60,
          f"{rate * 100:.0f}% of KYC notes carry PII (want 30-60%, so "
          f"'flag everything' scores badly)")
    # A naive regex catches the obvious formats but misses names in prose. That gap is the
    # whole argument for AI_CLASSIFY over a pattern match.
    regex_only = notes.str.contains(r"@|\(\d{3}\)\s\d{3}-\d{4}", regex=True)
    missed = int((has_pii & ~regex_only).sum())
    check("regex alone leaves a visible gap", missed >= 20,
          f"{missed} PII rows have no email or phone pattern to match on")
    check("notes are prose, not fields", notes.str.split().str.len().median() >= 9,
          f"median note length = {notes.str.split().str.len().median():.0f} words")

    print("\n" + "=" * 78)
    if failures:
        print(f"VERIFICATION FAILED --- {len(failures)} check(s):")
        for f in failures:
            print(f"  - {f}")
        print("=" * 78)
        return 1
    print("VERIFICATION PASSED --- the puzzle is solvable and correctly ordered.")
    print("=" * 78)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                    help="after generating, assert that the puzzle is solvable")
    ap.add_argument("--no-write", action="store_true", help="verify without writing CSVs")
    args = ap.parse_args()

    bundle = generate()
    if not args.no_write:
        write_csvs(bundle)
    if args.verify or args.no_write:
        sys.exit(verify(bundle))


if __name__ == "__main__":
    main()
