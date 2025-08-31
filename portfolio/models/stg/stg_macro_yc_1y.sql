{{ config(materialized='table') }}

WITH src AS (
  SELECT * FROM read_csv('data_raw/Zinsstrukturkurve_1_Y.csv', delim=';', header=false)
),
filtered AS (
  SELECT
    try_strptime(column0, '%Y-%m') AS month_raw,
    replace(column1, ',', '.')     AS value_str
  FROM src
  WHERE regexp_matches(column0, '^[0-9]{4}-[0-9]{2}$')
    AND regexp_matches(column1, '^-?[0-9]+([.,][0-9]+)?$')
)
SELECT
  month_raw::date   AS obs_month,
  value_str::DOUBLE AS yield_1y_pct
FROM filtered
WHERE month_raw IS NOT NULL
ORDER BY obs_month