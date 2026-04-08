import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. SETTINGS & CALCULATIONS ---
st.set_page_config(page_title="Heat Perception Tool", page_icon="🌡️")

def calculate_heat_index(T, rh):
    """Formula for Heat Index (Apparent Temperature)"""
    return -8.7846947556 + 1.61139411 * T + 2.33854883889 * rh + \
           -0.14611605 * T * rh + -0.012308094 * (T**2) + \
           -0.0164248277778 * (rh**2) + 0.002211732 * (T**2) * rh + \
           0.00072546 * T * (rh**2) + -0.000003582 * (T**2) * (rh**2)

# --- 2. DATABASE CONNECTION ---
# This looks for the secrets you added in Streamlit Cloud Settings
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. HEADER & INTRO ---
st.title("🌡️ Heat Perception: Live Session")
st.write("How does your city feel today? Add your data to help us map the 'Perception Gap'.")

# --- 4. DATA ENTRY FORM ---
with st.form("input_form"):
    st.subheader("Step 1: Your Current Conditions")
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        city_name = st.text_input("City/Location Name", placeholder="e.g. Mumbai")
        air_temp = st.number_input("Air Temperature (°C)", min_value=15, max_value=55, value=30)
    
    with col_input2:
        humidity = st.slider("Humidity (%)", 0, 100, 50)
        surface = st.selectbox("What are you standing on?", ["Asphalt/Road", "Grass/Park", "Cool Roof", "Indoor/Office"])

    submit_button = st.form_submit_button("Submit to Live Map")

    if submit_button:
        # Calculate individual 'Feels Like'
        feels_like = calculate_heat_index(air_temp, humidity)
        
        # Simple Logic: Add surface heat factor for LST context
        surface_factor = 5 if surface == "Asphalt/Road" else -2 if surface == "Grass/Park" else 0
        final_score = feels_like + surface_factor

        # Prepare data for Google Sheets
        new_entry = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "City": city_name,
            "Air_Temp": air_temp,
            "Humidity": humidity,
            "Surface": surface,
            "Feels_Like": round(final_score, 1)
        }])

        # Update the sheet
        try:
            existing_data = conn.read()
            updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"Successfully added {city_name}! Scroll down to see the results.")
            st.balloons()
        except Exception as e:
            st.error("Connection Error. Ensure your Google Sheet is shared with the Service Account email.")

# --- 5. LIVE VISUALIZATION ---
st.divider()
st.header("📍 Live Session Dashboard")

# Read the data back for the dashboard
try:
    live_df = conn.read()
    
    if not live_df.empty:
        # Metric 1: Average Gap
        avg_air = live_df['Air_Temp'].mean()
        avg_feels = live_df['Feels_Like'].mean()
        gap = avg_feels - avg_air
        
        m1, m2 = st.columns(2)
        m1.metric("Average Room Air Temp", f"{round(avg_air, 1)}°C")
        m2.metric("Average 'Feels Like' Temp", f"{round(avg_feels, 1)}°C", f"+{round(gap, 1)}°C Difference")

        # Visual 2: Comparative Bar Chart
        st.subheader("Heat Perception by City")
        chart_data = live_df.tail(10) # Show last 10 entries
        st.bar_chart(data=chart_data, x="City", y=["Air_Temp", "Feels_Like"])
        
        # Visual 3: Raw Data Table
        st.subheader("Recent Submissions")
        st.dataframe(live_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)
    else:
        st.info("Waiting for the first entry... Be the first to contribute!")
        
except Exception as e:
    st.warning("Dashboard will appear once the first entry is submitted.")

st.caption("Powered by WRI Geospatial Research Principles | Data collected live.")
