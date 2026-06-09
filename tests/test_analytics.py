import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_synthetic_data import generate_rows
from risk_analytics import (
    AdvancedRiskEngine,
    IdentityVendorCircuitBreaker,
    RiskEngine,
    calculate_population_stability_index,
    evaluate_population_stability,
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
    def setUp(self):
        self.engine = AdvancedRiskEngine(false_positive_tolerance=85.0, max_queue_burden_hours=100.0)

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

    def test_toxic_rule_isolation(self):
        engine = RiskEngine()
        sample_metrics = {
            "rule_id": "R_099_WEB_SESSION_VELOCITY",
            "false_positive_rate_pct": 89.5,
            "queue_burden_hours": 120,
            "avg_api_latency_ms": 640,
        }
        optimization_candidates = engine.identify_optimization_targets([sample_metrics])
        self.assertIn("R_099_WEB_SESSION_VELOCITY", optimization_candidates)

    def test_population_stability_critical_alert(self):
        alert = evaluate_population_stability(
            current_distribution=[0.02, 0.03, 0.95],
            baseline_distribution=[0.33, 0.33, 0.34],
        )
        self.assertEqual(alert["severity"], "critical")
        self.assertIn("fallback vendor", alert["action"])

    def test_advanced_engine_stochastic_toxic_rule_isolation(self):
        mock_pipeline_rules = [
            {
                "rule_id": "R_099_WEB_VELOCITY_HIGH_FRICTION",
                "false_positive_rate_pct": 92.4,
                "queue_burden_hours": 145.0,
            },
            {
                "rule_id": "R_001_SSN_DETERMINISTIC_MATCH",
                "false_positive_rate_pct": 1.2,
                "queue_burden_hours": 12.0,
            },
        ]

        targets = self.engine.identify_optimization_targets(mock_pipeline_rules)

        self.assertIn("R_099_WEB_VELOCITY_HIGH_FRICTION", targets)
        self.assertNotIn("R_001_SSN_DETERMINISTIC_MATCH", targets)

    def test_advanced_engine_vendor_cascade_logic(self):
        mock_data = [
            {"user_id": "U001", "vendor_latency_ms": 600, "kyc_vendor_score": 0.80},
            {"user_id": "U002", "vendor_latency_ms": 120, "kyc_vendor_score": 0.95},
            {"user_id": "U003", "vendor_latency_ms": 200, "kyc_vendor_score": 0.10},
        ]

        processed = self.engine.execute_vendor_cascade_routing(mock_data)
        routing = {row["user_id"]: row["assigned_routing_tier"] for row in processed}

        self.assertEqual(routing["U001"], "CHALLENGER_SECONDARY_CASCADE")
        self.assertEqual(routing["U002"], "CHAMPION_PRIMARY_PATH")
        self.assertEqual(routing["U003"], "CHALLENGER_SECONDARY_CASCADE")

    def test_malformed_production_data_handling(self):
        corrupted_mock_data = pd.DataFrame({
            "user_id": ["U_CRASH_1", "U_CRASH_2"],
            "vendor_latency_ms": [None, np.nan],
            "kyc_vendor_score": [None, 0.95],
        })

        processed_df = self.engine.execute_vendor_cascade_routing(corrupted_mock_data)

        first_route = processed_df.loc[
            processed_df["user_id"] == "U_CRASH_1", "assigned_routing_tier"
        ].values[0]
        second_route = processed_df.loc[
            processed_df["user_id"] == "U_CRASH_2", "assigned_routing_tier"
        ].values[0]
        self.assertEqual(first_route, "CHALLENGER_SECONDARY_CASCADE")
        self.assertEqual(second_route, "CHALLENGER_SECONDARY_CASCADE")

    def test_malformed_dict_payload_handling(self):
        corrupted_mock_data = [
            {"user_id": "U_BAD_1", "vendor_latency_ms": "timeout", "kyc_vendor_score": "n/a"},
            {"user_id": "U_BAD_2"},
        ]

        processed = self.engine.execute_vendor_cascade_routing(corrupted_mock_data)
        routing = {row["user_id"]: row["assigned_routing_tier"] for row in processed}

        self.assertEqual(routing["U_BAD_1"], "CHALLENGER_SECONDARY_CASCADE")
        self.assertEqual(routing["U_BAD_2"], "CHALLENGER_SECONDARY_CASCADE")

    def test_vectorized_psi_survives_poisoned_current_payload(self):
        rng = np.random.default_rng(326)
        baseline_scores = pd.Series(rng.normal(0.5, 0.1, 1000))
        poisoned_current = pd.Series([np.nan, np.inf, -np.inf, "corrupted_payload", 0.5, 0.6])

        result = calculate_population_stability_index(baseline_scores, poisoned_current)

        self.assertIsInstance(result, float)
        self.assertFalse(np.isnan(result))

    def test_vectorized_psi_handles_constant_distribution(self):
        result = calculate_population_stability_index([0.7, 0.7, 0.7], [0.7, 0.7])

        self.assertEqual(result, 0.0)

    def test_vectorized_psi_handles_empty_current_distribution(self):
        result = calculate_population_stability_index([0.1, 0.2, 0.3], [np.nan, np.inf, "bad"])

        self.assertEqual(result, 0.0)

    def test_identity_vendor_circuit_breaker_opens_and_recovers(self):
        breaker = IdentityVendorCircuitBreaker(failure_threshold=2, recovery_timeout_seconds=0)

        self.assertTrue(breaker.allow_request())
        breaker.record_execution(success=False, latency_ms=100)
        self.assertEqual(breaker.state, "CLOSED")

        breaker.record_execution(success=True, latency_ms=1500)
        self.assertEqual(breaker.state, "OPEN")
        self.assertFalse(breaker.allow_request())

        breaker.record_execution(success=True, latency_ms=100)
        self.assertEqual(breaker.state, "CLOSED")
        self.assertTrue(breaker.allow_request())


if __name__ == "__main__":
    unittest.main()
