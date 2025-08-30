# run_duck.py
import duckdb, pathlib

# open/create DB in repo root
con = duckdb.connect("data.duckdb")

print(con.sql("SELECT * FROM equities_daily LIMIT 5;").df())