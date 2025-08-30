# run_duck.py
import duckdb
from pathlib import Path

HERE = Path(__file__).resolve().parent
# One folder above the script
DB_PATH = (HERE / ".." / "data.duckdb").resolve()

con = duckdb.connect(str(DB_PATH)) 

# Run arbitrary SQL (e.g., build tables)
con.execute("""
-- Stitch monthly yields into one wide table
CREATE OR REPLACE TABLE macro_yc_all AS
WITH
y05 AS (
  SELECT DISTINCT obs_month::DATE AS m, value::DOUBLE AS y_0_5y
  FROM macro_yc_05y
),
y1 AS (
  SELECT DISTINCT obs_month::DATE AS m, value::DOUBLE AS y_1y
  FROM macro_yc_1y
),
y5 AS (
  SELECT DISTINCT obs_month::DATE AS m, value::DOUBLE AS y_5y
  FROM macro_yc_5y
),
y10 AS (
  SELECT DISTINCT obs_month::DATE AS m, value::DOUBLE AS y_10y
  FROM macro_yc_10y
),
months AS (              -- master month list from all series
  SELECT m FROM y05
  UNION
  SELECT m FROM y1
  UNION
  SELECT m FROM y5
  UNION
  SELECT m FROM y10
)
SELECT
  months.m AS obs_month,
  y05.y_0_5y,
  y1.y_1y,
  y5.y_5y,
  y10.y_10y
FROM months
LEFT JOIN y05  ON y05.m  = months.m
LEFT JOIN y1   ON y1.m   = months.m
LEFT JOIN y5   ON y5.m   = months.m
LEFT JOIN y10  ON y10.m  = months.m
ORDER BY obs_month;              
""")

print(con.sql("""
Select * from macro_yc_all
"""))