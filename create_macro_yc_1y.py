# run_duck.py
import duckdb

con = duckdb.connect("data.duckdb")  # opens/creates DB in current folder

# Run arbitrary SQL (e.g., build tables)
con.execute("""
CREATE OR REPLACE TABLE macro_yc_1y AS
WITH src AS (
  SELECT *
  FROM read_csv(
    'data_raw\Zinsstrukturkurve_1_Y.csv',
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
""")