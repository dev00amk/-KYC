-- Population Stability Index for key decisioning features.
-- PSI < 0.10 = stable | 0.10-0.25 = investigate | > 0.25 = recalibrate

WITH feature_values AS (
    SELECT 'ip_risk_score' AS feature, ip_risk_score * 1.0 AS feature_value, created_at FROM kyc_applications UNION ALL
    SELECT 'name_match_score', name_match_score * 1.0, created_at FROM kyc_applications UNION ALL
    SELECT 'phone_tenure_days', phone_tenure_days * 1.0, created_at FROM kyc_applications UNION ALL
    SELECT 'vendor_latency_ms', vendor_latency_ms * 1.0, created_at FROM kyc_applications
),
date_split AS (
    SELECT
        feature,
        feature_value,
        CASE WHEN created_at < DATE '2026-02-15' THEN 'baseline' ELSE 'current' END AS period
    FROM feature_values
),
ranges AS (
    SELECT feature, MIN(feature_value) AS min_value, MAX(feature_value) AS max_value
    FROM date_split
    GROUP BY feature
),
binned AS (
    SELECT
        d.feature,
        d.period,
        CASE
            WHEN r.max_value = r.min_value THEN 0
            ELSE FLOOR((d.feature_value - r.min_value) / NULLIF((r.max_value - r.min_value) / 10.0, 0))
        END AS bin_id,
        COUNT(*) AS cnt
    FROM date_split d
    JOIN ranges r USING (feature)
    GROUP BY 1, 2, 3
),
totals AS (
    SELECT feature, period, SUM(cnt) AS total
    FROM binned
    GROUP BY 1, 2
),
pcts AS (
    SELECT
        b.feature,
        b.bin_id,
        MAX(CASE WHEN b.period = 'baseline' THEN b.cnt * 1.0 / t.total END) AS base_pct,
        MAX(CASE WHEN b.period = 'current' THEN b.cnt * 1.0 / t.total END) AS curr_pct
    FROM binned b
    JOIN totals t USING (feature, period)
    GROUP BY 1, 2
),
psi AS (
    SELECT
        feature,
        SUM(
            (COALESCE(curr_pct, 0.0001) - COALESCE(base_pct, 0.0001))
            * LN(COALESCE(curr_pct, 0.0001) / NULLIF(COALESCE(base_pct, 0.0001), 0))
        ) AS psi
    FROM pcts
    GROUP BY feature
)
SELECT
    feature,
    ROUND(psi, 4) AS psi,
    CASE
        WHEN psi < 0.10 THEN 'Stable'
        WHEN psi < 0.25 THEN 'Moderate Shift - Investigate'
        ELSE 'Major Shift - Recalibrate Thresholds'
    END AS status
FROM psi
ORDER BY psi DESC;
