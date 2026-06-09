import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


FIRST_NAMES = [
    "Ava", "Maya", "Noah", "Liam", "Emma", "Olivia", "Sophia", "Ethan",
    "Lucas", "Mia", "Isabella", "Amir", "Priya", "Mateo", "Sofia", "Zoe",
]
LAST_NAMES = [
    "Patel", "Garcia", "Smith", "Johnson", "Brown", "Nguyen", "Kim",
    "Martinez", "Davis", "Wilson", "Lee", "Anderson", "Thomas", "Moore",
]
STATES = ["CA", "TX", "NY", "FL", "IL", "GA", "AZ", "NC", "WA", "OH"]
VENDORS = ["baseline_id", "challenger_id"]
ACTIVE_IP_THRESHOLD = 80
ACTIVE_NAME_THRESHOLD = 83
ACTIVE_PHONE_TENURE_THRESHOLD = 30


def chance(probability: float) -> bool:
    return random.random() < probability


def weighted_choice(options):
    total = sum(weight for _, weight in options)
    marker = random.uniform(0, total)
    running = 0
    for value, weight in options:
        running += weight
        if marker <= running:
            return value
    return options[-1][0]


def device_adjusted_ip_risk(device: str) -> int:
    means = {"ios": 33, "android": 36, "web": 51}
    return min(100, max(0, int(random.gauss(means[device], 19))))


def monitoring_trigger_for(final_status, confirmed_fraud, active_balance, sanctions_hit):
    if final_status != "approved":
        return "", 0
    if sanctions_hit and chance(0.35):
        return "sanctions_rescan_hit", max(2, int(random.gauss(68, 22)))
    if confirmed_fraud and chance(0.6):
        return "chargeback_dispute", max(2, int(random.gauss(54, 18)))
    if active_balance > 2000 and chance(0.04):
        return "velocity_flag", max(2, int(random.gauss(36, 14)))
    if chance(0.015):
        return "address_change_30d", max(2, int(random.gauss(48, 16)))
    return "", 0


def build_reason_codes(
    sanctions_hit,
    commercial_po_box,
    doc_mismatch,
    device_fingerprint_mismatch,
    ssn_velocity_group,
    phone_tenure_days,
    ip_risk_score,
    name_match_score,
):
    reason_codes = []
    if sanctions_hit:
        reason_codes.append("R01_SANCTIONS_HIT")
    if commercial_po_box:
        reason_codes.append("R02_PO_BOX_ADDRESS")
    if doc_mismatch:
        reason_codes.append("R03_DOC_MISMATCH")
    if device_fingerprint_mismatch:
        reason_codes.append("R04_DEVICE_FP_MISMATCH")
    if bool(ssn_velocity_group):
        reason_codes.append("R05_SSN_VELOCITY")
    if phone_tenure_days < ACTIVE_PHONE_TENURE_THRESHOLD:
        reason_codes.append("R06_PHONE_TENURE_LOW")
    if ip_risk_score > ACTIVE_IP_THRESHOLD:
        reason_codes.append("R07_IP_RISK_HIGH")
    if name_match_score < ACTIVE_NAME_THRESHOLD:
        reason_codes.append("R08_NAME_MATCH_LOW")
    return "|".join(reason_codes) if reason_codes else "CLEAN"


def generate_rows(n: int, seed: int):
    random.seed(seed)
    start = datetime(2026, 1, 1)
    ssn_reuse_pool = [f"SSN-GROUP-{i:03d}" for i in range(1, 70)]
    vendor_week_match_rate = {}

    def get_vendor_match_rate(vendor, week_str, created_at):
        key = (vendor, week_str)
        if key not in vendor_week_match_rate:
            base = random.uniform(0.91, 0.97) if vendor == "challenger_id" else random.uniform(0.89, 0.95)
            if vendor == "baseline_id" and created_at >= datetime(2026, 3, 16):
                base -= random.uniform(0.08, 0.17)
            vendor_week_match_rate[key] = round(max(0.45, min(0.99, base)), 4)
        return vendor_week_match_rate[key]

    for i in range(1, n + 1):
        created_at = start + timedelta(days=random.randint(0, 118), minutes=random.randint(0, 1439))
        week_start = created_at - timedelta(days=created_at.weekday())
        glitch_window = datetime(2026, 1, 15) <= created_at <= datetime(2026, 3, 20)

        device = weighted_choice([("ios", 48), ("android", 42), ("web", 10)])
        mobile_risk_profile = "mobile_native" if device in {"ios", "android"} else "web_high_variance"
        commercial_po_box = chance(0.035)
        sanctions_hit = chance(0.025)
        doc_mismatch = chance(0.07)
        device_fingerprint_mismatch = chance(0.042 if device == "web" else 0.022)
        ssn_velocity_group = random.choice(ssn_reuse_pool) if chance(0.028) else ""
        phone_tenure_days = random.randint(0, 730)
        ip_risk_score = device_adjusted_ip_risk(device)
        name_match_score = min(100, max(50, int(random.gauss(91, 6))))

        true_high_risk = (
            commercial_po_box
            or sanctions_hit
            or doc_mismatch
            or device_fingerprint_mismatch
            or bool(ssn_velocity_group)
            or phone_tenure_days < ACTIVE_PHONE_TENURE_THRESHOLD
            or ip_risk_score > ACTIVE_IP_THRESHOLD
            or name_match_score < ACTIVE_NAME_THRESHOLD
        )

        fraud_probability = 0.008
        fraud_probability += 0.08 if commercial_po_box else 0
        fraud_probability += 0.18 if sanctions_hit else 0
        fraud_probability += 0.05 if doc_mismatch else 0
        fraud_probability += 0.06 if device_fingerprint_mismatch else 0
        fraud_probability += 0.07 if ssn_velocity_group else 0
        fraud_probability += 0.03 if phone_tenure_days < 14 else 0
        fraud_probability += 0.05 if ip_risk_score > 82 else 0
        fraud_probability += 0.04 if name_match_score < 78 else 0
        confirmed_fraud = chance(min(fraud_probability, 0.75))

        baseline_reject = true_high_risk or (
            ip_risk_score > ACTIVE_IP_THRESHOLD and phone_tenure_days < ACTIVE_PHONE_TENURE_THRESHOLD
        )
        challenger_reject = (
            sanctions_hit
            or doc_mismatch
            or commercial_po_box
            or device_fingerprint_mismatch
            or bool(ssn_velocity_group)
            or (ip_risk_score > ACTIVE_IP_THRESHOLD + 4 and phone_tenure_days < 21)
            or name_match_score < ACTIVE_NAME_THRESHOLD - 9
        )

        vendor = random.choice(VENDORS)
        vendor_flagged = baseline_reject if vendor == "baseline_id" else challenger_reject
        vendor_latency_ms = int(random.gauss(610 if vendor == "baseline_id" else 540, 120))
        vendor_latency_ms += 230 if created_at >= datetime(2026, 3, 16) and vendor == "baseline_id" else 0
        vendor_match_rate = get_vendor_match_rate(vendor, week_start.date().isoformat(), created_at)

        engine_action = "manual_review" if vendor_flagged else "instant_approve"
        if glitch_window and engine_action == "manual_review" and (commercial_po_box or sanctions_hit):
            engine_action = "instant_approve"
        review_reason_codes = build_reason_codes(
            sanctions_hit,
            commercial_po_box,
            doc_mismatch,
            device_fingerprint_mismatch,
            ssn_velocity_group,
            phone_tenure_days,
            ip_risk_score,
            name_match_score,
        )

        if engine_action == "instant_approve":
            final_status = "approved"
            queue_minutes = 0
            drop_step = ""
        else:
            queue_minutes = max(8, int(random.gauss(330, 150)))
            final_status = weighted_choice([("approved", 48), ("rejected", 36), ("abandoned", 16)])
            drop_step = "" if final_status == "approved" else weighted_choice([
                ("doc_upload", 35), ("selfie_match", 25), ("address_check", 20), ("ssn_check", 20)
            ])

        active_balance = round(random.uniform(0, 3500), 2) if final_status == "approved" else 0
        chargeoff_amount = round(random.uniform(25, 1400), 2) if confirmed_fraud and final_status == "approved" else 0
        monitoring_trigger, monitoring_resolution_hours = monitoring_trigger_for(
            final_status, confirmed_fraud, active_balance, sanctions_hit
        )
        if monitoring_trigger:
            if sanctions_hit or monitoring_trigger == "sanctions_rescan_hit":
                re_review_outcome = weighted_choice([("sar_filed", 38), ("blocked", 32), ("escalated", 20), ("cleared", 10)])
            elif confirmed_fraud:
                re_review_outcome = weighted_choice([("blocked", 45), ("sar_filed", 25), ("escalated", 20), ("cleared", 10)])
            else:
                re_review_outcome = weighted_choice([("cleared", 68), ("escalated", 19), ("blocked", 9), ("sar_filed", 4)])
        else:
            re_review_outcome = ""

        kyc_ssn_present = not chance(0.006)
        kyc_ssn_verified = kyc_ssn_present and not bool(ssn_velocity_group) and not chance(0.018)
        kyc_address_verified = not commercial_po_box and not chance(0.024)
        kyc_dob_present = not chance(0.004)
        kyc_dob_verified = kyc_dob_present and not chance(0.011)
        kyc_selfie_match_passed = not doc_mismatch and not device_fingerprint_mismatch and not chance(0.019)
        sop_override = chance(0.045 if engine_action == "manual_review" else 0.008)
        missing_kyc_attribute = not all([
            kyc_ssn_present,
            kyc_ssn_verified,
            kyc_address_verified,
            kyc_dob_present,
            kyc_dob_verified,
            kyc_selfie_match_passed,
        ])

        yield {
            "application_id": f"APP-{i:06d}",
            "created_at": created_at.isoformat(timespec="seconds"),
            "week_start": week_start.date().isoformat(),
            "first_name": random.choice(FIRST_NAMES),
            "last_name": random.choice(LAST_NAMES),
            "state": random.choice(STATES),
            "device": device,
            "mobile_risk_profile": mobile_risk_profile,
            "vendor": vendor,
            "vendor_flagged": int(vendor_flagged),
            "vendor_latency_ms": max(120, vendor_latency_ms),
            "vendor_match_rate": round(max(0.45, min(0.99, vendor_match_rate)), 4),
            "commercial_po_box": int(commercial_po_box),
            "sanctions_hit": int(sanctions_hit),
            "doc_mismatch": int(doc_mismatch),
            "device_fingerprint_mismatch": int(device_fingerprint_mismatch),
            "ssn_velocity_group": ssn_velocity_group,
            "phone_tenure_days": phone_tenure_days,
            "ip_risk_score": ip_risk_score,
            "name_match_score": name_match_score,
            "engine_action": engine_action,
            "review_reason_codes": review_reason_codes,
            "final_status": final_status,
            "confirmed_fraud": int(confirmed_fraud),
            "queue_minutes": queue_minutes,
            "drop_step": drop_step,
            "active_balance": active_balance,
            "chargeoff_amount": chargeoff_amount,
            "monitoring_trigger": monitoring_trigger,
            "monitoring_resolution_hours": monitoring_resolution_hours,
            "re_review_outcome": re_review_outcome,
            "kyc_ssn_present": int(kyc_ssn_present),
            "kyc_ssn_verified": int(kyc_ssn_verified),
            "kyc_address_verified": int(kyc_address_verified),
            "kyc_dob_present": int(kyc_dob_present),
            "kyc_dob_verified": int(kyc_dob_verified),
            "kyc_selfie_match_passed": int(kyc_selfie_match_passed),
            "sop_override": int(sop_override),
            "missing_kyc_attribute": int(missing_kyc_attribute),
        }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic KYC lifecycle data.")
    parser.add_argument("--rows", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=326)
    parser.add_argument("--output", default="data/kyc_applications.csv")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(generate_rows(args.rows, args.seed))

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows):,} synthetic applications to {out_path}")


if __name__ == "__main__":
    main()
