-- Ongoing monitoring trigger diagnostics across the post-approval lifecycle.

WITH approved_accounts AS (
    SELECT *
    FROM kyc_applications
    WHERE final_status = 'approved'
),
triggered AS (
    SELECT
        monitoring_trigger,
        COUNT(*) AS triggered_accounts,
        AVG(monitoring_resolution_hours) AS avg_resolution_hours,
        SUM(CASE WHEN confirmed_fraud = 1 THEN 1 ELSE 0 END) AS confirmed_fraud_accounts,
        SUM(CASE WHEN commercial_po_box = 1 OR sanctions_hit = 1 OR device_fingerprint_mismatch = 1 THEN 1 ELSE 0 END) AS prior_onboarding_flag_count
    FROM approved_accounts
    WHERE monitoring_trigger <> ''
    GROUP BY monitoring_trigger
),
approved_total AS (
    SELECT COUNT(*) AS approved_accounts
    FROM approved_accounts
)
SELECT
    triggered.monitoring_trigger,
    triggered.triggered_accounts,
    triggered.triggered_accounts * 1.0 / approved_total.approved_accounts AS re_review_rate,
    triggered.avg_resolution_hours,
    triggered.confirmed_fraud_accounts,
    triggered.prior_onboarding_flag_count,
    triggered.prior_onboarding_flag_count * 1.0 / NULLIF(triggered.triggered_accounts, 0) AS prior_flag_predictive_share
FROM triggered
CROSS JOIN approved_total
ORDER BY triggered_accounts DESC;
