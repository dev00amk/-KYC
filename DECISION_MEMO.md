# Decision Memo

TO: Head of Risk Strategy  
FROM: Identity Risk Analyst  
RE: Name-Match Threshold Optimization - Q1 2026  
DATE: 2026-04-01

## Recommendation

Lower name-match tolerance from 90 to 83 while raising the IP-risk threshold to 80. Projected impact: reduce manual review volume by 18% while increasing fraud leakage by 0.3 percentage points, which remains inside the stated risk appetite.

## Supporting Analysis

The rule simulation shows that current thresholds create excess manual-review queues without proportional fraud capture. The strongest friction drivers are low phone tenure, high IP-risk scores, and strict name matching. Device-channel analysis also shows web onboarding carries higher average IP-risk than iOS and Android, supporting a mobile-first risk profile rather than a uniform threshold across all channels.

The dashboard Rules tab contains the simulation grid and active policy panel. The Vendors tab should be reviewed before production rollout because vendor match-rate drift can change the leakage profile.

## Dependencies

- Compliance sign-off on the policy change.
- Engineering configuration update to decisioning thresholds.
- Operations staffing plan for residual Tier 1 sanctions and SAR review queues.
- Weekly vendor SLA monitoring during the first 30 days after rollout.

## Risk

If `challenger_id` match rate continues to degrade, fraud leakage may exceed tolerance by Q3. Recommend monthly threshold review and immediate SLA escalation when match rate drops or latency spikes by more than 15%.
