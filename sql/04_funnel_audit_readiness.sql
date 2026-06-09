-- Dashboard extract for onboarding funnel diagnostics and audit readiness metrics.

WITH funnel AS (
    SELECT
        device,
        COUNT(*) AS applications,
        SUM(CASE WHEN final_status = 'approved' THEN 1 ELSE 0 END) AS approved_accounts,
        SUM(CASE WHEN drop_step = 'ssn_check' THEN 1 ELSE 0 END) AS ssn_check_dropoffs,
        SUM(CASE WHEN drop_step = 'address_check' THEN 1 ELSE 0 END) AS address_check_dropoffs,
        SUM(CASE WHEN drop_step = 'doc_upload' THEN 1 ELSE 0 END) AS doc_upload_dropoffs,
        SUM(CASE WHEN drop_step = 'selfie_match' THEN 1 ELSE 0 END) AS selfie_match_dropoffs
    FROM kyc_applications
    GROUP BY device
),
audit_readiness AS (
    SELECT
        COUNT(*) AS applications,
        AVG(sop_override) AS sop_deviation_rate,
        AVG(missing_kyc_attribute) AS missing_kyc_attribute_rate,
        SUM(CASE WHEN commercial_po_box = 1 OR ofac_partial = 1 THEN 1 ELSE 0 END) AS high_risk_attribute_count
    FROM kyc_applications
)
SELECT
    funnel.*,
    approved_accounts * 1.0 / NULLIF(applications, 0) AS approval_rate,
    audit_readiness.sop_deviation_rate,
    audit_readiness.missing_kyc_attribute_rate,
    audit_readiness.high_risk_attribute_count
FROM funnel
CROSS JOIN audit_readiness
ORDER BY applications DESC;
