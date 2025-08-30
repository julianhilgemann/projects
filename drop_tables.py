# run_duck.py
import duckdb

con = duckdb.connect("data.duckdb")  # opens/creates DB in current folder

# drop the two tables (won't error if they don't exist)
con.execute("DROP TABLE IF EXISTS ...;")

# show what's left
print(con.sql("""
  SELECT table_schema, table_name, table_type
  FROM information_schema.tables
  WHERE table_schema = 'main'
  ORDER BY table_name
""").df())

con.close()