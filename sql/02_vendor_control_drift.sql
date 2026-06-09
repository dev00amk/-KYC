-- Champion/challenger vendor performance, false negatives, and control drift monitor.

WITH weekly_vendor AS (
    SELECT
        DATE_TRUNC('week', created_at) AS week_start,
        vendor,
        COUNT(*) AS applications,
        AVG(vendor_match_rate) AS match_rate,
        AVG(vendor_latency_ms) AS latency_ms,
        SUM(vendor_flagged) AS vendor_flags,
        SUM(confirmed_fraud) AS confirmed_fraud,
        SUM(CASE WHEN vendor_flagged = 1 AND confirmed_fraud = 0 THEN 1 ELSE 0 END) AS false_positives,
        SUM(CASE WHEN vendor_flagged = 0 AND confirmed_fraud = 1 THEN 1 ELSE 0 END) AS false_negatives
    FROM kyc_applications
    GROUP BY 1, 2
),
lagged AS (
    SELECT
        *,
        LAG(match_rate) OVER (PARTITION BY vendor ORDER BY week_start) AS prior_match_rate,
        LAG(latency_ms) OVER (PARTITION BY vendor ORDER BY week_start) AS prior_latency_ms
    FROM weekly_vendor
),
scored AS (
    SELECT
        *,
        false_positives * 1.0 / NULLIF(applications - confirmed_fraud, 0) AS false_positive_ratio,
        false_negatives * 1.0 / NULLIF(confirmed_fraud, 0) AS vendor_false_negative_rate,
        (match_rate - prior_match_rate) / NULLIF(prior_match_rate, 0) AS match_rate_change,
        (latency_ms - prior_latency_ms) / NULLIF(prior_latency_ms, 0) AS latency_change
    FROM lagged
)
SELECT
    *,
    CASE
        WHEN match_rate_change <= -0.15 THEN 'Control Drift Alert - match rate deterioration'
        WHEN latency_change >= 0.15 THEN 'Control Drift Alert - latency spike'
        ELSE 'Within tolerance'
    END AS drift_status,
    CASE
        WHEN vendor = 'baseline_id' AND (match_rate_change <= -0.15 OR latency_change >= 0.15)
            THEN 'Escalate SLA review; consider increasing challenger_id traffic share to 60%'
        WHEN match_rate_change <= -0.15 OR latency_change >= 0.15
            THEN 'Escalate vendor SLA review'
        ELSE 'No action'
    END AS recommended_action
FROM scored
ORDER BY week_start, vendor;
