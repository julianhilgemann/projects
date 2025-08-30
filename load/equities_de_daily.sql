CREATE OR REPLACE TABLE equities_daily AS
SELECT
  CAST("date" AS DATE)                         AS dt,
  UPPER(ticker)                                AS ticker,
  CAST(ROUND(CAST(Close_EUR AS DOUBLE), 2) AS DECIMAL(18,2)) AS price_close_eur
FROM read_csv_auto(
  '\data_raw\equities_de_daily.csv'
)
WHERE "date" IS NOT NULL AND ticker IS NOT NULL;
