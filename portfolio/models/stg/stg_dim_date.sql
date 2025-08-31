{{ config(materialized='table') }}

WITH
-- Easter Sunday dates (1970–2049)
easter_sunday(year_actual, day_actual) AS (
    VALUES
    (1970, DATE '1970-03-29'), (1971, DATE '1971-04-11'), (1972, DATE '1972-04-02'),
    (1973, DATE '1973-04-22'), (1974, DATE '1974-04-14'), (1975, DATE '1975-03-30'),
    (1976, DATE '1976-04-18'), (1977, DATE '1977-04-10'), (1978, DATE '1978-03-26'),
    (1979, DATE '1979-04-15'), (1980, DATE '1980-04-06'), (1981, DATE '1981-04-19'),
    (1982, DATE '1982-04-11'), (1983, DATE '1983-04-03'), (1984, DATE '1984-04-22'),
    (1985, DATE '1985-04-07'), (1986, DATE '1986-03-30'), (1987, DATE '1987-04-19'),
    (1988, DATE '1988-04-03'), (1989, DATE '1989-03-26'), (1990, DATE '1990-04-15'),
    (1991, DATE '1991-03-31'), (1992, DATE '1992-04-19'), (1993, DATE '1993-04-11'),
    (1994, DATE '1994-04-03'), (1995, DATE '1995-04-16'), (1996, DATE '1996-04-07'),
    (1997, DATE '1997-03-30'), (1998, DATE '1998-04-12'), (1999, DATE '1999-04-04'),
    (2000, DATE '2000-04-23'), (2001, DATE '2001-04-15'), (2002, DATE '2002-03-31'),
    (2003, DATE '2003-04-20'), (2004, DATE '2004-04-11'), (2005, DATE '2005-03-27'),
    (2006, DATE '2006-04-16'), (2007, DATE '2007-04-08'), (2008, DATE '2008-03-23'),
    (2009, DATE '2009-04-12'), (2010, DATE '2010-04-04'), (2011, DATE '2011-04-24'),
    (2012, DATE '2012-04-08'), (2013, DATE '2013-03-31'), (2014, DATE '2014-04-20'),
    (2015, DATE '2015-04-05'), (2016, DATE '2016-03-27'), (2017, DATE '2017-04-16'),
    (2018, DATE '2018-04-01'), (2019, DATE '2019-04-21'), (2020, DATE '2020-04-12'),
    (2021, DATE '2021-04-04'), (2022, DATE '2022-04-17'), (2023, DATE '2023-04-09'),
    (2024, DATE '2024-03-31'), (2025, DATE '2025-04-20'), (2026, DATE '2026-04-05'),
    (2027, DATE '2027-03-28'), (2028, DATE '2028-04-16'), (2029, DATE '2029-04-01'),
    (2030, DATE '2030-04-21'), (2031, DATE '2031-04-13'), (2032, DATE '2032-03-28'),
    (2033, DATE '2033-04-17'), (2034, DATE '2034-04-09'), (2035, DATE '2035-03-25'),
    (2036, DATE '2036-04-13'), (2037, DATE '2037-04-05'), (2038, DATE '2038-04-25'),
    (2039, DATE '2039-04-10'), (2040, DATE '2040-04-01'), (2041, DATE '2041-04-21'),
    (2042, DATE '2042-04-06'), (2043, DATE '2043-03-29'), (2044, DATE '2044-04-17'),
    (2045, DATE '2045-04-09'), (2046, DATE '2046-03-25'), (2047, DATE '2047-04-14'),
    (2048, DATE '2048-04-05'), (2049, DATE '2049-04-18')
),
d AS (
  SELECT d::DATE AS datum
  FROM range(DATE '1970-01-01', DATE '2050-01-01', INTERVAL 1 DAY) t(d)  
)
SELECT
  CAST(strftime(d.datum, '%Y%m%d') AS INTEGER)                      AS id,
  d.datum                                                            AS date_actual,
  date_diff('seconds', TIMESTAMP '1970-01-01 00:00:00', d.datum::TIMESTAMP) AS epoch_seconds,


  -- Names & ordinals
  (CAST(EXTRACT(DAY FROM d.datum) AS INTEGER)::VARCHAR ||
     CASE
       WHEN EXTRACT(DAY FROM d.datum) IN (11,12,13) THEN 'th'
       WHEN EXTRACT(DAY FROM d.datum) % 10 = 1 THEN 'st'
       WHEN EXTRACT(DAY FROM d.datum) % 10 = 2 THEN 'nd'
       WHEN EXTRACT(DAY FROM d.datum) % 10 = 3 THEN 'rd'
       ELSE 'th'
     END)                                                            AS day_suffix,
  strftime(d.datum, '%A')                                           AS day_name,
  CAST(strftime(d.datum, '%u') AS INTEGER)                          AS day_of_week_iso,  -- Mon=1..Sun=7
  EXTRACT(DAY FROM d.datum)                                         AS day_of_month,
  date_diff('day', date_trunc('quarter', d.datum), d.datum) + 1     AS day_of_quarter,
  CAST(strftime(d.datum, '%j') AS INTEGER)                          AS day_of_year,

  -- Weeks
  CAST(
    floor(
      (EXTRACT(DAY FROM d.datum)
       + CAST(strftime(date_trunc('month', d.datum), '%u') AS INTEGER) - 2
      ) / 7
    ) + 1 AS INTEGER
  )                                                                 AS week_of_month,     -- ISO-style
  CAST(strftime(d.datum + INTERVAL 1 DAY, '%U') AS INTEGER)         AS week_of_year,      -- Sunday-start (00–53)
  strftime(d.datum, '%G-W%V-%u')                                    AS week_of_year_iso,  -- e.g., 2025-W35-1

  -- Month / quarter / year
  EXTRACT(MONTH FROM d.datum)                                       AS month_actual,
  strftime(d.datum, '%B')                                           AS month_name,
  strftime(d.datum, '%b')                                           AS month_name_abbreviated,
  EXTRACT(QUARTER FROM d.datum)                                     AS quarter_actual,
  ('Q' || EXTRACT(QUARTER FROM d.datum)::VARCHAR)                   AS quarter_name,
  EXTRACT(YEAR FROM d.datum)                                        AS year_actual,

  -- Period boundaries
  d.datum - (CAST(strftime(d.datum, '%u') AS INTEGER) - 1) * INTERVAL 1 DAY  AS first_day_of_week,
  d.datum + (7 - CAST(strftime(d.datum, '%u') AS INTEGER)) * INTERVAL 1 DAY  AS last_day_of_week,
  date_trunc('month', d.datum)                                      AS first_day_of_month,
  date_trunc('month', d.datum) + INTERVAL 1 MONTH - INTERVAL 1 DAY  AS last_day_of_month,
  date_trunc('quarter', d.datum)                                    AS first_day_of_quarter,
  date_trunc('quarter', d.datum) + INTERVAL 3 MONTH - INTERVAL 1 DAY AS last_day_of_quarter,
  date_trunc('year', d.datum)                                       AS first_day_of_year,
  date_trunc('year', d.datum) + INTERVAL 1 YEAR - INTERVAL 1 DAY    AS last_day_of_year,

  -- Labels / sorters
  strftime(d.datum, '%m%Y')                                         AS mmyyyy,
  strftime(d.datum, '%m%d%Y')                                       AS mmddyyyy,
  strftime(d.datum, '%G%V')                                         AS yyyyww,           -- ISO year+week (e.g., 202535)
  strftime(d.datum, '%m/%y')                                        AS month_year_label, -- 07/25
  ('Q' || EXTRACT(QUARTER FROM d.datum)::VARCHAR || '/' || strftime(d.datum, '%y'))
                                                                   AS quarter_year_label,
  EXTRACT(YEAR FROM d.datum) * 10 + EXTRACT(QUARTER FROM d.datum)   AS quarter_year_sort,
  (strftime(d.datum, '%V') || '/' || strftime(d.datum, '%y'))       AS iso_week_year_label,
  ('KW' || lpad(strftime(d.datum, '%V'), 2, '0') || '/' || strftime(d.datum, '%y'))
                                                                   AS kw_label,
  CAST(strftime(d.datum, '%G') AS INTEGER) * 100
    + CAST(strftime(d.datum, '%V') AS INTEGER)                      AS iso_week_year_sort,
  EXTRACT(YEAR FROM d.datum) * 100 + EXTRACT(MONTH FROM d.datum)    AS month_year_sort,

  -- Workday / weekend / holidays (DE core + movable feasts)
  (CAST(strftime(d.datum, '%u') AS INTEGER) IN (6,7))               AS weekend_indr,
  CASE
    WHEN EXTRACT(DAY FROM d.datum)=1 AND EXTRACT(MONTH FROM d.datum)=1  THEN TRUE  -- Neujahr
    WHEN EXTRACT(DAY FROM d.datum)=1 AND EXTRACT(MONTH FROM d.datum)=5  THEN TRUE  -- Tag der Arbeit
    WHEN EXTRACT(DAY FROM d.datum)=3 AND EXTRACT(MONTH FROM d.datum)=10 THEN TRUE  -- Tag d. dt. Einheit
    WHEN EXTRACT(DAY FROM d.datum)=25 AND EXTRACT(MONTH FROM d.datum)=12 THEN TRUE -- 1. Weihnachtstag
    WHEN EXTRACT(DAY FROM d.datum)=26 AND EXTRACT(MONTH FROM d.datum)=12 THEN TRUE -- 2. Weihnachtstag
    WHEN es.day_actual = d.datum                                     THEN TRUE  -- Ostersonntag
    WHEN es.day_actual - INTERVAL 2 DAY = d.datum                    THEN TRUE  -- Karfreitag
    WHEN es.day_actual + INTERVAL 1 DAY = d.datum                    THEN TRUE  -- Ostermontag
    WHEN es.day_actual + INTERVAL 39 DAY = d.datum                   THEN TRUE  -- Christi Himmelfahrt
    WHEN es.day_actual + INTERVAL 50 DAY = d.datum                   THEN TRUE  -- Pfingstmontag
    ELSE FALSE
  END                                                                AS is_holiday,
  (CAST(strftime(d.datum, '%u') AS INTEGER) BETWEEN 1 AND 5)
    AND NOT (
      CASE
        WHEN EXTRACT(DAY FROM d.datum)=1 AND EXTRACT(MONTH FROM d.datum)=1  THEN TRUE
        WHEN EXTRACT(DAY FROM d.datum)=1 AND EXTRACT(MONTH FROM d.datum)=5  THEN TRUE
        WHEN EXTRACT(DAY FROM d.datum)=3 AND EXTRACT(MONTH FROM d.datum)=10 THEN TRUE
        WHEN EXTRACT(DAY FROM d.datum)=25 AND EXTRACT(MONTH FROM d.datum)=12 THEN TRUE
        WHEN EXTRACT(DAY FROM d.datum)=26 AND EXTRACT(MONTH FROM d.datum)=12 THEN TRUE
        WHEN es.day_actual = d.datum                                      THEN TRUE
        WHEN es.day_actual - INTERVAL 2 DAY = d.datum                     THEN TRUE
        WHEN es.day_actual + INTERVAL 1 DAY = d.datum                     THEN TRUE
        WHEN es.day_actual + INTERVAL 39 DAY = d.datum                    THEN TRUE
        WHEN es.day_actual + INTERVAL 50 DAY = d.datum                    THEN TRUE
        ELSE FALSE
      END
    )                                                                  AS is_workday

FROM d
LEFT JOIN easter_sunday es
  ON es.year_actual = EXTRACT(YEAR FROM d.datum)
ORDER BY id