# Assumptions

This project uses synthetic data and scenario-calibrated assumptions. The values below are not empirical measurements.

| Assumption | Value | Why It Exists |
| --- | ---: | --- |
| Analyst handling time per manual review | 0.22 hours | Converts queue reduction into operating cost savings. Adjustable by operations staffing model. |
| Fully loaded analyst hourly cost | $34 | Portfolio assumption for loaded analyst cost. Replace with internal finance rate in production. |
| Release defect window | 2026-01-15 to 2026-03-20 | Simulates a decision-engine release gap that caused mandatory controls to be bypassed. |
| Commercial P.O. Box fraud lift | +0.08 | Calibrates the synthetic population toward realistic fraud concentration. |
| Sanctions hit fraud lift | +0.18 | Creates high-severity Tier 1 cases for sanctions and AML remediation workflow testing. |
| Device fingerprint mismatch fraud lift | +0.06 | Represents digital-native synthetic identity and account-opening fraud risk. |
| SSN velocity fraud lift | +0.07 | Simulates repeated identity use across applications within a short window. |
| Target synthetic fraud rate | Approximately 2% | Keeps the dataset plausible while preserving enough signal for backtesting. |
