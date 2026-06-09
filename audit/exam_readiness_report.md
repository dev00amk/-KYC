# Regulatory Examination and Control Self-Assessment

**Framework Version:** 2026.1.4  
**Regulatory Standards Alignment:** FFIEC BSA/AML Manual, FinCEN CIP Rule, Federal Reserve SR 11-7 Model Risk Management  
**Primary Audience:** Financial Crimes, Identity Risk, sponsor-bank compliance, vendor governance, and internal audit

## 1. Control Effectiveness Summary

This framework operates on an active identity-control model. Entry-point onboarding risks are detected, reason-coded, routed, and measured before application outcomes are treated as final. The system is designed to protect legitimate member conversion while preserving evidence trails for sanctions, CIP, vendor-risk, and model-risk review.

## 2. Institutional Control Matrix

| Control ID | Risk Vector | Programmatic Detection Mechanism | Fail-Safe Default Protocol |
| --- | --- | --- | --- |
| CTRL-KYC-001 | Synthetic identity fraud | SSN velocity profiling, document mismatch, device fingerprint mismatch, and name-match thresholds | Route to secondary out-of-band documentary review |
| CTRL-SAN-002 | Sanctions screening | `sanctions_hit` reason code and Tier 1 remediation classification | Soft-lock account ledger and trigger SAR review workflow |
| CTRL-DRF-003 | Vendor or model drift | Population Stability Index tracking and vendor-week match-rate monitoring | Notify Risk Strategy and initialize challenger cascade review |
| CTRL-OPS-004 | Manual-review fatigue | Rule precision, false-positive rate, API latency, and queue-burden scoring | Degrade, retune, or move noisy controls to step-up verification |
| CTRL-AUD-005 | Evidence completeness | Reason-code audit trail and attribute-level KYC completeness checks | Block audit packet closure until required evidence fields are complete |

## 3. Model Risk Management and Drift Thresholds

Identity vendor scores and decisioning signals are treated as model-risk inputs. Distribution movement is monitored using PSI:

- `PSI < 0.10`: Stable. Current onboarding thresholds remain valid.
- `0.10 <= PSI <= 0.25`: Moderate shift. Risk Strategy should review vendor inputs and threshold calibration.
- `PSI > 0.25`: Structural shift. Trigger immediate recalibration review and challenger routing assessment.

Evaluation cadence: rolling 168-hour review in production, represented in this repository by baseline/current cohort comparison.

## 4. Population Under Review

The Q1 2026 lookback population includes accounts instant-approved despite commercial P.O. Box or sanctions screening exceptions. The dashboard extract quantifies impacted accounts, active balance exposure, and chargeoff exposure.

Primary population filters:

- `engine_action = 'instant_approve'`
- `commercial_po_box = 1 OR sanctions_hit = 1`
- Application date within the simulated release defect window of 2026-01-15 through 2026-03-20

## 5. Remediation Status

| Tier | Action | Simulated Completion Rate | Evidence |
| --- | --- | ---: | --- |
| Tier 1 | SAR review and account block | 61% | Case export, sanctions-screening payload, disposition notes |
| Tier 2 | Freeze and step-up document request | 74% | Member outreach log, utility bill or address verification |
| Tier 3 | Low-friction database reverification | 89% | Background reverification result and audit evidence row |

## 6. Outstanding Items

| Item | Owner | Target Date | Status |
| --- | --- | --- | --- |
| Backfill raw sanctions payload IDs into the lookback evidence table | Data Engineering | 2026-04-18 | In progress |
| Complete QA sampling for Tier 2 step-up outcomes | Operations QA | 2026-04-22 | Open |
| Review challenger vendor false-negative rate after traffic shift | Vendor Governance | 2026-05-01 | Open |
