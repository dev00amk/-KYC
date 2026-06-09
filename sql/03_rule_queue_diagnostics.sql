-- Rule queue diagnostics and SLA friction analysis.
-- Business context: keep onboarding fast while isolating toxic, low-precision rules.

WITH rule_execution_events AS (
    SELECT
        application_id AS user_id,
        'R01_SANCTIONS_HIT' AS rule_id,
        'Sanctions hit' AS rule_name,
        sanctions_hit AS is_triggered,
        confirmed_fraud,
        final_status,
        vendor_latency_ms,
        queue_minutes * 60 AS manual_review_time_seconds
    FROM kyc_applications
    UNION ALL
    SELECT application_id, 'R02_PO_BOX_ADDRESS', 'Commercial PO Box address',
        commercial_po_box, confirmed_fraud, final_status, vendor_latency_ms, queue_minutes * 60
    FROM kyc_applications
    UNION ALL
    SELECT application_id, 'R03_DOC_MISMATCH', 'Document mismatch',
        doc_mismatch, confirmed_fraud, final_status, vendor_latency_ms, queue_minutes * 60
    FROM kyc_applications
    UNION ALL
    SELECT application_id, 'R04_DEVICE_FP_MISMATCH', 'Device fingerprint mismatch',
        device_fingerprint_mismatch, confirmed_fraud, final_status, vendor_latency_ms, queue_minutes * 60
    FROM kyc_applications
    UNION ALL
    SELECT application_id, 'R05_SSN_VELOCITY', 'SSN velocity',
        CASE WHEN ssn_velocity_group <> '' THEN 1 ELSE 0 END,
        confirmed_fraud, final_status, vendor_latency_ms, queue_minutes * 60
    FROM kyc_applications
    UNION ALL
    SELECT application_id, 'R06_PHONE_TENURE_LOW', 'Phone tenure below 30 days',
        CASE WHEN phone_tenure_days < 30 THEN 1 ELSE 0 END,
        confirmed_fraud, final_status, vendor_latency_ms, queue_minutes * 60
    FROM kyc_applications
    UNION ALL
    SELECT application_id, 'R07_IP_RISK_HIGH', 'IP risk score above 80',
        CASE WHEN ip_risk_score > 80 THEN 1 ELSE 0 END,
        confirmed_fraud, final_status, vendor_latency_ms, queue_minutes * 60
    FROM kyc_applications
    UNION ALL
    SELECT application_id, 'R08_NAME_MATCH_LOW', 'Name match below 83',
        CASE WHEN name_match_score < 83 THEN 1 ELSE 0 END,
        confirmed_fraud, final_status, vendor_latency_ms, queue_minutes * 60
    FROM kyc_applications
),
scored AS (
    SELECT
        rule_id,
        rule_name,
        COUNT(DISTINCT user_id) AS total_evaluations,
        SUM(is_triggered) AS total_triggers,
        SUM(CASE WHEN is_triggered = 1 AND confirmed_fraud = 1 THEN 1 ELSE 0 END) AS true_positive_triggers,
        SUM(CASE WHEN is_triggered = 1 AND confirmed_fraud = 0 THEN 1 ELSE 0 END) AS false_positive_triggers,
        AVG(vendor_latency_ms) AS avg_api_latency_ms,
        SUM(CASE WHEN is_triggered = 1 THEN manual_review_time_seconds ELSE 0 END) / 3600.0 AS total_queue_burden_hours
    FROM rule_execution_events
    GROUP BY rule_id, rule_name
)
SELECT
    rule_id,
    rule_name,
    total_evaluations,
    total_triggers,
    ROUND(false_positive_triggers * 100.0 / NULLIF(total_triggers, 0), 2) AS false_positive_rate_pct,
    ROUND(true_positive_triggers * 100.0 / NULLIF(total_triggers, 0), 2) AS precision_pct,
    ROUND(avg_api_latency_ms, 0) AS avg_api_latency_ms,
    ROUND(total_queue_burden_hours, 2) AS total_queue_burden_hours,
    CASE
        WHEN false_positive_triggers * 100.0 / NULLIF(total_triggers, 0) > 85
          AND total_queue_burden_hours > 100
            THEN 'Optimization candidate - degrade or step-up'
        WHEN avg_api_latency_ms > 900
            THEN 'Vendor SLA review'
        ELSE 'Monitor'
    END AS recommended_action
FROM scored
WHERE total_triggers > 50
ORDER BY total_queue_burden_hours DESC, avg_api_latency_ms DESC;
