import sqlite3
import pandas as pd
import os

# ====== Paths to your CSVs ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
providers_csv = os.path.join(BASE_DIR, "data", "providers_data.csv")
receivers_csv = os.path.join(BASE_DIR, "data", "receivers_data.csv")
food_listings_csv = os.path.join(BASE_DIR, "data", "food_listings_data.csv")
claims_csv = os.path.join(BASE_DIR, "data", "claims_data.csv")

# ====== Output DB file ======
db_file = os.path.join(BASE_DIR, "food_wastage.db")

# ====== Create schema ======
schema_sql = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS providers (
    Provider_ID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Type TEXT NOT NULL,
    Address TEXT,
    City TEXT NOT NULL,
    Contact TEXT
);

CREATE TABLE IF NOT EXISTS receivers (
    Receiver_ID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Type TEXT NOT NULL,
    City TEXT NOT NULL,
    Contact TEXT
);

CREATE TABLE IF NOT EXISTS food_listings (
    Food_ID INTEGER PRIMARY KEY,
    Food_Name TEXT NOT NULL,
    Quantity INTEGER NOT NULL,
    Expiry_Date TEXT NOT NULL,
    Provider_ID INTEGER NOT NULL,
    Provider_Type TEXT NOT NULL,
    Location TEXT NOT NULL,
    Food_Type TEXT NOT NULL,
    Meal_Type TEXT NOT NULL,
    FOREIGN KEY (Provider_ID) REFERENCES providers(Provider_ID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS claims (
    Claim_ID INTEGER PRIMARY KEY,
    Food_ID INTEGER NOT NULL,
    Receiver_ID INTEGER NOT NULL,
    Status TEXT NOT NULL,
    Timestamp TEXT NOT NULL,
    FOREIGN KEY (Food_ID) REFERENCES food_listings(Food_ID) ON DELETE CASCADE,
    FOREIGN KEY (Receiver_ID) REFERENCES receivers(Receiver_ID) ON DELETE CASCADE
);
"""

def build_db(force=False):
    """Create and populate database if not exists or if force=True"""
    if os.path.exists(db_file) and not force:
        return db_file  # DB already exists

    con = sqlite3.connect(db_file)
    cur = con.cursor()
    cur.executescript(schema_sql)

    # ---- Clear old rows (but keep schema) ----
    for table in ["claims", "food_listings", "providers", "receivers"]:
        cur.execute(f"DELETE FROM {table};")

    # ---- Insert fresh CSV data ----
    providers_df = pd.read_csv(providers_csv)
    receivers_df = pd.read_csv(receivers_csv)
    food_df = pd.read_csv(food_listings_csv)
    claims_df = pd.read_csv(claims_csv)

    # Insert providers, receivers, food listings first
    providers_df.to_sql("providers", con, if_exists="append", index=False)
    receivers_df.to_sql("receivers", con, if_exists="append", index=False)
    food_df.to_sql("food_listings", con, if_exists="append", index=False)

    # ---- Validate claims foreign keys ----
    valid_claims = claims_df[
        claims_df["Receiver_ID"].isin(receivers_df["Receiver_ID"]) &
        claims_df["Food_ID"].isin(food_df["Food_ID"])
    ]

    if len(valid_claims) < len(claims_df):
        print(f"⚠ Skipped {len(claims_df) - len(valid_claims)} invalid claim rows (foreign key mismatch)")

    valid_claims.to_sql("claims", con, if_exists="append", index=False)

    con.commit()
    con.close()
    return db_file


if __name__ == "__main__":
    print("Rebuilding database...")
    build_db(force=True)
    print(f"Database created at {db_file}")
