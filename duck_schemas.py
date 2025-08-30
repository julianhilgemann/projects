import duckdb, pathlib
# open/create DB in repo root 
con = duckdb.connect("data.duckdb")

# Schemas
print(con.sql("""
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name
""").df())

# All tables & views
print(con.sql("""
SELECT table_schema, table_name, table_type
FROM information_schema.tables
ORDER BY table_schema, table_name
""").df())

# Columns of a specific table (e.g., equities_daily in default 'main' schema)
print(con.sql("""
SELECT column_name, data_type, is_nullable, ordinal_position
FROM information_schema.columns
WHERE table_schema = 'main' AND table_name = 'equities_daily'
ORDER BY ordinal_position
""").df())
