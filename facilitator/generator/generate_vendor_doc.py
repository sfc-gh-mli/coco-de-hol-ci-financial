#!/usr/bin/env python3
"""Generate Meridian's performance methodology statement as a PDF.

This is the document attendees run AI_PARSE_DOCUMENT and AI_EXTRACT against in Session 2.
It is written the way real vendor methodology statements are written: confident, prose-heavy,
and vague in exactly the places that matter.

Of the seven substantive methodology claims embedded in the prose, five CONTRADICT what the
data actually shows and two are accurate. That asymmetry is the point of the exercise --- the
deliverable is not "extract the claims", it is "diff the claims against what you proved".

Claims and their status (see facilitator/SOLUTION.md for the proving SQL):
  1. "time-weighted rate of return"              CONTRADICTS  (actually Modified Dietz)
  2. "exchange rates prevailing on the valuation date"  CONTRADICTS  (actually prior day)
  3. "net of all fund operating expenses"        CONTRADICTS  (excludes OTHER_EXPENSE)
  4. "distributions are treated as reinvested"   ACCURATE
  5. "blended benchmarks rebalanced monthly"     ACCURATE
  6. "excess return = fund less benchmark"       CONTRADICTS  (actually geometric)
  7. "performance fees accrued monthly"          CONTRADICTS  (crystallised annually in Dec)

The claims are deliberately embedded mid-paragraph rather than in a tidy table. A document
whose facts are already in a table does not demonstrate anything about extraction.

Usage:
    python3 generate_vendor_doc.py
"""

from pathlib import Path

from fpdf import FPDF
from fpdf.fpdf import FPDF_VERSION

OUT = Path(__file__).resolve().parent.parent.parent / "data" / "documents"
FILENAME = "meridian_performance_methodology_2025.pdf"

# Pinned so the PDF is byte-reproducible. fpdf stamps datetime.now() into /CreationDate by
# default, which means an unchanged regeneration still shows up as a modified file in git and
# breaks the "regenerate and confirm a clean working tree" reproducibility check. Matches the
# document's stated effective date rather than the build time, which is also more honest.
CREATION_DATE = "D:20250101000000"

# fpdf 1.7 is latin-1 only, so everything here stays plain ASCII on purpose.

TITLE = "Performance Measurement Methodology Statement"
SUBTITLE = "Meridian Performance Analytics Inc."
META = [
    ("Document reference", "MPA-METH-2025-04"),
    ("Version", "4.2"),
    ("Effective date", "1 January 2025"),
    ("Prepared for", "CI Financial - Asset Management Operations"),
    ("Classification", "Client Confidential"),
]

SECTIONS = [
    ("1. Purpose and Scope", [
        "This statement describes the methodology Meridian Performance Analytics Inc. "
        "(\"Meridian\") applies when calculating and reporting investment performance for "
        "portfolios administered on behalf of CI Financial. It is provided for the "
        "information of the client's operations, finance and compliance functions and is "
        "reviewed annually by our Performance Oversight Committee.",

        "The methodology set out below applies to all pooled fund mandates covered under "
        "Schedule B of the master services agreement. Where a mandate is subject to "
        "mandate-specific terms, those terms prevail. Meridian's calculations are performed "
        "in accordance with prevailing industry practice and are subject to the limitations "
        "described in Section 7.",
    ]),
    ("2. Valuation", [
        "Portfolio market values are struck daily using official closing prices sourced from "
        "our primary pricing vendors, with secondary sources applied under our price "
        "challenge procedure where a primary price is unavailable or fails validation.",

        "For holdings denominated in a currency other than the portfolio's base currency, "
        "market values are converted using the exchange rates prevailing on the valuation "
        "date. Rates are sourced from a single consolidated feed to ensure internal "
        "consistency across mandates and reporting periods.",

        "Net asset value is reported after accrual of all liabilities known to Meridian as "
        "at the valuation point, including accrued management and administration fees.",
    ]),
    ("3. Return Calculation", [
        "Meridian calculates portfolio returns on a time-weighted rate of return basis, "
        "which removes the effect of the timing and magnitude of external cash flows and "
        "therefore reflects the performance of the investment mandate rather than the "
        "behaviour of the investor. Returns are calculated at the total portfolio level and "
        "compounded to produce quarterly, annual and since-inception figures.",

        "External cash flows comprise subscriptions and redemptions. Income distributions "
        "paid out of the fund are not treated as external cash flows; distributions are "
        "treated as reinvested at the distribution date for the purpose of return "
        "measurement, consistent with a total return presentation.",

        "Returns are presented net of all fund operating expenses, including management "
        "fees, administration fees, and other ordinary operating costs borne by the fund. "
        "Gross returns, where shown, are presented before the deduction of these amounts.",
    ]),
    ("4. Fees and Expenses", [
        "Management and administration fees are accrued in accordance with the fee schedule "
        "applicable to each mandate and are reflected in net return figures for the period "
        "in which they are accrued.",

        "Where a mandate carries a performance fee, the fee is accrued monthly on the basis "
        "of performance measured to that month end, and is reflected in the net return for "
        "each month in which an accrual arises. Performance fee arrangements are described "
        "in the relevant offering documentation.",

        "The expense ratio reported for each period is calculated as total fund expenses for "
        "the period expressed as a percentage of average net assets, annualised.",
    ]),
    ("5. Benchmarks", [
        "Each mandate is measured against the benchmark specified in its investment policy "
        "statement. Benchmark returns are sourced directly from the relevant index provider "
        "and are used without adjustment.",

        "Where a mandate is measured against a blended benchmark, component index returns "
        "are combined using the target weights set out in the investment policy statement. "
        "Blended benchmarks are rebalanced monthly to their target weights.",

        "Excess return is presented as the fund return less the benchmark return for the "
        "corresponding period. Excess return figures are shown to two decimal places and "
        "may not sum across periods due to rounding and compounding.",
    ]),
    ("6. Data Sources and Client Responsibilities", [
        "Meridian's calculations rely on holdings, transaction, cash flow and fee data "
        "supplied by the client or the client's administrator. Meridian applies automated "
        "validation to detect gaps, duplicates and outliers, and will query apparent "
        "anomalies, but does not independently verify the completeness or accuracy of "
        "client-supplied data.",

        "The client is responsible for ensuring that data supplied to Meridian is complete, "
        "accurate, and free of personal information not required for the performance of the "
        "services. Meridian's data handling obligations are set out in Schedule D.",
    ]),
    ("7. Limitations and Contact", [
        "Past performance is not indicative of future results. This statement describes "
        "methodology only and does not constitute investment advice. Meridian reserves the "
        "right to amend this methodology, with notice to affected clients, where required to "
        "reflect changes in market practice, regulation, or the underlying data available.",

        "Questions concerning this statement, or requests for clarification of a specific "
        "calculation, should be directed to the Performance Oversight Committee via your "
        "Meridian client service representative, quoting the document reference above.",
    ]),
]

VERSION_HISTORY = [
    ("4.2", "1 Jan 2025", "Annual review. Benchmark section clarified."),
    ("4.1", "1 Jan 2024", "Updated pricing vendor hierarchy."),
    ("4.0", "1 Jan 2023", "Restructured to align with revised service schedules."),
    ("3.3", "1 Jul 2021", "Editorial amendments only."),
]


class Doc(FPDF):
    def _putinfo(self):
        """Same as FPDF._putinfo but with a fixed creation date.

        Overridden rather than post-processing the output bytes so the reason lives next to the
        behaviour. See CREATION_DATE above.
        """
        self._out("/Producer " + self._textstring("PyFPDF " + FPDF_VERSION
                                                 + " http://pyfpdf.googlecode.com/"))
        for attr, key in (("title", "/Title"), ("subject", "/Subject"),
                          ("author", "/Author"), ("keywords", "/Keywords"),
                          ("creator", "/Creator")):
            if hasattr(self, attr):
                self._out(f"{key} " + self._textstring(getattr(self, attr)))
        self._out("/CreationDate " + self._textstring(CREATION_DATE))

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"{SUBTITLE} - {TITLE}", 0, 1, "R")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"MPA-METH-2025-04  |  Client Confidential  |  Page {self.page_no()}",
                  0, 0, "C")
        self.set_text_color(0, 0, 0)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = Doc(format="Letter", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(22, 20, 22)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.multi_cell(0, 7, SUBTITLE)
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 13)
    pdf.multi_cell(0, 6, TITLE)
    pdf.ln(4)

    pdf.set_draw_color(41, 181, 232)
    pdf.set_line_width(0.6)
    y = pdf.get_y()
    pdf.line(22, y, 194, y)
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 9)
    for label, value in META:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(42, 5, f"{label}:", 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, value, 0, 1)
    pdf.ln(5)

    for heading, paragraphs in SECTIONS:
        if pdf.get_y() > 235:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, heading)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        for p in paragraphs:
            pdf.multi_cell(0, 5, p)
            pdf.ln(2)
        pdf.ln(2)

    if pdf.get_y() > 210:
        pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, "Appendix A - Version History")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(22, 6, "Version", 1, 0)
    pdf.cell(32, 6, "Effective", 1, 0)
    pdf.cell(0, 6, "Summary of change", 1, 1)
    pdf.set_font("Helvetica", "", 9)
    for v, d, s in VERSION_HISTORY:
        pdf.cell(22, 6, v, 1, 0)
        pdf.cell(32, 6, d, 1, 0)
        pdf.cell(0, 6, s, 1, 1)

    path = OUT / FILENAME
    pdf.output(str(path))
    size_kb = path.stat().st_size / 1024
    print(f"wrote {path} ({size_kb:.1f} KB, {pdf.page_no()} pages)")
    return path


if __name__ == "__main__":
    build()
