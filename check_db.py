import sqlite3
import pandas as pd

DB_FILE = "food_wastage.db"

# Connect to the database
con = sqlite3.connect(DB_FILE)

# Preview row counts
for table in ["providers", "receivers", "food_listings", "claims"]:
    count = pd.read_sql_query(f"SELECT COUNT(*) as total FROM {table};", con)
    print(f"{table}: {count['total'][0]} rows")

print("\n=== Providers (first 5) ===")
print(pd.read_sql_query("SELECT * FROM providers LIMIT 5;", con))

print("\n=== Food Listings (first 5) ===")
print(pd.read_sql_query("SELECT * FROM food_listings LIMIT 5;", con))

print("\n=== Claims Status Counts ===")
print(pd.read_sql_query("SELECT Status, COUNT(*) as cnt FROM claims GROUP BY Status;", con))

con.close()
