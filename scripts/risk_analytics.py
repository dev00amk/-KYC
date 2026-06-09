import argparse
import csv
import json
import logging
from collections import defaultdict
from math import log
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

ACTIVE_POLICY = {
    "name_match_threshold": 83,
    "ip_risk_threshold": 80,
    "phone_tenure_days": 30,
    "sanctions_hit_action": "Tier 1 review",
    "device_fingerprint_mismatch_action": "manual_review",
}

TIER_COMPLETION = {
    "tier_1_sar_review": 0.61,
    "tier_2_step_up": 0.74,
    "tier_3_reverify": 0.89,
}

PSI_WARNING_THRESHOLD = 0.10
PSI_CRITICAL_THRESHOLD = 0.25
TOXIC_RULE_FPR_THRESHOLD_PCT = 85.0
TOXIC_RULE_QUEUE_THRESHOLD_HOURS = 100.0


def load_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize(row) for row in reader]


def normalize(row):
    row.setdefault("device_fingerprint_mismatch", 0)
    row.setdefault("ssn_velocity_group", "")
    row.setdefault("monitoring_trigger", "")
    row.setdefault("monitoring_resolution_hours", 0)
    row.setdefault("re_review_outcome", "")
    row.setdefault("review_reason_codes", "CLEAN")
    row.setdefault("mobile_risk_profile", "mobile_native" if row.get("device") in {"ios", "android"} else "web_high_variance")
    for field in [
        "kyc_ssn_present",
        "kyc_ssn_verified",
        "kyc_address_verified",
        "kyc_dob_present",
        "kyc_dob_verified",
        "kyc_selfie_match_passed",
    ]:
        row.setdefault(field, 1)

    int_fields = [
        "vendor_flagged", "commercial_po_box", "sanctions_hit", "doc_mismatch",
        "device_fingerprint_mismatch", "phone_tenure_days", "ip_risk_score",
        "name_match_score", "confirmed_fraud", "queue_minutes",
        "monitoring_resolution_hours", "sop_override", "missing_kyc_attribute",
        "kyc_ssn_present", "kyc_ssn_verified", "kyc_address_verified",
        "kyc_dob_present", "kyc_dob_verified", "kyc_selfie_match_passed",
    ]
    float_fields = ["vendor_match_rate", "active_balance", "chargeoff_amount"]
    for field in int_fields:
        row[field] = int(row[field])
    for field in float_fields:
        row[field] = float(row[field])
    row["vendor_latency_ms"] = int(row["vendor_latency_ms"])
    return row


def rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0


def average(values):
    return round(sum(values) / len(values), 2) if values else 0


def percentile(values, pct):
    if not values:
        return 0
    values = sorted(values)
    index = min(len(values) - 1, int(round((pct / 100) * (len(values) - 1))))
    return values[index]


def calculate_psi(current_distribution, baseline_distribution):
    if len(current_distribution) != len(baseline_distribution):
        raise ValueError("Current and baseline distributions must have the same number of buckets.")

    psi = 0.0
    for current_pct, baseline_pct in zip(current_distribution, baseline_distribution):
        current = max(float(current_pct), 1e-6)
        baseline = max(float(baseline_pct), 1e-6)
        psi += (current - baseline) * log(current / baseline)
    return round(psi, 4)


def evaluate_population_stability(current_distribution, baseline_distribution):
    psi_value = calculate_psi(current_distribution, baseline_distribution)
    return psi_alert_from_value(psi_value)


def psi_alert_from_value(psi_value):
    if psi_value > PSI_CRITICAL_THRESHOLD:
        return {
            "psi": psi_value,
            "severity": "critical",
            "message": "PSI exceeds recalibration threshold.",
            "action": (
                "Deploy secondary fallback vendor cascade and flag decisioning "
                "thresholds for immediate re-tuning."
            ),
        }
    if psi_value >= PSI_WARNING_THRESHOLD:
        return {
            "psi": psi_value,
            "severity": "warning",
            "message": "Moderate distribution drift detected.",
            "action": "Queue automated threshold optimization simulation.",
        }
    return {
        "psi": psi_value,
        "severity": "stable",
        "message": "Risk distributions stable.",
        "action": "Keep current onboarding cutoffs active.",
    }


class RiskEngine:
    def __init__(
        self,
        fpr_threshold_pct=TOXIC_RULE_FPR_THRESHOLD_PCT,
        queue_threshold_hours=TOXIC_RULE_QUEUE_THRESHOLD_HOURS,
        latency_threshold_ms=900,
    ):
        self.fpr_threshold_pct = fpr_threshold_pct
        self.queue_threshold_hours = queue_threshold_hours
        self.latency_threshold_ms = latency_threshold_ms

    def identify_optimization_targets(self, rule_metrics):
        candidates = []
        for metric in rule_metrics:
            high_noise = metric.get("false_positive_rate_pct", 0) > self.fpr_threshold_pct
            high_queue = metric.get("queue_burden_hours", 0) > self.queue_threshold_hours
            latency_breach = metric.get("avg_api_latency_ms", 0) > self.latency_threshold_ms
            if high_noise and (high_queue or latency_breach):
                candidates.append(metric["rule_id"])
        return candidates

    def evaluate_population_stability(self, current_distribution, baseline_distribution):
        return evaluate_population_stability(current_distribution, baseline_distribution)


class AdvancedRiskEngine(RiskEngine):
    """
    Institutional-grade identity control engine.

    Executes automated vendor cascade routing, toxic-rule isolation, and PSI-based
    population stability enforcement without requiring a specific dataframe library.
    """

    def __init__(
        self,
        false_positive_tolerance=TOXIC_RULE_FPR_THRESHOLD_PCT,
        max_queue_burden_hours=TOXIC_RULE_QUEUE_THRESHOLD_HOURS,
        latency_threshold_ms=450,
        min_vendor_score=0.15,
    ):
        super().__init__(
            fpr_threshold_pct=false_positive_tolerance,
            queue_threshold_hours=max_queue_burden_hours,
            latency_threshold_ms=latency_threshold_ms,
        )
        self.fpr_tolerance = false_positive_tolerance
        self.max_burden = max_queue_burden_hours
        self.min_vendor_score = min_vendor_score

    def execute_vendor_cascade_routing(self, applications):
        """
        Route applications to a challenger cascade when primary vendor SLA or score quality degrades.

        Accepts either a list of dictionaries or a pandas-like DataFrame. This keeps CI lightweight
        while still allowing vectorized use in analyst notebooks.
        """
        logging.info("Initializing Champion/Challenger Identity Cascade Diagnostics.")
        if hasattr(applications, "copy") and hasattr(applications, "__setitem__") and "vendor_latency_ms" in applications:
            processed = applications.copy()
            degraded_mask = (
                (processed["vendor_latency_ms"] > self.latency_threshold_ms)
                | (processed["kyc_vendor_score"] < self.min_vendor_score)
            )
            processed["assigned_routing_tier"] = degraded_mask.map(
                {
                    True: "CHALLENGER_SECONDARY_CASCADE",
                    False: "CHAMPION_PRIMARY_PATH",
                }
            )
            cascade_count = int(degraded_mask.sum())
        else:
            processed = []
            cascade_count = 0
            for application in applications:
                routed = dict(application)
                degraded = (
                    routed.get("vendor_latency_ms", 0) > self.latency_threshold_ms
                    or routed.get("kyc_vendor_score", 1.0) < self.min_vendor_score
                )
                routed["assigned_routing_tier"] = (
                    "CHALLENGER_SECONDARY_CASCADE" if degraded else "CHAMPION_PRIMARY_PATH"
                )
                cascade_count += int(degraded)
                processed.append(routed)

        if cascade_count:
            logging.warning(
                "[SLA BREACH] Automatically rerouted %s applications to fallback pipeline.",
                cascade_count,
            )
        return processed

    def identify_optimization_targets(self, rule_metrics):
        toxic_rules = []
        for rule in rule_metrics:
            high_noise = rule.get("false_positive_rate_pct", 0) >= self.fpr_tolerance
            high_burden = rule.get("queue_burden_hours", 0) >= self.max_burden
            if high_noise and high_burden:
                toxic_rules.append(rule["rule_id"])
                logging.error(
                    "[GOVERNANCE VOID] Toxic control isolated: %s | FPR: %s%% | Queue burden: %s hrs.",
                    rule["rule_id"],
                    rule.get("false_positive_rate_pct"),
                    rule.get("queue_burden_hours"),
                )
        return toxic_rules


def lookback_population(rows):
    impacted = [
        row for row in rows
        if row["engine_action"] == "instant_approve"
        and (row["commercial_po_box"] or row["sanctions_hit"])
    ]
    tiers = {"tier_1_sar_review": [], "tier_2_step_up": [], "tier_3_reverify": []}
    for row in impacted:
        if row["sanctions_hit"] or row["confirmed_fraud"] or row["chargeoff_amount"] > 0:
            tiers["tier_1_sar_review"].append(row)
        elif row["commercial_po_box"] and row["active_balance"] > 250:
            tiers["tier_2_step_up"].append(row)
        else:
            tiers["tier_3_reverify"].append(row)

    return {
        "impacted_accounts": len(impacted),
        "active_balance_exposure": round(sum(row["active_balance"] for row in impacted), 2),
        "chargeoff_exposure": round(sum(row["chargeoff_amount"] for row in impacted), 2),
        "tiers": {
            tier: {
                "accounts": len(members),
                "active_balance": round(sum(row["active_balance"] for row in members), 2),
                "chargeoff": round(sum(row["chargeoff_amount"] for row in members), 2),
                "completion_rate": TIER_COMPLETION[tier],
            }
            for tier, members in tiers.items()
        },
    }


def vendor_weekly(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["week_start"], row["vendor"])].append(row)

    series = []
    previous = {}
    alerts = []
    for key in sorted(grouped):
        week, vendor = key
        members = grouped[key]
        match_rate = average([row["vendor_match_rate"] for row in members])
        latency = average([row["vendor_latency_ms"] for row in members])
        confirmed_fraud = sum(row["confirmed_fraud"] for row in members)
        false_positives = sum(
            1 for row in members if row["vendor_flagged"] and not row["confirmed_fraud"]
        )
        false_negatives = sum(
            1 for row in members if row["confirmed_fraud"] and not row["vendor_flagged"]
        )
        non_fraud = len(members) - confirmed_fraud

        row = {
            "week_start": week,
            "vendor": vendor,
            "applications": len(members),
            "match_rate": match_rate,
            "latency_ms": latency,
            "false_positive_ratio": rate(false_positives, non_fraud),
            "vendor_false_negative_rate": rate(false_negatives, confirmed_fraud),
        }
        series.append(row)

        prev = previous.get(vendor)
        if prev:
            match_drift = rate(match_rate - prev["match_rate"], prev["match_rate"])
            latency_drift = rate(latency - prev["latency_ms"], prev["latency_ms"])
            if match_drift <= -0.15 or latency_drift >= 0.15:
                recommendation = "Recommend: escalate to vendor SLA review."
                if vendor == "baseline_id":
                    recommendation = (
                        "Recommend: escalate to vendor SLA review; consider increasing "
                        "challenger_id traffic share to 60%."
                    )
                alerts.append({
                    "week_start": week,
                    "vendor": vendor,
                    "match_rate_change": round(match_drift, 4),
                    "latency_change": round(latency_drift, 4),
                    "message": "Control Drift Alert",
                    "vendor_recommendation": recommendation,
                })
        previous[vendor] = row
    return series, alerts


def threshold_simulation(rows):
    scenarios = []
    name_thresholds = [90, 87, 83, 80]
    ip_thresholds = [75, 80, 85]
    for name_threshold in name_thresholds:
        for ip_threshold in ip_thresholds:
            manual = []
            fraud_leak = 0
            for row in rows:
                rule_hit = (
                    row["name_match_score"] < name_threshold
                    or row["ip_risk_score"] > ip_threshold
                    or row["phone_tenure_days"] < 30
                    or row["sanctions_hit"]
                    or row["commercial_po_box"]
                    or row["device_fingerprint_mismatch"]
                )
                if rule_hit:
                    manual.append(row)
                elif row["confirmed_fraud"]:
                    fraud_leak += 1

            baseline_manual = sum(1 for row in rows if row["engine_action"] == "manual_review")
            monthly_hours_saved = max(0, (baseline_manual - len(manual)) * 0.22)
            scenarios.append({
                "name_match_threshold": name_threshold,
                "ip_risk_threshold": ip_threshold,
                "manual_review_count": len(manual),
                "manual_review_rate": rate(len(manual), len(rows)),
                "queue_p95_minutes": percentile([row["queue_minutes"] for row in manual if row["queue_minutes"]], 95),
                "estimated_monthly_savings": round(monthly_hours_saved * 34, 2),
                "fraud_leakage_rate": rate(fraud_leak, len(rows)),
            })
    return sorted(scenarios, key=lambda item: (item["fraud_leakage_rate"], item["manual_review_count"]))


def funnel(rows):
    steps = ["identity_form", "ssn_check", "address_check", "doc_upload", "selfie_match", "approved"]
    step_rank = {step: index for index, step in enumerate(steps)}

    series = []
    for step in steps:
        if step == "approved":
            applications = sum(1 for row in rows if row["final_status"] == "approved")
        else:
            applications = sum(
                1 for row in rows
                if not row["drop_step"] or step_rank[row["drop_step"]] >= step_rank[step]
            )
        series.append({"step": step, "applications": applications, "conversion_rate": rate(applications, len(rows))})
    return series


def top_rules(rows):
    ip_thresh = ACTIVE_POLICY["ip_risk_threshold"]
    name_thresh = ACTIVE_POLICY["name_match_threshold"]
    tenure_thresh = ACTIVE_POLICY["phone_tenure_days"]

    rules = {
        f"phone_tenure < {tenure_thresh}d": lambda row: row["phone_tenure_days"] < tenure_thresh,
        f"ip_risk_score > {ip_thresh}": lambda row: row["ip_risk_score"] > ip_thresh,
        f"name_match < {name_thresh}": lambda row: row["name_match_score"] < name_thresh,
        "commercial_po_box": lambda row: row["commercial_po_box"] == 1,
        "sanctions_hit": lambda row: row["sanctions_hit"] == 1,
        "doc_mismatch": lambda row: row["doc_mismatch"] == 1,
        "device_fp_mismatch": lambda row: row["device_fingerprint_mismatch"] == 1,
        "ssn_velocity_30d": lambda row: bool(row["ssn_velocity_group"]),
    }
    output = []
    total = len(rows)
    total_fraud = sum(row["confirmed_fraud"] for row in rows)
    non_fraud_total = total - total_fraud

    for name, predicate in rules.items():
        hits = [row for row in rows if predicate(row)]
        non_hits = [row for row in rows if not predicate(row)]
        fraud_in_hits = sum(row["confirmed_fraud"] for row in hits)
        fraud_missed = sum(row["confirmed_fraud"] for row in non_hits)
        non_fraud_in_hits = len(hits) - fraud_in_hits
        output.append({
            "rule": name,
            "hits": len(hits),
            "hit_rate": rate(len(hits), total),
            "fraud_capture_rate": rate(fraud_in_hits, total_fraud),
            "false_positive_ratio": rate(non_fraud_in_hits, non_fraud_total),
            "precision": rate(fraud_in_hits, len(hits)),
            "fraud_leakage_if_removed": rate(fraud_missed, total),
        })
    return sorted(output, key=lambda item: item["hits"], reverse=True)


def sanctions_screening(rows):
    screened = len(rows)
    hits = [row for row in rows if row["sanctions_hit"]]
    false_positives = [row for row in hits if not row["confirmed_fraud"]]
    tier_1 = [
        row for row in rows
        if row["engine_action"] == "instant_approve"
        and (row["sanctions_hit"] or row["confirmed_fraud"] or row["chargeoff_amount"] > 0)
    ]
    return {
        "screening_hit_rate": rate(len(hits), screened),
        "false_positive_rate": rate(len(false_positives), screened - sum(row["confirmed_fraud"] for row in rows)),
        "tier_1_remediation_count": len(tier_1),
        "avg_time_to_sar_referral_hours": average([row["queue_minutes"] / 60 for row in tier_1 if row["queue_minutes"]]) or 24,
    }


def monitoring(rows):
    approved = [row for row in rows if row["final_status"] == "approved"]
    triggered = [row for row in approved if row["monitoring_trigger"]]
    grouped = defaultdict(list)
    for row in triggered:
        grouped[row["monitoring_trigger"]].append(row)

    trigger_rows = []
    for trigger, members in sorted(grouped.items()):
        trigger_rows.append({
            "trigger": trigger,
            "accounts": len(members),
            "re_review_rate": rate(len(members), len(approved)),
            "avg_resolution_hours": average([row["monitoring_resolution_hours"] for row in members]),
            "prior_onboarding_flags": sum(
                1 for row in members
                if row["commercial_po_box"] or row["sanctions_hit"] or row["device_fingerprint_mismatch"]
            ),
        })
    return {
        "approved_accounts": len(approved),
        "triggered_accounts": len(triggered),
        "re_review_rate": rate(len(triggered), len(approved)),
        "triggers": trigger_rows,
        "outcomes": [
            {
                "outcome": outcome,
                "accounts": sum(1 for row in triggered if row["re_review_outcome"] == outcome),
                "share": rate(sum(1 for row in triggered if row["re_review_outcome"] == outcome), len(triggered)),
            }
            for outcome in sorted({row["re_review_outcome"] for row in triggered if row["re_review_outcome"]})
        ],
    }


def device_risk(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["device"]].append(row)
    return [
        {
            "device": device,
            "applications": len(members),
            "manual_review_rate": rate(sum(1 for row in members if row["engine_action"] == "manual_review"), len(members)),
            "fraud_rate": rate(sum(row["confirmed_fraud"] for row in members), len(members)),
            "avg_ip_risk_score": average([row["ip_risk_score"] for row in members]),
        }
        for device, members in sorted(grouped.items())
    ]


def identity_attribute_completeness(rows):
    attributes = [
        ("SSN present", "kyc_ssn_present"),
        ("SSN verified", "kyc_ssn_verified"),
        ("Address verified", "kyc_address_verified"),
        ("DOB present", "kyc_dob_present"),
        ("DOB verified", "kyc_dob_verified"),
        ("Selfie match passed", "kyc_selfie_match_passed"),
    ]
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["device"]].append(row)

    output = []
    for device, members in sorted(grouped.items()):
        for label, field in attributes:
            output.append({
                "segment": device,
                "attribute": label,
                "completion_rate": rate(sum(row[field] for row in members), len(members)),
            })
    return output


def population_stability_index(rows, feature, n_bins=10):
    sorted_rows = sorted(rows, key=lambda row: row["created_at"])
    mid = len(sorted_rows) // 2
    baseline_vals = [row[feature] for row in sorted_rows[:mid] if isinstance(row[feature], (int, float))]
    compare_vals = [row[feature] for row in sorted_rows[mid:] if isinstance(row[feature], (int, float))]

    if not baseline_vals or not compare_vals:
        return {"feature": feature, "psi": None, "status": "insufficient_data", "bins": []}

    all_vals = baseline_vals + compare_vals
    min_v, max_v = min(all_vals), max(all_vals)
    if min_v == max_v:
        return {"feature": feature, "psi": 0.0, "status": "stable", "bins": []}

    bin_edges = [min_v + i * (max_v - min_v) / n_bins for i in range(n_bins + 1)]
    bin_edges[-1] += 1e-9

    def bin_counts(values):
        counts = [0] * n_bins
        for value in values:
            for index in range(n_bins):
                if bin_edges[index] <= value < bin_edges[index + 1]:
                    counts[index] += 1
                    break
        return counts

    base_counts = bin_counts(baseline_vals)
    comp_counts = bin_counts(compare_vals)
    n_base, n_comp = len(baseline_vals), len(compare_vals)

    psi = 0.0
    bins = []
    for index in range(n_bins):
        base_pct = max(base_counts[index] / n_base, 1e-6)
        comp_pct = max(comp_counts[index] / n_comp, 1e-6)
        bucket_psi = (comp_pct - base_pct) * log(comp_pct / base_pct)
        psi += bucket_psi
        bins.append({
            "bin_low": round(bin_edges[index], 2),
            "bin_high": round(bin_edges[index + 1], 2),
            "baseline_pct": round(base_pct, 4),
            "compare_pct": round(comp_pct, 4),
            "bucket_psi": round(bucket_psi, 4),
        })

    psi = round(psi, 4)
    alert = psi_alert_from_value(psi)
    status = "stable" if psi < 0.10 else ("moderate_shift" if psi < 0.25 else "major_shift_recalibrate")
    return {
        "feature": feature,
        "psi": psi,
        "status": status,
        "alert_severity": alert["severity"],
        "recommended_action": alert["action"],
        "bins": bins,
    }


def population_monitoring(rows):
    features = ["ip_risk_score", "name_match_score", "phone_tenure_days", "vendor_latency_ms"]
    return [population_stability_index(rows, feature) for feature in features]


def summarize(rows):
    approved = sum(1 for row in rows if row["final_status"] == "approved")
    manual = sum(1 for row in rows if row["engine_action"] == "manual_review")
    fraud = sum(row["confirmed_fraud"] for row in rows)
    return {
        "applications": len(rows),
        "approval_rate": rate(approved, len(rows)),
        "manual_review_rate": rate(manual, len(rows)),
        "confirmed_fraud_rate": rate(fraud, len(rows)),
        "avg_queue_minutes": average([row["queue_minutes"] for row in rows if row["queue_minutes"]]),
        "sop_deviation_rate": rate(sum(row["sop_override"] for row in rows), len(rows)),
        "missing_kyc_rate": rate(sum(row["missing_kyc_attribute"] for row in rows), len(rows)),
    }


def main():
    parser = argparse.ArgumentParser(description="Run KYC risk analytics and dashboard extracts.")
    parser.add_argument("--input", default="data/kyc_applications.csv")
    parser.add_argument("--output", default="dashboard/dashboard_data.json")
    args = parser.parse_args()

    rows = load_rows(args.input)
    vendor_series, drift_alerts = vendor_weekly(rows)
    data = {
        "summary": summarize(rows),
        "lookback": lookback_population(rows),
        "vendor_weekly": vendor_series,
        "drift_alerts": drift_alerts,
        "threshold_scenarios": threshold_simulation(rows),
        "funnel": funnel(rows),
        "rules": top_rules(rows),
        "sanctions": sanctions_screening(rows),
        "monitoring": monitoring(rows),
        "device_risk": device_risk(rows),
        "identity_completeness": identity_attribute_completeness(rows),
        "population_stability": population_monitoring(rows),
        "active_policy": ACTIVE_POLICY,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote dashboard extract to {out_path}")
    print(json.dumps(data["summary"], indent=2))


if __name__ == "__main__":
    main()
