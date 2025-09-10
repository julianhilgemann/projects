{{ config(materialized='table') }}

WITH months AS (
 
  SELECT DISTINCT obs_month AS month FROM {{ ref('stg_macro_yc_1y') }}
  UNION
  SELECT DISTINCT obs_month FROM {{ ref('stg_macro_yc_5y') }}
  UNION
  SELECT DISTINCT obs_month FROM {{ ref('stg_macro_yc_10y') }}
  UNION
  SELECT DISTINCT obs_month FROM {{ ref('stg_macro_yc_05y') }}
)
SELECT
  m.month,
  y05.yield_05y_pct,
  y1.yield_1y_pct,
  y5.yield_5y_pct,
  y10.yield_10y_pct
FROM months m
LEFT JOIN {{ ref('stg_macro_yc_05y') }}  y05   ON y05.obs_month = m.month
LEFT JOIN {{ ref('stg_macro_yc_1y') }}    y1   ON y1.obs_month   = m.month
LEFT JOIN {{ ref('stg_macro_yc_5y') }}    y5   ON y5.obs_month   = m.month
LEFT JOIN {{ ref('stg_macro_yc_10y') }}   y10  ON y10.obs_month  = m.month
ORDER BY m.month