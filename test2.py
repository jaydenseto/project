
import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime

# Initialize the database
def init_db():
    conn = sqlite3.connect("co2_tracker.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS emissions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  date TEXT,
                  distance REAL,
                  transport_type TEXT,
                  co2_emissions REAL,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.commit()
    conn.close()

# Hash the password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Register a new user
def register_user(username, password):
    conn = sqlite3.connect("co2_tracker.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                  (username, hash_password(password)))
        conn.commit()
        st.success("User registered successfully!")
    except sqlite3.IntegrityError:
        st.error("Username already exists!")
    conn.close()

# Authenticate user
def login_user(username, password):
    conn = sqlite3.connect("co2_tracker.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user

# Add CO2 emission entry
def add_emission(user_id, date, distance, transport_type, co2_emissions):
    conn = sqlite3.connect("co2_tracker.db")
    c = conn.cursor()
    c.execute('''INSERT INTO emissions 
                 (user_id, date, distance, transport_type, co2_emissions) 
                 VALUES (?, ?, ?, ?, ?)''', 
              (user_id, date, distance, transport_type, co2_emissions))
    conn.commit()
    conn.close()

# Fetch emissions for a user
def fetch_emissions(user_id):
    conn = sqlite3.connect("co2_tracker.db")
    c = conn.cursor()
    c.execute("SELECT date, co2_emissions FROM emissions WHERE user_id = ?", (user_id,))
    data = c.fetchall()
    conn.close()
    return pd.DataFrame(data, columns=["date", "co2_emissions"])

# Generate PDF report
def create_pdf(user_id):
    emissions = fetch_emissions(user_id)
    filename = "co2_report.pdf"

    # Create a line graph
    plt.figure(figsize=(10, 6))
    plt.plot(emissions["date"], emissions["co2_emissions"], marker="o")
    plt.title("CO2 Emissions Over Time")
    plt.xlabel("Date")
    plt.ylabel("CO2 Emissions (kg)")
    plt.grid()
    plt.savefig("co2_trend.png")
    plt.close()

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="CO2 Emissions Report", ln=True, align="C")
    pdf.image("co2_trend.png", x=10, y=30, w=180)
    pdf.output(filename)
    st.success(f"PDF Report Generated: {filename}")

# Main application
def main():
    init_db()

    st.title("CO2 Emission Tracker")

    # Login or Register
    menu = st.sidebar.selectbox("Menu", ["Login", "Register", "Logout"])
    if menu == "Register":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            register_user(username, password)
    elif menu == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state["user_id"] = user[0]
                st.success("Logged in successfully!")
            else:
                st.error("Invalid username or password!")
    elif menu == "Logout":
        st.session_state.clear()
        st.success("Logged out successfully!")

    # Main App
    if "user_id" in st.session_state:
        st.subheader("Log CO2 Emissions")
        date = st.date_input("Date")
        distance = st.number_input("Distance (km)", min_value=0.0)
        transport_type = st.selectbox("Transportation Type", ["Car", "Bike", "Bus", "Train"])
        if st.button("Add Entry"):
            co2_emissions = distance * 0.12  # Example: Car = 0.12 kg CO2 per km
            add_emission(st.session_state["user_id"], date, distance, transport_type, co2_emissions)
            st.success("Emission data added!")

        st.subheader("Emission Trends")
        emissions = fetch_emissions(st.session_state["user_id"])
        if not emissions.empty:
            st.line_chart(emissions.set_index("date"))

        if st.button("Generate PDF Report"):
            create_pdf(st.session_state["user_id"])

if __name__ == "__main__":
    main()

