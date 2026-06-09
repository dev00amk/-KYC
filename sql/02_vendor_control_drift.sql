-- Champion/challenger vendor performance and control drift monitor.

WITH weekly_vendor AS (
    SELECT
        DATE_TRUNC('week', created_at) AS week_start,
        vendor,
        COUNT(*) AS applications,
        AVG(vendor_match_rate) AS match_rate,
        AVG(vendor_latency_ms) AS latency_ms,
        SUM(vendor_flagged) AS vendor_flags,
        SUM(confirmed_fraud) AS confirmed_fraud
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
        (vendor_flags - confirmed_fraud) * 1.0 / NULLIF(vendor_flags, 0) AS false_positive_ratio,
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
    END AS drift_status
FROM scored
ORDER BY week_start, vendor;
