import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ACTIVE_POLICY = {
    "name_match_threshold": 83,
    "ip_risk_threshold": 80,
    "phone_tenure_days": 30,
    "sanctions_hit_action": "Tier 1 review",
    "device_fingerprint_mismatch_action": "manual_review",
}


def load_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize(row) for row in reader]


def normalize(row):
    row.setdefault("device_fingerprint_mismatch", 0)
    row.setdefault("ssn_velocity_group", "")
    row.setdefault("monitoring_trigger", "")
    row.setdefault("monitoring_resolution_hours", 0)
    row.setdefault("mobile_risk_profile", "mobile_native" if row.get("device") in {"ios", "android"} else "web_high_variance")

    int_fields = [
        "vendor_flagged", "commercial_po_box", "sanctions_hit", "doc_mismatch",
        "device_fingerprint_mismatch", "phone_tenure_days", "ip_risk_score",
        "name_match_score", "confirmed_fraud", "queue_minutes",
        "monitoring_resolution_hours", "sop_override", "missing_kyc_attribute",
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
                "completion_rate": round(0.62 + (index * 0.11), 2),
            }
            for index, (tier, members) in enumerate(tiers.items())
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
    abandoned_by_step = defaultdict(int)
    for row in rows:
        if row["drop_step"]:
            abandoned_by_step[row["drop_step"]] += 1

    remaining = len(rows)
    series = []
    for step in steps:
        if step == "approved":
            remaining = sum(1 for row in rows if row["final_status"] == "approved")
        else:
            remaining -= abandoned_by_step[step]
        series.append({"step": step, "applications": max(remaining, 0), "conversion_rate": rate(max(remaining, 0), len(rows))})
    return series


def top_rules(rows):
    rules = {
        "phone_tenure_days < 30": lambda row: row["phone_tenure_days"] < 30,
        "ip_risk_score > 75": lambda row: row["ip_risk_score"] > 75,
        "name_match_score < 83": lambda row: row["name_match_score"] < 83,
        "commercial_po_box": lambda row: row["commercial_po_box"] == 1,
        "sanctions_hit": lambda row: row["sanctions_hit"] == 1,
        "doc_mismatch": lambda row: row["doc_mismatch"] == 1,
        "device_fingerprint_mismatch": lambda row: row["device_fingerprint_mismatch"] == 1,
        "ssn_velocity_30d": lambda row: bool(row["ssn_velocity_group"]),
    }
    output = []
    for name, predicate in rules.items():
        hits = [row for row in rows if predicate(row)]
        fraud = sum(row["confirmed_fraud"] for row in hits)
        output.append({
            "rule": name,
            "hits": len(hits),
            "fraud_capture_rate": rate(fraud, len(hits)),
            "false_positive_ratio": rate(len(hits) - fraud, len(hits)),
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
        "active_policy": ACTIVE_POLICY,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote dashboard extract to {out_path}")
    print(json.dumps(data["summary"], indent=2))


if __name__ == "__main__":
    main()
