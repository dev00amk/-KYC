# KYC Risk Control Health

This project is a portfolio-grade control framework for an Identity and KYC analyst role. It models the kind of work a fintech risk team needs when onboarding systems change, identity vendors drift, fraud rules create operational queue pressure, and post-approval monitoring reveals new customer lifecycle risk.

The project uses synthetic data only. The scenario, metrics, remediation tiers, and governance artifacts are intentionally realistic, but no customer or company data is included.

## Control Framework

- Onboarding controls: KYC decisioning, document mismatch, phone tenure, name-match tolerance, IP-risk, commercial P.O. Box detection, device fingerprint mismatch, and SSN velocity.
- Ongoing monitoring: post-approval triggers for chargeback disputes, velocity flags, address changes, and sanctions rescans.
- Vendor governance: champion/challenger monitoring for identity vendors, including match-rate drift, latency, false positive ratio, and vendor false negative rate.
- Audit readiness: remediation tiers, management response artifacts, policy logs, documented assumptions, and exam-ready control inventory.

Device channel risk profiling reflects the mobile-first onboarding environment of digital banking platforms. The synthetic model treats iOS and Android traffic as more predictable than web sessions and surfaces device-level manual review and fraud rates.

## Financial Crime Typologies Represented

- New account fraud
- Synthetic identity
- Sanctions screening and OFAC-style partial matches
- Structuring and velocity-based signals
- Device fingerprint mismatch
- Reused identity attributes across applications within 30 days

## Project Structure

```text
audit/
  exam_readiness_report.md      Management response and exam readiness artifact
data/
  kyc_applications.csv          Synthetic onboarding, vendor, and monitoring extract
dashboard/
  index.html                    Static executive dashboard
  dashboard_data.json           Dashboard-ready analytics extract
scripts/
  generate_synthetic_data.py    Reproducible synthetic data generator
  risk_analytics.py             Lookback, drift, funnel, monitoring, and threshold analytics
sql/
  01_regulatory_lookback_audit.sql
  02_vendor_control_drift.sql
  03_rule_queue_diagnostics.sql
  04_funnel_audit_readiness.sql
  05_ongoing_monitoring_triggers.sql
tests/
  test_analytics.py             Unit tests for core analytics behavior
ASSUMPTIONS.md                  Magic-number documentation
DECISION_MEMO.md                Internal recommendation memo
POLICY_LOG.md                   Threshold change-management trail
```

## Run Locally

From this folder:

```powershell
python scripts/generate_synthetic_data.py --rows 8000
python scripts/risk_analytics.py
python -m unittest discover -s tests
python -m http.server 8080 --directory dashboard
```

Then open `http://localhost:8080`.

If Python is not on PATH, use the bundled Codex runtime path shown in the workspace dependency output.

## Interview Walkthrough

Open with the risk-control framing:

> I designed this as a lifecycle control system, not a generic analytics dashboard. It assumes KYC platforms fail in ordinary ways: release defects create lookback populations, third-party identity vendors drift, decisioning thresholds need policy governance, and post-approval monitoring can surface risk that was invisible at onboarding.

Then walk through the artifacts:

1. Dashboard Overview: conversion, manual review load, fraud rate, queue health, SOP deviation, and KYC completeness.
2. Lookback: accounts bypassing mandatory address or sanctions controls, with remediation tiers.
3. Sanctions Screening: hit rate, false positive rate, Tier 1 count, and SAR-referral timing proxy.
4. Vendors: baseline vs. challenger identity provider health, including false negative rate and recommended action.
5. Rules: current policy plus simulations showing queue and leakage tradeoffs.
6. Monitoring: post-approval trigger rates and whether onboarding flags predicted lifecycle risk.
7. Audit Artifacts: decision memo, policy log, assumptions, and exam readiness report.

## Decision Example

The threshold simulation supports a concrete operating recommendation:

> Lowering name-match tolerance from 90 to 83 while increasing IP-risk tolerance to 80 reduces manual reviews while keeping fraud leakage inside the team's risk appetite. The decision is paired with weekly vendor drift monitoring so future performance drops do not remain invisible.

## SQL Notes

The SQL files are written in portable warehouse-style SQL. In a production environment, I would adapt `DATE_TRUNC` and percentile syntax to the target warehouse, connect `vendor_payload_logs` to the raw API response store, and persist lookback outputs into a case-management or audit evidence table.
