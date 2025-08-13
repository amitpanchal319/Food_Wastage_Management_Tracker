import sqlite3
import pandas as pd

# ====== Paths to your CSVs ======
providers_csv = r"E:\Laptop Data\Amit Panchal\Internship Projects\Food Wastage\data\providers_data.csv"
receivers_csv = r"E:\Laptop Data\Amit Panchal\Internship Projects\Food Wastage\data\receivers_data.csv"
food_listings_csv = r"E:\Laptop Data\Amit Panchal\Internship Projects\Food Wastage\data\food_listings_data.csv"
claims_csv = r"E:\Laptop Data\Amit Panchal\Internship Projects\Food Wastage\data\claims_data.csv"

# ====== Output DB file ======
db_file = "food_wastage.db"

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

# ====== Create DB and load CSV data ======
con = sqlite3.connect(db_file)
cur = con.cursor()
cur.executescript(schema_sql)

# Load CSVs into tables
pd.read_csv(providers_csv).to_sql("providers", con, if_exists="append", index=False)
pd.read_csv(receivers_csv).to_sql("receivers", con, if_exists="append", index=False)
pd.read_csv(food_listings_csv).to_sql("food_listings", con, if_exists="append", index=False)
pd.read_csv(claims_csv).to_sql("claims", con, if_exists="append", index=False)

con.commit()
con.close()

print(f"Database created: {db_file}")
