import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Alignment
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import textwrap
import seaborn as sns

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
def add_emission(user_id, date, distance, transport_type):
    # Define emission factors for each transport type
    emission_factors = {
        "Car": 0.12,  # CO2 in kg per km
        "Bike": 0.0,  # No emissions for bikes
        "Bus": 0.05,
        "Train": 0.03
    }
    co2_emissions = distance * emission_factors.get(transport_type, 0.0)

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
    c.execute("SELECT date, distance, co2_emissions, transport_type FROM emissions WHERE user_id = ?", (user_id,))
    data = c.fetchall()
    conn.close()
    return pd.DataFrame(data, columns=["Date", "Distance (km)", "CO2 Emissions (kg)", "Transport Type"])

# Generate the graph for CO2 emissions over time
def display_graphs(user_id):
    emissions_df = fetch_emissions(user_id)

    # Check if there's any emission data
    if not emissions_df.empty:
        # Convert the 'Date' column to datetime format (in case it's not already)
        emissions_df['Date'] = pd.to_datetime(emissions_df['Date'])
        
        # Sort the DataFrame by date (just in case it's not sorted)
        emissions_df = emissions_df.sort_values(by="Date")

        # Plot the graph for CO2 emissions for each specific entry
        plt.figure(figsize=(10, 6))

        # Use the entry index as the x-axis (this will be based on entry number)
        plt.plot(emissions_df.index, emissions_df['CO2 Emissions (kg)'], marker='o', color='tab:blue', label='CO2 Emissions')

        # Customize the graph
        plt.title("CO2 Emissions per Entry")
        plt.xlabel("Date")  # Revert the X-axis title to "Date"
        plt.ylabel("CO2 Emissions (kg)")

        # Set the x-ticks to be the entry numbers (index) but label them with dates
        plt.xticks(ticks=emissions_df.index, labels=emissions_df['Date'].dt.strftime('%Y-%m-%d'), rotation=45)

        # Grid for better readability
        plt.grid(True)
        
        # Show the plot in the Streamlit app
        st.pyplot(plt)

    else:
        st.info("No emission data available yet.")
    

# Calculate the average emissions
def calculate_average_emissions(user_id):
    emissions_df = fetch_emissions(user_id)
    if emissions_df.empty:
        return 0  # No data, so no average
    return emissions_df["CO2 Emissions (kg)"].mean()

# Generate feedback on progress
def generate_improvement_feedback(user_id):
    emissions_df = fetch_emissions(user_id)
    
    # If no emissions have been recorded yet
    if emissions_df.empty:
        return "No emissions data yet. Start recording your trips to track progress."
    
    average_emissions = calculate_average_emissions(user_id)
    last_emission = emissions_df.iloc[-1]
    
    # Round the emissions values to 2 decimal places
    last_emission_value = round(last_emission["CO2 Emissions (kg)"], 2)
    average_emissions_value = round(average_emissions, 2)
    
    if last_emission_value < average_emissions_value:
        return f"Your last entry was {last_emission_value} kg CO2, which is an improvement from your average of {average_emissions_value} kg. Keep it up!"
    else:
        return f"Your last entry was {last_emission_value} kg CO2, which is above your average of {average_emissions_value} kg. Consider reducing your emissions to improve."

# Generate the PDF report
def generate_report(user_id):
    emissions_df = fetch_emissions(user_id)

    # Convert 'Date' column to datetime if it's not already
    emissions_df['Date'] = pd.to_datetime(emissions_df['Date'])

    # Create PDF in memory
    report_stream = BytesIO()
    c = canvas.Canvas(report_stream, pagesize=letter)

    # Add a title to the PDF
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "CO2 Emissions Report")

    # Add a subtitle
    c.setFont("Helvetica", 12)
    c.drawString(100, 730, f"User ID: {user_id}")
    c.drawString(100, 710, f"Report Date: {datetime.now().strftime('%m-%d')}")

    # Add Emission Data Table
    c.setFont("Helvetica-Bold", 10)
    c.drawString(100, 680, "Date")
    c.drawString(200, 680, "Distance (km)")
    c.drawString(300, 680, "CO2 Emissions (kg)")
    c.drawString(400, 680, "Transport Type")

    # Draw emission entries
    y_position = 660
    for index, row in emissions_df.iterrows():
        c.setFont("Helvetica", 10)
        c.drawString(100, y_position, row["Date"].strftime("%m-%d"))  # Correctly formatted date
        c.drawString(200, y_position, f"{row['Distance (km)']:.2f}")
        c.drawString(300, y_position, f"{row['CO2 Emissions (kg)']:.2f}")
        c.drawString(400, y_position, row["Transport Type"])
        y_position -= 20
        if y_position < 100:  # Add a new page if we run out of space
            c.showPage()
            c.setFont("Helvetica-Bold", 10)
            c.drawString(100, 680, "Date")
            c.drawString(200, 680, "Distance (km)")
            c.drawString(300, 680, "CO2 Emissions (kg)")
            c.drawString(400, 680, "Transport Type")
            y_position = 660

    # Add feedback section
    feedback = generate_improvement_feedback(user_id)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y_position - 30, "Feedback on Your Progress:")
    c.setFont("Helvetica", 10)
    c.drawString(100, y_position - 50, feedback)

    # Add the total CO2 emissions paragraph with personalized message
    total_emissions = emissions_df["CO2 Emissions (kg)"].sum()
    total_emissions = round(total_emissions, 2)  # Round to 2 decimal places
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y_position - 80, "Your Total CO2 Emissions Usage:")

    # Personalized written part based on the total emissions
    if total_emissions < 50:
        message = (
            f"Congratulations! Your total CO2 emissions of {total_emissions} kg are well below average. "
            "This indicates that you're making mindful choices in terms of transportation, such as using low-emission modes like biking or public transport. "
            "Keep up the great work! You are contributing to a cleaner and greener world."
        )
    elif total_emissions < 150:
        message = (
            f"Your total CO2 emissions amount to {total_emissions} kg. While you're doing better than many, there is still room for improvement. "
            "Consider incorporating more sustainable transport options, like electric vehicles or carpooling, into your routine. "
            "By making small adjustments, you can significantly reduce your environmental footprint."
        )
    else:
        message = (
            f"Your total CO2 emissions amount to {total_emissions} kg. This is above the recommended threshold for low-emission living, "
            "indicating that there might be opportunities to reduce your carbon footprint. Consider switching to greener modes of transport such as biking, "
            "walking, or using electric vehicles. Your actions can help mitigate climate change and create a sustainable future for everyone."
        )

    # Handle wrapping of text for long messages using textwrap
    text_object = c.beginText(100, y_position - 100)  # Start the text at a given position
    text_object.setFont("Helvetica", 10)  # Set the font and size
    text_object.setTextOrigin(100, y_position - 100)  # Text starts here
    text_object.setLeading(12)  # Set the space between lines

    # Use textwrap to ensure text fits within page width
    max_width = letter[0] - 200  # Page width minus margins (100px left + 100px right)
    wrapped_message = textwrap.fill(message, width=70)  # Wrap message to fit within width
    text_object.textLines(wrapped_message)  # Add wrapped text

    c.drawText(text_object)  # Draw the wrapped text onto the PDF

    # Save the PDF to the in-memory stream
    c.showPage()
    c.save()

    # Go back to the beginning of the stream
    report_stream.seek(0)

    # Make the report available for download in the Streamlit app
    st.download_button(
        label="Download CO2 Emissions PDF Report",
        data=report_stream,
        file_name="co2_emissions_report.pdf",
        mime="application/pdf"
    )


# Display user tips for CO2 reduction
def display_user_tips(transport_type):
    tips = {
        "Car": [
            "Consider using public transport to reduce your CO2 footprint.",
            "Carpooling or using electric vehicles can help reduce your CO2 emissions.",
            "Try to limit the use of high-emission vehicles like SUVs and trucks."
        ],
        "Bike": [
            "Biking is a great zero-emission transport option.",
            "Try biking for short trips instead of using a car or bus."
        ],
        "Bus": [
            "Public transport like buses can significantly reduce CO2 emissions compared to individual car use.",
            "Consider using the bus instead of driving alone to reduce your footprint."
        ],
        "Train": [
            "Trains are a more eco-friendly mode of transport than cars or planes.",
            "If possible, choose trains for longer journeys to reduce your emissions."
        ]
    }

    st.subheader("CO2 Reduction Tips")
    if transport_type in tips:
        for tip in tips[transport_type]:
            st.write(f"- {tip}")

# Additional Analytical Visualizations
def display_additional_visualizations(user_id):
    emissions_df = fetch_emissions(user_id)
    
    if emissions_df.empty:
        st.info("No emission data available yet.")
        return

    # 1. CO2 Emissions Trend Over Time
    emissions_df['Date'] = pd.to_datetime(emissions_df['Date'])
    emissions_df = emissions_df.sort_values(by='Date')

    # CO2 Emissions Trend
    plt.figure(figsize=(10, 6))
    plt.plot(emissions_df['Date'], emissions_df['CO2 Emissions (kg)'], marker='o', color='tab:red')
    plt.title("CO2 Emissions Over Time")
    plt.xlabel("Date")
    plt.ylabel("CO2 Emissions (kg)")
    plt.grid(True)
    st.pyplot(plt)

    # 2. Percentage of CO2 Emissions by Transport Type (Pie Chart)
    emissions_by_transport = emissions_df.groupby('Transport Type')['CO2 Emissions (kg)'].sum()
    plt.figure(figsize=(8, 8))
    emissions_by_transport.plot(kind='pie', autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
    plt.title("Percentage of CO2 Emissions by Transport Type")
    st.pyplot(plt)

    # 3. CO2 Emissions Decrease Trend (Moving Average)
    emissions_df['CO2 Emissions (kg) MA'] = emissions_df['CO2 Emissions (kg)'].rolling(window=5).mean()

    plt.figure(figsize=(10, 6))
    plt.plot(emissions_df['Date'], emissions_df['CO2 Emissions (kg)'], label='CO2 Emissions', color='tab:blue')
    plt.plot(emissions_df['Date'], emissions_df['CO2 Emissions (kg) MA'], label='Moving Average (5 days)', color='tab:orange')
    plt.title("CO2 Emissions Trend (with Moving Average)")
    plt.xlabel("Date")
    plt.ylabel("CO2 Emissions (kg)")
    plt.legend()
    plt.grid(True)
    st.pyplot(plt)

    # 4. Distance vs CO2 Emissions (Scatter Plot with Regression Line)
    plt.figure(figsize=(10, 6))
    sns.regplot(x='Distance (km)', y='CO2 Emissions (kg)', data=emissions_df, scatter_kws={'color': 'tab:green'}, line_kws={'color': 'tab:red'})
    plt.title("Distance vs CO2 Emissions")
    plt.xlabel("Distance (km)")
    plt.ylabel("CO2 Emissions (kg)")
    st.pyplot(plt)

    # 5. Emissions by Transport Type Over Time (Stacked Line Plot)
    emissions_by_transport_type = emissions_df.pivot_table(index='Date', columns='Transport Type', values='CO2 Emissions (kg)', aggfunc='sum')
    emissions_by_transport_type.plot(kind='area', stacked=True, figsize=(10, 6), cmap='tab20')
    plt.title("CO2 Emissions by Transport Type Over Time")
    plt.xlabel("Date")
    plt.ylabel("CO2 Emissions (kg)")
    plt.grid(True)
    st.pyplot(plt)

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
            add_emission(st.session_state["user_id"], date, distance, transport_type)
            st.success("Emission data added!")

        # Display the graphs for CO2 emissions and trips
        st.subheader("CO2 Emissions Trend")
        display_graphs(st.session_state["user_id"])

        # Show the table with individual emission entries
        st.subheader("Emission Entries")
        emissions_df = fetch_emissions(st.session_state["user_id"])
        if not emissions_df.empty:
            st.write(emissions_df)
        else:
            st.info("No emission entries yet.")

        # Calculate and display average emissions
        average_emissions = calculate_average_emissions(st.session_state["user_id"])
        st.subheader(f"Your Average CO2 Emissions: {average_emissions:.2f} kg")
        
        # Get the latest emission entry to compare
        if not emissions_df.empty:
            latest_emission = emissions_df.iloc[-1]
            feedback = generate_improvement_feedback(st.session_state["user_id"])
            st.write(f"Your last entry was {latest_emission['CO2 Emissions (kg)']} kg CO2. {feedback}")
        else:
            st.info("No emission entries yet. Please add your first emission entry!")

        # Display user tips for CO2 reduction
        display_user_tips(transport_type)

        # Generate the report (PDF)
        if st.button("Generate Report"):
            generate_report(st.session_state["user_id"])

        # Display additional analytical visualizations
        st.subheader("Additional Analytical Insights")
        display_additional_visualizations(st.session_state["user_id"])

if __name__ == "__main__":
    main()
