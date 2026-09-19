-- Staging view over daily holdings, valued in CAD.
--
-- NOTE: this model is deliberately non-compliant. It is the dbt-flavoured review target for
-- the deployment-checklist skill built in Session 3, alongside the plain SQL in sql/deploy/.
-- Do not "fix" it before then.
--
-- Reading this file requires no dbt install --- Session 3 reviews it as text.

SELECT
    *
FROM CI_SANDBOX.DE_HOL_SHARED.HOLDINGS_DAILY h
LEFT JOIN CI_SANDBOX.DE_HOL_SHARED.PRICES_DAILY p
       ON p.SECURITY_ID = h.SECURITY_ID
      AND p.PRICE_DATE = h.AS_OF_DATE
LEFT JOIN CI_SANDBOX.DE_HOL_SHARED.FX_RATES_DAILY f
       ON f.FROM_CURRENCY = p.CURRENCY
      AND f.RATE_DATE = h.AS_OF_DATE
WHERE h.AS_OF_DATE >= '2025-01-01'
