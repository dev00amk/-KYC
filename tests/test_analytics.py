import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_synthetic_data import generate_rows
from risk_analytics import lookback_population, vendor_weekly


def make_row(**overrides):
    row = {
        "application_id": "APP-TEST",
        "week_start": "2026-01-05",
        "vendor": "baseline_id",
        "vendor_flagged": 0,
        "vendor_latency_ms": 500,
        "vendor_match_rate": 0.95,
        "engine_action": "instant_approve",
        "commercial_po_box": 0,
        "sanctions_hit": 0,
        "confirmed_fraud": 0,
        "chargeoff_amount": 0,
        "active_balance": 0,
    }
    row.update(overrides)
    return row


class AnalyticsTests(unittest.TestCase):
    def test_lookback_returns_zero_for_clean_data(self):
        clean = [make_row(engine_action="instant_approve", commercial_po_box=0, sanctions_hit=0)]
        result = lookback_population(clean)
        self.assertEqual(result["impacted_accounts"], 0)

    def test_drift_alert_fires_on_match_rate_drop(self):
        rows = [
            make_row(application_id=f"APP-A-{i}", week_start="2026-01-05", vendor_match_rate=0.95)
            for i in range(25)
        ] + [
            make_row(application_id=f"APP-B-{i}", week_start="2026-01-12", vendor_match_rate=0.74)
            for i in range(25)
        ]
        _, alerts = vendor_weekly(rows)
        self.assertTrue(any(alert["vendor"] == "baseline_id" for alert in alerts))

    def test_generator_row_count(self):
        rows = list(generate_rows(100, seed=42))
        self.assertEqual(len(rows), 100)
        self.assertTrue(all("application_id" in row for row in rows))
        self.assertTrue(all("monitoring_trigger" in row for row in rows))


if __name__ == "__main__":
    unittest.main()
