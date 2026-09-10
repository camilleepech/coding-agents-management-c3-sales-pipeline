"""Red command for BUG-REPORT.md.

Finance reconciled store S-014 against the till receipts and gets 56 232,09 €
for August; the pipeline reports 50 043,47 €. This rebuilds the warehouse from
the real raw files and checks the S-014 monthly total against the finance figure.

Fails on the original code, passes once the amount parsing is fixed.
"""

from decimal import Decimal
from pathlib import Path

from pipeline import ingest, load, report, transform

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

FINANCE_TOTAL_S014 = Decimal("56232.09") 


def test_s014_monthly_total_matches_finance(tmp_path):
    rows = ingest.read_all(RAW_DIR)
    records = transform.transform_all(rows)
    conn = load.connect(tmp_path / "warehouse.db")
    load.load(records, conn)

    total = report.store_total(conn, "S-014")

    assert total == FINANCE_TOTAL_S014, f"S-014 off by {FINANCE_TOTAL_S014 - total}"
