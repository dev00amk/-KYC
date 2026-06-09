# Strategic Decision Memo: Identity and KYC Control Optimization

**To:** VP of Financial Crimes and Identity, Director of Risk Product
**From:** Principal Risk Analytics Lead
**Date:** June 9, 2026
**Subject:** Optimizing onboarding funnel efficiency while balancing KYC/AML fraud mitigation and member conversion
friction

## 1. Executive Summary

During hyper-growth periods, the tension between friction-free onboarding and defensive financial crime controls increases.
This memo outlines a data-driven framework designed to audit historical vulnerabilities, monitor live vendor degradation,
and actively tune onboarding thresholds.

By deploying advanced analytics, including Population Stability Index tracking, the framework can maintain strict
compliance expectations for fintech sponsor-bank programs such as The Bancorp Bank and Stride Bank while reducing
false-positive manual review queues by an estimated 18-22%.

## 2. Core Operational Challenges

### A. Manual Review Queue Fatigue

**Primary artifact:** `sql/03_rule_queue_diagnostics.sql`

Legacy KYC rules trigger static verification queues based on unoptimized risk weights. This creates operational backlog,
increases customer experience wait times, and reduces the conversion rate of legitimate applicants.

The strategic shift is to evaluate each control using both rule precision and trigger velocity. Rules with low
true-positive detection but high queue burden should be flagged for degradation, retuning, or movement into downstream
step-up challenges such as document or selfie verification.

### B. Vendor Performance Drift

**Primary artifacts:** `sql/02_vendor_control_drift.sql`, `sql/07_psi_feature_drift.sql`

Third-party identity verification vendors can update underlying data sources, matching logic, or model features without
materially useful release notes. A sudden drop in vendor match rate can either increase synthetic identity leakage or shut
down valid sign-ups.

The strategic shift is to establish strict baseline monitoring using Population Stability Index. Any score-distribution
shift where PSI is greater than 0.10 should trigger product and risk review before fraud losses appear downstream in
card-clearing, chargeback, or account abuse outcomes.

## 3. Analytical Framework Implementation Matrix

- `01_regulatory_lookback_audit.sql`: Compliance and Audit artifact for remediation cost, exposure windows, BSA/AML
  lookback orders, and FinCEN expectations.
- `02_vendor_control_drift.sql`: Product Engineering artifact for upstream conversion rate, vendor SLA, and Vendor Risk
  Management review.
- `03_rule_queue_diagnostics.sql`: Operations Strategy artifact for average handle time, queue burden, operational
  scalability, and member experience.
- `06_control_effectiveness_scorecard.sql`: Risk Finance artifact for unit fraud exposure, loss catch rate,
  fraud-to-sales ratio, and sponsor-bank risk appetite.
- `07_psi_feature_drift.sql`: Risk Data Science artifact for model performance, population shifts, Model Risk
  Management, and threshold governance.

## 4. Immediate Strategy Recommendations

1. Implement dynamic escalation cascades. If primary bureau matching fails due to address discrepancies, route the
   applicant through an optimized secondary vendor instead of defaulting directly to manual review.
2. Decommission top-heavy rules. Any rule with false positive rate above 85% and queue burden above 100 analyst hours
   per month should be reviewed for deprecation unless explicitly required by regulation or lookback terms.
3. Re-baseline score thresholds monthly. Use `sql/06_control_effectiveness_scorecard.sql` to capture emerging digital
   banking typologies such as synthetic identity clusters, SSN velocity, and device-fingerprint mismatch patterns.
4. Preserve sponsor-bank evidence trails. Each threshold change should include a decision memo, policy-log entry, PSI
   status, and before/after queue and fraud-leakage estimates.

## 5. Decision

Adopt the active policy configuration represented in the dashboard Rules tab:

- Name-match threshold: 83
- IP-risk threshold: 80
- Phone-tenure threshold: 30 days
- Sanctions hits: Tier 1 review
- Device fingerprint mismatch: manual review

This configuration should remain subject to monthly recalibration and immediate review if vendor match-rate drift, PSI
movement, or post-approval re-review outcomes exceed tolerance.

## 6. Strategic Core: Regulatory Hard Controls vs. Operational Friction Rules

The control framework separates absolute regulatory obligations from tunable operational-friction controls. Sanctions
screening, OFAC fuzzy matching at or above the 85% risk threshold, SSN integrity, and deterministic identity-attribute
failures remain hard controls with zero tolerance for automated bypass. If the regulatory layer is unavailable,
malformed, or breaching latency safety limits, the engine should fail closed into manual hold instead of sending the
applicant into a conversion-optimized path.

Champion/Challenger experimentation belongs only in the operational-friction layer: device fingerprinting, IP velocity,
behavioral biometrics, phone-tenure sensitivity, and secondary vendor routing. Those controls can be tuned using
precision, queue burden, Population Stability Index movement, and downstream confirmed-fraud leakage. This preserves
regulatory evidence quality while still giving product and risk teams a disciplined way to reduce unnecessary manual
review for legitimate customers.
