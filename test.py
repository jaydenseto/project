import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt

# Database Setup
def init_db():
    conn = sqlite3.connect("co2_emission_tracker.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS emissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        date TEXT,
                        distance REAL,
                        transportation TEXT,
                        co2_emitted REAL,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

# Calculate CO2 Emissions
def calculate_emissions(distance, transportation):
    co2_factors = {
        "Car": 0.12,    # kg CO2 per km
        "Bus": 0.05,
        "Train": 0.03,
        "Bicycle": 0.0,
        "Walking": 0.0
    }
    return distance * co2_factors.get(transportation, 0)

# Add Emission Data
def add_emission(user_id, date, distance, transportation):
    co2_emitted = calculate_emissions(distance, transportation)
    conn = sqlite3.connect("co2_emission_tracker.db")
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO emissions (user_id, date, distance, transportation, co2_emitted) 
                      VALUES (?, ?, ?, ?, ?)''', (user_id, date, distance, transportation, co2_emitted))
    conn.commit()
    conn.close()

# Fetch Data for Visualization
def fetch_user_emissions(user_id):
    conn = sqlite3.connect("co2_emission_tracker.db")
    cursor = conn.cursor()
    cursor.execute('''SELECT date, co2_emitted FROM emissions WHERE user_id = ?''', (user_id,))
    data = cursor.fetchall()
    conn.close()
    return pd.DataFrame(data, columns=["Date", "CO2 Emitted (kg)"])

# Streamlit App
st.title("CO2 Emission Tracker")

# Initialize Database
init_db()

# User Registration or Selection
st.sidebar.header("User")
username = st.sidebar.text_input("Enter your name")
if st.sidebar.button("Register"):
    conn = sqlite3.connect("co2_emission_tracker.db")
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO users (name) VALUES (?)''', (username,))
    conn.commit()
    conn.close()
    st.sidebar.success(f"User {username} registered successfully!")

# Select User
conn = sqlite3.connect("co2_emission_tracker.db")
cursor = conn.cursor()
cursor.execute('''SELECT id, name FROM users''')
users = cursor.fetchall()
conn.close()
user_dict = {name: user_id for user_id, name in users}
selected_user = st.sidebar.selectbox("Select User", options=list(user_dict.keys()))
user_id = user_dict.get(selected_user, None)

if user_id:
    # Data Entry
    st.header("Log Your Emissions")
    date = st.date_input("Date")
    distance = st.number_input("Distance Traveled (km)", min_value=0.0, step=0.1)
    transportation = st.selectbox("Transportation Type", ["Car", "Bus", "Train", "Bicycle", "Walking"])

    if st.button("Add Entry"):
        add_emission(user_id, date, distance, transportation)
        st.success("Emission data added successfully!")

    # Visualization
    st.header("Your Emission Trends")
    data = fetch_user_emissions(user_id)
    if not data.empty:
        st.line_chart(data.set_index("Date"))
        st.write("Total CO2 Emitted (kg):", data["CO2 Emitted (kg)"].sum())
    else:
        st.write("No data to display. Start logging your emissions!")




