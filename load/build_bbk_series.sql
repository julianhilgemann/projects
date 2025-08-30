CREATE OR REPLACE TABLE bbk_series AS
WITH src AS (
  SELECT *
  FROM read_csv(
    'data_raw\BBSIS.M.I.ZST.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A (1).csv',
    delim=';', header=false
  )
),
filtered AS (
  SELECT
    try_strptime(column0, '%Y-%m')         AS month_raw,
    replace(column1, ',', '.')             AS value_str
  FROM src
  WHERE regexp_matches(column0, '^[0-9]{4}-[0-9]{2}$')   -- keep only YYYY-MM rows
    AND regexp_matches(column1, '^-?[0-9]+([.,][0-9]+)?$')  -- keep only numeric values
)
SELECT
  month_raw::date                          AS obs_month,
  value_str::DOUBLE                        AS value
FROM filtered
ORDER BY obs_month;