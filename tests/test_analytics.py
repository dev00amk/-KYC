import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_synthetic_data import generate_rows
from risk_analytics import (
    lookback_population,
    population_monitoring,
    threshold_simulation,
    top_rules,
    vendor_weekly,
)


def make_row(**overrides):
    row = {
        "application_id": "APP-TEST",
        "created_at": "2026-01-05T00:00:00",
        "week_start": "2026-01-05",
        "device": "ios",
        "mobile_risk_profile": "mobile_native",
        "vendor": "baseline_id",
        "vendor_flagged": 0,
        "vendor_latency_ms": 500,
        "vendor_match_rate": 0.95,
        "engine_action": "instant_approve",
        "review_reason_codes": "CLEAN",
        "commercial_po_box": 0,
        "sanctions_hit": 0,
        "doc_mismatch": 0,
        "device_fingerprint_mismatch": 0,
        "ssn_velocity_group": "",
        "phone_tenure_days": 180,
        "ip_risk_score": 25,
        "name_match_score": 95,
        "confirmed_fraud": 0,
        "queue_minutes": 0,
        "chargeoff_amount": 0,
        "active_balance": 0,
        "drop_step": "",
        "monitoring_trigger": "",
        "monitoring_resolution_hours": 0,
        "sop_override": 0,
        "missing_kyc_attribute": 0,
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
        self.assertTrue(all("review_reason_codes" in row for row in rows))

    def test_top_rules_fpr_denominator_is_non_fraud_population(self):
        rows = [
            make_row(application_id="fraud-hit", confirmed_fraud=1, sanctions_hit=1),
            make_row(application_id="fp-hit", confirmed_fraud=0, sanctions_hit=1),
            make_row(application_id="tn-1", confirmed_fraud=0, sanctions_hit=0),
            make_row(application_id="tn-2", confirmed_fraud=0, sanctions_hit=0),
        ]
        rules = top_rules(rows)
        sanctions_rule = next(rule for rule in rules if "sanctions" in rule["rule"].lower())
        self.assertAlmostEqual(sanctions_rule["false_positive_ratio"], 0.3333, places=3)

    def test_lookback_tier1_captures_all_sanctions_rows(self):
        rows = [
            make_row(application_id="s1", engine_action="instant_approve", sanctions_hit=1, active_balance=0.0),
            make_row(application_id="s2", engine_action="instant_approve", sanctions_hit=1, active_balance=10.0),
        ]
        result = lookback_population(rows)
        self.assertEqual(result["tiers"]["tier_1_sar_review"]["accounts"], 2)
        self.assertEqual(result["tiers"]["tier_2_step_up"]["accounts"], 0)

    def test_threshold_simulation_never_produces_negative_savings(self):
        rows = list(generate_rows(200, seed=99))
        scenarios = threshold_simulation(rows)
        for scenario in scenarios:
            self.assertGreaterEqual(
                scenario["estimated_monthly_savings"],
                0,
                f"Negative savings at scenario {scenario}",
            )

    def test_vendor_false_negative_rate_is_correct(self):
        rows = [
            make_row(application_id="caught", confirmed_fraud=1, vendor_flagged=1),
            make_row(application_id="missed", confirmed_fraud=1, vendor_flagged=0),
            make_row(application_id="clean", confirmed_fraud=0, vendor_flagged=0),
        ]
        series, _ = vendor_weekly(rows)
        self.assertAlmostEqual(series[0]["vendor_false_negative_rate"], 0.5, places=3)

    def test_population_monitoring_returns_psi_statuses(self):
        rows = list(generate_rows(200, seed=123))
        psi_rows = population_monitoring(rows)
        self.assertEqual({row["feature"] for row in psi_rows}, {
            "ip_risk_score",
            "name_match_score",
            "phone_tenure_days",
            "vendor_latency_ms",
        })
        self.assertTrue(all("status" in row for row in psi_rows))

    def test_vendor_match_rate_is_stable_within_vendor_week(self):
        rows = list(generate_rows(500, seed=326))
        rates_by_vendor_week = {}
        for row in rows:
            key = (row["vendor"], row["week_start"])
            rates_by_vendor_week.setdefault(key, set()).add(row["vendor_match_rate"])
        self.assertTrue(all(len(rates) == 1 for rates in rates_by_vendor_week.values()))


if __name__ == "__main__":
    unittest.main()
