# Technical Data Architecture and Schema Assumptions

This document defines the schema, system architecture, statistical assumptions, and synthetic-data calibration logic supporting the `-KYC` analytics warehouse project.

The project uses synthetic data. The values below are not empirical measurements from Chime, The Bancorp Bank, Stride Bank, Socure, Alloy, or any other production system.

## 1. Core Platform Assumptions and Data Pipelines

- **Database environment:** SQL is written for modern cloud data warehouses such as BigQuery, Snowflake, or Redshift, with minor syntax adaptation for date and percentile functions.
- **Temporal tracking:** Event logs are assumed to use UTC timestamps. Onboarding cohorts are partitioned by application date to support performant queries across high-volume registration attempts.
- **Idempotency:** Operational logs are append-only and keyed by deterministic identifiers such as `application_id`, `user_id`, `event_id`, and `session_id`.
- **Decision auditability:** Every onboarding decision has reason-code evidence. Clean approvals use `review_reason_codes = 'CLEAN'`; risk-triggered decisions use pipe-delimited reason codes.
- **Vendor governance:** Identity vendor performance is monitored at a vendor-week level because match rate is a property of vendor coverage against the population, not an independent transaction-level random variable.

## 2. Table-Level Schema Definitions

### A. `chime_risk_analytics.member_onboarding_profiles`

Tracks primary registration and identity attributes submitted at application kickoff.

- `user_id` (STRING, primary key): Unique applicant identifier.
- `application_id` (STRING): Unique onboarding application identifier.
- `kyc_vendor_score` (NUMERIC): Normalized risk score between `0.00` and `1.00`.
- `assigned_risk_tier` (STRING): Risk tier assigned at point of entry: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
- `device` (STRING): Onboarding channel such as `ios`, `android`, or `web`.
- `mobile_risk_profile` (STRING): Derived channel-risk segment used for digital banking onboarding diagnostics.

### B. `chime_risk_analytics.kyc_rule_execution_events`

Stores the audit trail of individual compliance and fraud rules executed during the onboarding cascade.

- `rule_id` (STRING): Unique identifier for the logic statement, such as `R05_SSN_VELOCITY`.
- `is_triggered` (INTEGER): Binary indicator where `1` means triggered and `0` means passed.
- `review_reason_codes` (STRING): Pipe-delimited decision reason trail used for queue diagnostics and audit evidence.
- `vendor_latency_ms` (INTEGER): API response time in milliseconds, used for vendor SLA degradation monitoring.

### C. `chime_risk_analytics.kyc_manual_review_dispositions`

Stores operations decisions for accounts routed to manual review.

- `review_disposition` (STRING): Human-review outcome. Expected values include `CONFIRMED_FRAUD`, `FALSE_POSITIVE_APPROVE`, `DISMISSED`, `ESCALATED`, and `SAR_FILED`.
- `review_started_at` (TIMESTAMP): Manual review start timestamp.
- `review_completed_at` (TIMESTAMP): Manual review completion timestamp.
- `analyst_queue_minutes` (INTEGER): Time spent waiting or being worked in the review queue.

### D. `chime_risk_analytics.transaction_chargebacks`

Stores downstream ledger entries representing realized financial fraud losses.

- `chargeback_amount` (NUMERIC): Fiat loss sustained by the platform.
- `fraud_type` (STRING): Classification such as `IDENTITY_THEFT`, `SYNTHETIC_FRAUD`, or `ACCOUNT_TAKEOVER_ONBOARDING`.
- `detected_at` (TIMESTAMP): Detection timestamp used to connect onboarding controls to post-approval outcomes.

### E. `chime_risk_analytics.ongoing_monitoring_events`

Stores lifecycle re-review triggers after initial onboarding approval.

- `monitoring_trigger` (STRING): Trigger type such as `chargeback_dispute`, `velocity_flag`, `address_change_30d`, or `sanctions_rescan_hit`.
- `re_review_outcome` (STRING): Outcome such as `cleared`, `blocked`, `escalated`, or `sar_filed`.
- `monitoring_resolution_hours` (NUMERIC): Time from trigger detection to disposition.

## 3. Statistical Baseline Metrics

Population Stability Index:

```text
PSI = sum((actual_pct - expected_pct) * ln(actual_pct / expected_pct))
```

- `PSI < 0.10`: Minimal shift; current onboarding thresholds are considered stable.
- `0.10 <= PSI <= 0.25`: Moderate shift; triggers advisory review of vendor inputs and score distributions.
- `PSI > 0.25`: Significant shift; requires threshold recalibration review to protect downstream product ecosystems.

## 4. Synthetic Calibration Assumptions

| Assumption | Value | Why it exists |
| --- | ---: | --- |
| Analyst handling time per manual review | 0.22 hours | Converts queue reduction into operating cost savings. Adjustable by operations staffing model. |
| Fully loaded analyst hourly cost | $34 | Portfolio assumption for loaded analyst cost. Replace with internal finance rate in production. |
| Release defect window | 2026-01-15 to 2026-03-20 | Simulates a decision-engine release gap that caused mandatory controls to be bypassed. |
| Commercial P.O. Box fraud lift | +0.08 | Calibrates the synthetic population toward realistic fraud concentration. |
| Sanctions hit fraud lift | +0.18 | Creates high-severity Tier 1 cases for sanctions and AML remediation workflow testing. |
| Device fingerprint mismatch fraud lift | +0.06 | Represents digital-native synthetic identity and account-opening fraud risk. |
| SSN velocity fraud lift | +0.07 | Simulates repeated identity use across applications within a short window. |
| Target synthetic fraud rate | Approximately 2% | Keeps the dataset plausible while preserving enough signal for backtesting. |
| Tier 1 completion rate | 61% | Simulates slower SAR and sanctions review completion due to evidence collection and filing-clock complexity. |
| Tier 2 completion rate | 74% | Simulates step-up document collection and operations QA throughput. |
| Tier 3 completion rate | 89% | Simulates lower-friction reverification workflows with higher completion. |
| PSI thresholds | 0.10 and 0.25 | Common model-risk monitoring convention: below 0.10 stable, 0.10-0.25 investigate, above 0.25 recalibrate. |
