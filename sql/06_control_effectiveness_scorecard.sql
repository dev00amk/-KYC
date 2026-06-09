-- Control effectiveness scorecard: ranks each rule by precision, recall, and leakage cost.
-- Used to support threshold change decisions and quarterly policy reviews.

WITH rule_hits AS (
    SELECT
        application_id,
        confirmed_fraud,
        CASE WHEN sanctions_hit = 1 THEN 1 ELSE 0 END AS r01_sanctions,
        CASE WHEN commercial_po_box = 1 THEN 1 ELSE 0 END AS r02_po_box,
        CASE WHEN doc_mismatch = 1 THEN 1 ELSE 0 END AS r03_doc_mismatch,
        CASE WHEN device_fingerprint_mismatch = 1 THEN 1 ELSE 0 END AS r04_device_fp,
        CASE WHEN ssn_velocity_group <> '' THEN 1 ELSE 0 END AS r05_ssn_velocity,
        CASE WHEN phone_tenure_days < 30 THEN 1 ELSE 0 END AS r06_phone_tenure,
        CASE WHEN ip_risk_score > 80 THEN 1 ELSE 0 END AS r07_ip_risk,
        CASE WHEN name_match_score < 83 THEN 1 ELSE 0 END AS r08_name_match
    FROM kyc_applications
),
totals AS (
    SELECT
        COUNT(*) AS total_apps,
        SUM(confirmed_fraud) AS total_fraud,
        COUNT(*) - SUM(confirmed_fraud) AS total_non_fraud
    FROM kyc_applications
),
unpivoted AS (
    SELECT 'R01 Sanctions Hit' AS rule_name, r01_sanctions AS hit, confirmed_fraud FROM rule_hits UNION ALL
    SELECT 'R02 PO Box Address', r02_po_box, confirmed_fraud FROM rule_hits UNION ALL
    SELECT 'R03 Doc Mismatch', r03_doc_mismatch, confirmed_fraud FROM rule_hits UNION ALL
    SELECT 'R04 Device FP Mismatch', r04_device_fp, confirmed_fraud FROM rule_hits UNION ALL
    SELECT 'R05 SSN Velocity', r05_ssn_velocity, confirmed_fraud FROM rule_hits UNION ALL
    SELECT 'R06 Phone Tenure < 30d', r06_phone_tenure, confirmed_fraud FROM rule_hits UNION ALL
    SELECT 'R07 IP Risk > 80', r07_ip_risk, confirmed_fraud FROM rule_hits UNION ALL
    SELECT 'R08 Name Match < 83', r08_name_match, confirmed_fraud FROM rule_hits
)
SELECT
    u.rule_name,
    SUM(u.hit) AS total_hits,
    SUM(u.hit) * 1.0 / t.total_apps AS hit_rate,
    SUM(CASE WHEN u.hit = 1 AND u.confirmed_fraud = 1 THEN 1 ELSE 0 END) * 1.0
        / NULLIF(SUM(u.hit), 0) AS precision_rate,
    SUM(CASE WHEN u.hit = 1 AND u.confirmed_fraud = 1 THEN 1 ELSE 0 END) * 1.0
        / NULLIF(t.total_fraud, 0) AS recall_rate,
    SUM(CASE WHEN u.hit = 1 AND u.confirmed_fraud = 0 THEN 1 ELSE 0 END) * 1.0
        / NULLIF(t.total_non_fraud, 0) AS false_positive_rate,
    SUM(CASE WHEN u.hit = 1 AND u.confirmed_fraud = 1 THEN 1 ELSE 0 END) AS fraud_caught,
    SUM(CASE WHEN u.hit = 1 AND u.confirmed_fraud = 0 THEN 1 ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN u.hit = 1 AND u.confirmed_fraud = 1 THEN 1 ELSE 0 END), 1) AS noise_ratio
FROM unpivoted u
CROSS JOIN totals t
GROUP BY u.rule_name, t.total_apps, t.total_fraud, t.total_non_fraud
ORDER BY recall_rate DESC;
