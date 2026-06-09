# KYC Risk Control Health

This project is a portfolio-grade risk analytics build for an Identity and KYC analyst role. It models the kind of work a fintech risk team needs when onboarding systems change, identity vendors drift, and fraud rules create operational queue pressure.

The project uses synthetic data only. The scenario, metrics, and remediation tiers are intentionally realistic, but no customer or company data is included.

## What It Demonstrates

- Regulatory lookback audit: finds instant approvals that bypassed commercial P.O. Box or partial OFAC controls.
- Remediation framework: buckets impacted accounts into SAR review, step-up verification, or background reverification tiers.
- Vendor champion/challenger monitoring: tracks weekly match-rate, latency, and false-positive-ratio drift.
- Rule threshold simulation: backtests name-match, IP-risk, and phone-tenure thresholds against manual review volume and fraud leakage.
- Audit readiness reporting: summarizes SOP override rates and missing KYC attributes for partner-bank or internal audit review.

## Project Structure

```text
data/
  kyc_applications.csv          Synthetic onboarding and vendor payload extract
dashboard/
  index.html                    Static executive dashboard
  dashboard_data.json           Dashboard-ready analytics extract
scripts/
  generate_synthetic_data.py    Reproducible synthetic data generator
  risk_analytics.py             Lookback, drift, funnel, and threshold analytics
sql/
  01_regulatory_lookback_audit.sql
  02_vendor_control_drift.sql
  03_rule_queue_diagnostics.sql
  04_funnel_audit_readiness.sql
```

## Run Locally

From this folder:

```powershell
python scripts/generate_synthetic_data.py --rows 8000
python scripts/risk_analytics.py
python -m http.server 8080 --directory dashboard
```

Then open `http://localhost:8080`.

If Python is not on PATH, use the bundled Codex runtime path shown in the workspace dependency output.

## Interview Walkthrough

Open with the risk-control framing:

> I designed this as a control health system, not a generic growth dashboard. It assumes KYC platforms fail in three ordinary ways: release defects create lookback populations, third-party identity vendors drift, and rules become over-sensitive as fraud patterns shift.

Then walk through the tabs:

1. Overview: shows conversion, manual review load, fraud rate, queue health, SOP deviation, and KYC completeness.
2. Lookback: quantifies bypassed mandatory controls and assigns remediation actions.
3. Vendors: compares baseline and challenger identity providers for match reliability, latency, and false positives.
4. Rules: shows which controls create the most operational noise and which threshold settings reduce queues with controlled leakage.
5. Audit: translates analytics into evidence a risk director, bank partner, or internal audit team can use.

## Decision Example

The threshold simulation is designed to support a concrete operating recommendation:

> Lowering name-match tolerance from 90 to 83 while increasing IP-risk tolerance to 80 reduces manual reviews while keeping fraud leakage inside the team's risk appetite. The decision is paired with weekly vendor drift monitoring so future performance drops do not remain invisible.

## SQL Notes

The SQL files are written in portable warehouse-style SQL. In a production environment, I would adapt `DATE_TRUNC` and percentile syntax to the target warehouse, connect `vendor_payload_logs` to the raw API response store, and persist lookback outputs into a case-management or audit evidence table.
