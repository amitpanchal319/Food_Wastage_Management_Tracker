import sqlite3
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime, timedelta

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from load_csv_to_sqlite import build_db

DB_FILE = build_db()  # ensures DB exists before connecting



DB_FILE = "food_wastage.db"


import os
from load_csv_to_sqlite import build_db

if not os.path.exists(DB_FILE):
    build_db()

# ---------------- Database Connection ----------------
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

@st.cache_data
def load_filters(_con):
    cities = pd.read_sql_query("SELECT DISTINCT City FROM providers ORDER BY City;", _con)["City"].tolist()
    provider_types = pd.read_sql_query("SELECT DISTINCT Provider_Type FROM food_listings ORDER BY Provider_Type;", _con)["Provider_Type"].tolist()
    food_types = pd.read_sql_query("SELECT DISTINCT Food_Type FROM food_listings ORDER BY Food_Type;", _con)["Food_Type"].tolist()
    meal_types = pd.read_sql_query("SELECT DISTINCT Meal_Type FROM food_listings ORDER BY Meal_Type;", _con)["Meal_Type"].tolist()
    return cities, provider_types, food_types, meal_types

def run_query(con, query, params=None):
    if params is None:
        params = []
    return pd.read_sql_query(query, con, params=params)

def run_execute(con, query, params=None):
    """For INSERT, UPDATE, DELETE"""
    if params is None:
        params = []
    cur = con.cursor()
    cur.execute(query, params)
    con.commit()

# ---------------- UI ----------------
st.set_page_config(page_title="Food Wastage Management", layout="wide")
st.title("🥗 Food Wastage Management - Starter App")

con = get_connection()
cities, provider_types, food_types, meal_types = load_filters(con)

# ---------------- Sidebar Filters ----------------
with st.sidebar:
    st.header("Filters")
    city = st.selectbox("City", ["All"] + cities)
    ptype = st.selectbox("Provider Type", ["All"] + provider_types)
    ftype = st.selectbox("Food Type", ["All"] + food_types)
    mtype = st.selectbox("Meal Type", ["All"] + meal_types)

# ---------------- Filtered Food Listings ----------------
st.subheader("Available Food Listings")
query = """
SELECT Food_ID, Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type
FROM food_listings WHERE 1=1
"""
params = []
if city != "All":
    query += " AND Location = ?"
    params.append(city)
if ptype != "All":
    query += " AND Provider_Type = ?"
    params.append(ptype)
if ftype != "All":
    query += " AND Food_Type = ?"
    params.append(ftype)
if mtype != "All":
    query += " AND Meal_Type = ?"
    params.append(mtype)

query += " ORDER BY date(Expiry_Date) ASC, Quantity DESC"
listings_df = run_query(con, query, params)

# --- Expiry Alert ---
# --- Expiry Alert ---
today = datetime.now().date()
soon_limit = today + timedelta(days=2)

def get_expiry_status(exp_date_str):
    try:
        exp_date = pd.to_datetime(exp_date_str).date()
        if exp_date == today:
            return ("⚠ Expiring Today", "#ff4d4d")
        elif today < exp_date <= soon_limit:
            return ("⚠ Expiring Soon", "#ffcccc")
        else:
            return ("", "")
    except:
        return ("", "")

# safely split into two new columns
expiry_info = listings_df["Expiry_Date"].apply(get_expiry_status)
listings_df["Expiry Alert"] = expiry_info.apply(lambda x: x[0])
listings_df["Color"] = expiry_info.apply(lambda x: x[1])

def highlight_row(row):
    if row["Color"]:
        return ["background-color: " + row["Color"]] * len(row)
    return [""] * len(row)

st.dataframe(listings_df.style.apply(highlight_row, axis=1), use_container_width=True)



# ---------------- Provider Contacts ----------------
st.subheader("Provider Contacts")
contact_query = "SELECT Name, Type, Address, City, Contact FROM providers"
contact_params = []
if city != "All":
    contact_query += " WHERE City = ?"
    contact_params.append(city)
contact_df = run_query(con, contact_query, contact_params)
st.dataframe(contact_df, use_container_width=True)

# ---------------- Quick Analytics ----------------
st.subheader("Quick Analytics")
col1, col2, col3 = st.columns(3)
with col1:
    total_qty = run_query(con, "SELECT SUM(Quantity) as total FROM food_listings WHERE date(Expiry_Date) >= date('now');")
    st.metric("Total Quantity Available", int(total_qty['total'][0]) if pd.notnull(total_qty['total'][0]) else 0)
with col2:
    status_counts = run_query(con, "SELECT Status, COUNT(*) as cnt FROM claims GROUP BY Status;")
    st.dataframe(status_counts, use_container_width=True, height=180)
with col3:
    top_city = run_query(con, "SELECT Location, COUNT(*) as cnt FROM food_listings GROUP BY Location ORDER BY cnt DESC LIMIT 1;")
    if not top_city.empty:
        st.metric("Top City by Listings", f"{top_city['Location'][0]} ({top_city['cnt'][0]})")

# ---------------- Predefined Queries ----------------
st.subheader("📊 Project Analysis Queries")
query_map = {
    "Providers per City":
        "SELECT City, COUNT(*) AS provider_count FROM providers GROUP BY City ORDER BY provider_count DESC, City;",
    "Receivers per City":
        "SELECT City, COUNT(*) AS receiver_count FROM receivers GROUP BY City ORDER BY receiver_count DESC, City;",
    "Top Contributing Provider Type":
        "SELECT Provider_Type, SUM(Quantity) AS total_quantity FROM food_listings GROUP BY Provider_Type ORDER BY total_quantity DESC;",
    "Provider Contacts by City":
        "SELECT Name, Type, Address, City, Contact FROM providers WHERE City = 'Mumbai' ORDER BY Name;",
    "Top Receivers by Completed Claims":
        """SELECT r.Receiver_ID, r.Name, r.Type, r.City,
                  COUNT(c.Claim_ID) AS total_claims,
                  SUM(CASE WHEN c.Status='Completed' THEN 1 ELSE 0 END) AS completed_claims
           FROM receivers r
           JOIN claims c ON c.Receiver_ID = r.Receiver_ID
           GROUP BY r.Receiver_ID, r.Name, r.Type, r.City
           ORDER BY completed_claims DESC, total_claims DESC
           LIMIT 10;""",
    "Total Quantity Available":
        "SELECT SUM(Quantity) AS total_available_quantity FROM food_listings WHERE date(Expiry_Date) >= date('now');",
    "City with Most Listings":
        "SELECT Location AS City, COUNT(*) AS listing_count FROM food_listings GROUP BY Location ORDER BY listing_count DESC, City;",
    "Most Common Food Types":
        "SELECT Food_Type, COUNT(*) AS items_count FROM food_listings GROUP BY Food_Type ORDER BY items_count DESC;",
    "Claims per Food Item":
        "SELECT Food_ID, COUNT(*) AS claim_count FROM claims GROUP BY Food_ID ORDER BY claim_count DESC, Food_ID LIMIT 20;",
    "Provider with Most Successful Claims":
        """SELECT p.Provider_ID, p.Name, p.Type, p.City,
                  COUNT(c.Claim_ID) AS successful_claims
           FROM providers p
           JOIN food_listings f ON f.Provider_ID = p.Provider_ID
           JOIN claims c ON c.Food_ID = f.Food_ID
           WHERE c.Status = 'Completed'
           GROUP BY p.Provider_ID, p.Name, p.Type, p.City
           ORDER BY successful_claims DESC
           LIMIT 10;""",
    "Claim Status Distribution":
        """SELECT Status, COUNT(*) AS count,
                  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM claims), 2) AS percentage
           FROM claims
           GROUP BY Status
           ORDER BY count DESC;""",
    "Average Quantity Claimed per Receiver":
        """SELECT r.Receiver_ID, r.Name,
                  ROUND(AVG(f.Quantity), 2) AS avg_quantity_per_claim
           FROM claims c
           JOIN receivers r ON r.Receiver_ID = c.Receiver_ID
           JOIN food_listings f ON f.Food_ID = c.Food_ID
           WHERE c.Status = 'Completed'
           GROUP BY r.Receiver_ID, r.Name
           ORDER BY avg_quantity_per_claim DESC
           LIMIT 15;""",
    "Most Claimed Meal Type":
        """SELECT f.Meal_Type, COUNT(*) AS completed_claims
           FROM claims c
           JOIN food_listings f ON f.Food_ID = c.Food_ID
           WHERE c.Status = 'Completed'
           GROUP BY f.Meal_Type
           ORDER BY completed_claims DESC;""",
    "Total Quantity Donated by Provider":
        """SELECT p.Provider_ID, p.Name, SUM(f.Quantity) AS total_quantity_donated
           FROM providers p
           JOIN food_listings f ON f.Provider_ID = p.Provider_ID
           GROUP BY p.Provider_ID, p.Name
           ORDER BY total_quantity_donated DESC
           LIMIT 20;""",
    "Listings Expiring Soon":
        """SELECT Food_ID, Food_Name, Quantity, Expiry_Date, Location, Food_Type, Meal_Type
           FROM food_listings
           WHERE date(Expiry_Date) BETWEEN date('now') AND date('now','+2 day')
           ORDER BY date(Expiry_Date), Quantity DESC;""",
    "Top Cities by Completed Claims":
        """SELECT f.Location AS City, COUNT(*) AS completed_claims
           FROM claims c
           JOIN food_listings f ON f.Food_ID = c.Food_ID
           WHERE c.Status = 'Completed'
           GROUP BY f.Location
           ORDER BY completed_claims DESC
           LIMIT 10;"""
}

selected_query_name = st.selectbox("Select a predefined query:", list(query_map.keys()))
if st.button("Run Selected Query", key="run_predefined_query"):
    sql = query_map[selected_query_name]
    try:
        result_df = run_query(con, sql)
        st.dataframe(result_df, use_container_width=True)
        # Optional: add charts (as in your original app)
    except Exception as e:
        st.error(f"Error: {e}")

# ---------------- Run Custom SQL ----------------
st.subheader("Run Custom SQL")
custom_sql = st.text_area("Enter SQL query:", "SELECT * FROM providers LIMIT 5;")
if st.button("Run SQL", key="run_custom_sql"):
    try:
        res = run_query(con, custom_sql)
        st.dataframe(res, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

# ---------------- CRUD Operations ----------------
st.subheader("🛠 CRUD Operations")

crud_tab = st.tabs(["Food Listings", "Providers", "Receivers", "Claims"])

# ---------------- Food Listings CRUD ----------------
with crud_tab[0]:
    st.markdown("### Manage Food Listings")
    action = st.selectbox("Select Action", ["Add", "Update", "Delete"])

    if action == "Add":
        with st.form("add_food_form"):
            food_name = st.text_input("Food Name")
            quantity = st.number_input("Quantity", min_value=1)
            expiry_date = st.date_input("Expiry Date")
            provider_id = st.text_input("Provider ID")
            provider_type = st.text_input("Provider Type")
            location = st.text_input("Location")
            food_type = st.text_input("Food Type")
            meal_type = st.text_input("Meal Type")
            submitted = st.form_submit_button("Add Food Listing")
            if submitted:
                run_execute(con,
                            "INSERT INTO food_listings (Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type) VALUES (?,?,?,?,?,?,?,?)",
                            [food_name, quantity, expiry_date, provider_id, provider_type, location, food_type, meal_type])
                st.success("Food Listing Added!")

    elif action == "Update":
        with st.form("update_food_form"):
            food_id = st.text_input("Food ID to Update")
            quantity = st.number_input("New Quantity", min_value=1)
            expiry_date = st.date_input("New Expiry Date")
            submitted = st.form_submit_button("Update Food Listing")
            if submitted:
                run_execute(con,
                            "UPDATE food_listings SET Quantity=?, Expiry_Date=? WHERE Food_ID=?",
                            [quantity, expiry_date, food_id])
                st.success("Food Listing Updated!")

    elif action == "Delete":
        with st.form("delete_food_form"):
            food_id = st.text_input("Food ID to Delete")
            submitted = st.form_submit_button("Delete Food Listing")
            if submitted:
                run_execute(con, "DELETE FROM food_listings WHERE Food_ID=?", [food_id])
                st.success("Food Listing Deleted!")

# ---------------- Providers CRUD ----------------
with crud_tab[1]:
    st.markdown("### Manage Providers")
    action = st.selectbox("Select Action", ["Add", "Update", "Delete"], key="provider_action")

    if action == "Add":
        with st.form("add_provider_form"):
            name = st.text_input("Name")
            type_ = st.text_input("Type")
            address = st.text_input("Address")
            city_ = st.text_input("City")
            contact = st.text_input("Contact")
            submitted = st.form_submit_button("Add Provider")
            if submitted:
                run_execute(con,
                            "INSERT INTO providers (Name, Type, Address, City, Contact) VALUES (?,?,?,?,?)",
                            [name, type_, address, city_, contact])
                st.success("Provider Added!")

    elif action == "Update":
        with st.form("update_provider_form"):
            provider_id = st.text_input("Provider ID to Update")
            contact = st.text_input("New Contact")
            submitted = st.form_submit_button("Update Provider")
            if submitted:
                run_execute(con,
                            "UPDATE providers SET Contact=? WHERE Provider_ID=?",
                            [contact, provider_id])
                st.success("Provider Updated!")

    elif action == "Delete":
        with st.form("delete_provider_form"):
            provider_id = st.text_input("Provider ID to Delete")
            submitted = st.form_submit_button("Delete Provider")
            if submitted:
                run_execute(con, "DELETE FROM providers WHERE Provider_ID=?", [provider_id])
                st.success("Provider Deleted!")

# ---------------- Receivers CRUD ----------------
with crud_tab[2]:
    st.markdown("### Manage Receivers")
    action = st.selectbox("Select Action", ["Add", "Update", "Delete"], key="receiver_action")

    if action == "Add":
        with st.form("add_receiver_form"):
            name = st.text_input("Name")
            type_ = st.text_input("Type")
            city_ = st.text_input("City")
            submitted = st.form_submit_button("Add Receiver")
            if submitted:
                run_execute(con,
                            "INSERT INTO receivers (Name, Type, City) VALUES (?,?,?)",
                            [name, type_, city_])
                st.success("Receiver Added!")

    elif action == "Update":
        with st.form("update_receiver_form"):
            receiver_id = st.text_input("Receiver ID to Update")
            city_ = st.text_input("New City")
            submitted = st.form_submit_button("Update Receiver")
            if submitted:
                run_execute(con,
                            "UPDATE receivers SET City=? WHERE Receiver_ID=?",
                            [city_, receiver_id])
                st.success("Receiver Updated!")

    elif action == "Delete":
        with st.form("delete_receiver_form"):
            receiver_id = st.text_input("Receiver ID to Delete")
            submitted = st.form_submit_button("Delete Receiver")
            if submitted:
                run_execute(con, "DELETE FROM receivers WHERE Receiver_ID=?", [receiver_id])
                st.success("Receiver Deleted!")

# ---------------- Claims CRUD ----------------
with crud_tab[3]:
    st.markdown("### Manage Claims")
    action = st.selectbox("Select Action", ["Add", "Update", "Delete"], key="claim_action")

    if action == "Add":
        with st.form("add_claim_form"):
            food_id = st.text_input("Food ID")
            receiver_id = st.text_input("Receiver ID")
            status = st.selectbox("Status", ["Pending", "Completed", "Canceled"])
            submitted = st.form_submit_button("Add Claim")
            if submitted:
                run_execute(con,
                            "INSERT INTO claims (Food_ID, Receiver_ID, Status) VALUES (?,?,?)",
                            [food_id, receiver_id, status])
                st.success("Claim Added!")

    elif action == "Update":
        with st.form("update_claim_form"):
            claim_id = st.text_input("Claim ID to Update")
            status = st.selectbox("New Status", ["Pending", "Completed", "Canceled"])
            submitted = st.form_submit_button("Update Claim")
            if submitted:
                run_execute(con,
                            "UPDATE claims SET Status=? WHERE Claim_ID=?",
                            [status, claim_id])
                st.success("Claim Updated!")

    elif action == "Delete":
        with st.form("delete_claim_form"):
            claim_id = st.text_input("Claim ID to Delete")
            submitted = st.form_submit_button("Delete Claim")
            if submitted:
                run_execute(con, "DELETE FROM claims WHERE Claim_ID=?", [claim_id])
                st.success("Claim Deleted!")
