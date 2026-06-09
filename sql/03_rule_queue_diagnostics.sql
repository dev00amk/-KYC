-- Rule threshold backtest for manual review volume, queue pressure, and fraud leakage.

WITH candidate_thresholds AS (
    SELECT 90 AS name_match_threshold, 75 AS ip_risk_threshold UNION ALL
    SELECT 87, 75 UNION ALL
    SELECT 83, 75 UNION ALL
    SELECT 83, 80 UNION ALL
    SELECT 83, 85 UNION ALL
    SELECT 80, 85
),
simulated AS (
    SELECT
        thresholds.name_match_threshold,
        thresholds.ip_risk_threshold,
        app.application_id,
        app.confirmed_fraud,
        app.queue_minutes,
        CASE
            WHEN app.name_match_score < thresholds.name_match_threshold
              OR app.ip_risk_score > thresholds.ip_risk_threshold
              OR app.phone_tenure_days < 30
              OR app.commercial_po_box = 1
              OR app.sanctions_hit = 1
              OR app.device_fingerprint_mismatch = 1
            THEN 1 ELSE 0
        END AS simulated_manual_review
    FROM kyc_applications app
    CROSS JOIN candidate_thresholds thresholds
),
baseline AS (
    SELECT COUNT(*) AS baseline_manual_reviews
    FROM kyc_applications
    WHERE engine_action = 'manual_review'
)
SELECT
    name_match_threshold,
    ip_risk_threshold,
    SUM(simulated_manual_review) AS simulated_manual_reviews,
    AVG(simulated_manual_review) AS manual_review_rate,
    SUM(CASE WHEN simulated_manual_review = 0 AND confirmed_fraud = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS fraud_leakage_rate,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY CASE WHEN simulated_manual_review = 1 THEN queue_minutes END) AS p95_queue_minutes,
    (MAX(baseline.baseline_manual_reviews) - SUM(simulated_manual_review)) * 0.22 * 34 AS estimated_monthly_savings
FROM simulated
CROSS JOIN baseline
GROUP BY name_match_threshold, ip_risk_threshold
ORDER BY fraud_leakage_rate, simulated_manual_reviews;
