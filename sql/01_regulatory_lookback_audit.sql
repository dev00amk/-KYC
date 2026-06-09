-- Regulatory lookback audit for instant approvals with KYC and sanctions exceptions.
-- Dialect: warehouse-friendly ANSI SQL; adapt date functions for Snowflake/BigQuery/Redshift.

WITH application_base AS (
    SELECT
        application_id,
        created_at,
        vendor,
        engine_action,
        final_status,
        commercial_po_box,
        sanctions_hit,
        active_balance,
        chargeoff_amount,
        confirmed_fraud
    FROM production_applications
    WHERE created_at >= DATE '2026-01-01'
      AND created_at < DATE '2026-04-01'
),
vendor_flags AS (
    SELECT
        application_id,
        MAX(CASE WHEN payload_key = 'address_type' AND payload_value = 'commercial_po_box' THEN 1 ELSE 0 END) AS vendor_po_box_flag,
        MAX(CASE WHEN payload_key = 'sanctions_result' AND payload_value IN ('partial_match', 'possible_match') THEN 1 ELSE 0 END) AS vendor_sanctions_hit
    FROM vendor_payload_logs
    WHERE created_at >= DATE '2026-01-01'
      AND created_at < DATE '2026-04-01'
    GROUP BY application_id
),
control_bypasses AS (
    SELECT
        app.application_id,
        app.created_at,
        app.vendor,
        app.active_balance,
        app.chargeoff_amount,
        app.confirmed_fraud,
        COALESCE(flags.vendor_po_box_flag, app.commercial_po_box) AS po_box_flag,
        COALESCE(flags.vendor_sanctions_hit, app.sanctions_hit) AS sanctions_hit_flag
    FROM application_base app
    LEFT JOIN vendor_flags flags USING (application_id)
    WHERE app.engine_action = 'instant_approve'
      AND (
          COALESCE(flags.vendor_po_box_flag, app.commercial_po_box) = 1
          OR COALESCE(flags.vendor_sanctions_hit, app.sanctions_hit) = 1
      )
),
remediation_tiers AS (
    SELECT
        *,
        CASE
            WHEN sanctions_hit_flag = 1 OR confirmed_fraud = 1 OR chargeoff_amount > 0
                THEN 'Tier 1 - SAR review and account block'
            WHEN po_box_flag = 1 AND active_balance > 250
                THEN 'Tier 2 - freeze and step-up document request'
            ELSE 'Tier 3 - low-friction database re-verification'
        END AS remediation_tier
    FROM control_bypasses
)
SELECT
    remediation_tier,
    COUNT(*) AS impacted_accounts,
    SUM(active_balance) AS active_balance_exposure,
    SUM(chargeoff_amount) AS chargeoff_exposure,
    MIN(created_at) AS first_impacted_at,
    MAX(created_at) AS last_impacted_at
FROM remediation_tiers
GROUP BY remediation_tier
ORDER BY impacted_accounts DESC;
