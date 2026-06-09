# Exam Readiness Report

## 1. Control Inventory

| Control | Threshold | Last Calibration Date | Owner |
| --- | --- | --- | --- |
| Sanctions screening | Any sanctions hit routes to Tier 1 review | 2026-04-01 | AML Compliance |
| Name-match tolerance | Manual review below 83 | 2026-04-01 | Identity Risk Strategy |
| IP-risk threshold | Manual review above 80 | 2026-04-01 | Fraud Decisioning |
| Phone tenure | Manual review below 30 days | 2026-03-15 | Identity Risk Strategy |
| Device fingerprint mismatch | Manual review when mismatch is present | 2026-04-01 | Fraud Engineering |
| Vendor drift monitor | Alert at 15% match-rate drop or latency spike | 2026-03-22 | Vendor Governance |

## 2. Population Under Review

The Q1 2026 lookback population includes accounts instant-approved despite commercial P.O. Box or sanctions screening exceptions. The dashboard extract quantifies impacted accounts, active balance exposure, and chargeoff exposure.

Primary population filters:

- `engine_action = 'instant_approve'`
- `commercial_po_box = 1 OR sanctions_hit = 1`
- Application date within the simulated release defect window of 2026-01-15 through 2026-03-20

## 3. Remediation Status

| Tier | Action | Simulated Completion Rate | Evidence |
| --- | --- | ---: | --- |
| Tier 1 | SAR review and account block | 62% | Case export, sanctions-screening payload, disposition notes |
| Tier 2 | Freeze and step-up document request | 73% | Member outreach log, utility bill or address verification |
| Tier 3 | Low-friction database reverification | 84% | Background reverification result and audit evidence row |

## 4. Outstanding Items

| Item | Owner | Target Date | Status |
| --- | --- | --- | --- |
| Backfill raw sanctions payload IDs into the lookback evidence table | Data Engineering | 2026-04-18 | In progress |
| Complete QA sampling for Tier 2 step-up outcomes | Operations QA | 2026-04-22 | Open |
| Review challenger vendor false-negative rate after traffic shift | Vendor Governance | 2026-05-01 | Open |
