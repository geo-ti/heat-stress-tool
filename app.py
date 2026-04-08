import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. SETTINGS & GEODATA ---
st.set_page_config(page_title="Heat Perception Tool", page_icon="🌡️", layout="wide")

# Simple geocoding helper for a live session
def get_coords(city):
    city = city.strip().title()
    # Dictionary of major Indian cities for instant geocoding
    geo_dict = {
        "Mumbai": [19.0760, 72.8777],
        "Delhi": [28.6139, 77.2090],
        "Bangalore": [12.9716, 77.5946],
        "Chennai": [13.0827, 80.2707],
        "Kolkata": [22.5726, 88.3639],
        "Hyderabad": [17.3850, 78.4867],
        "Pune": [18.5204, 73.8567],
        "Ahmedabad": [23.0225, 72.5714],
        "Lucknow": [26.8467, 80.9462],
        "Jaipur": [26.9124, 75.7873]
    }
    # Return coords if in dict, else default to a central India point or skip
    return geo_dict.get(city, [20.5937, 78.9629]) 

def calculate_heat_index(T, rh):
    return -8.7846947556 + 1.61139411 * T + 2.33854883889 * rh + \
           -0.14611605 * T * rh + -0.012308094 * (T**2) + \
           -0.0164248277778 * (rh**2) + 0.002211732 * (T**2) * rh + \
           0.00072546 * T * (rh**2) + -0.000003582 * (T**2) * (rh**2)

# --- 2. DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. DATA ENTRY FORM ---
st.title("🌡️ Heat Perception Live Map")

with st.form("input_form", clear_on_submit=True):
    st.subheader("Add Your Local Conditions")
    col1, col2 = st.columns(2)
    with col1:
        city_name = st.text_input("City Name (e.g., Mumbai, Delhi)")
        air_temp = st.number_input("Air Temp (°C)", value=30)
    with col2:
        humidity = st.slider("Humidity (%)", 0, 100, 50)
        surface = st.selectbox("Surface Type", ["Asphalt", "Grass", "Cool Roof", "Indoor"])

    if st.form_submit_button("Submit"):
        if city_name:
            coords = get_coords(city_name)
            feels = round(calculate_heat_index(air_temp, humidity), 1)
            
            new_entry = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "City": city_name,
                "Air_Temp": air_temp,
                "Feels_Like": feels,
                "lat": coords[0],
                "lon": coords[1]
            }])

            try:
                df = conn.read(ttl=0)
                updated_df = pd.concat([df, new_entry], ignore_index=True) if df is not None else new_entry
                conn.update(data=updated_df)
                st.success(f"Added {city_name}!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error: {e}")

# --- 4. VISUALIZATION DASHBOARD ---
st.divider()
try:
    live_df = conn.read(ttl=0)
    if live_df is not None and not live_df.empty:
        
        # --- ROW 1: THE MAP ---
        st.subheader("📍 Live Heat Map (Session Participants)")
        # st.map automatically looks for columns named 'lat' and 'lon'
        st.map(live_df, size=20, color='#ff4b4b') 

        # --- ROW 2: THE CHARTS ---
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("City Comparison")
            st.bar_chart(live_df.tail(10), x="City", y=["Air_Temp", "Feels_Like"])
        
        with col_right:
            st.subheader("Recent Submissions")
            st.dataframe(live_df[['City', 'Air_Temp', 'Feels_Like']].tail(5))
except:
    st.info("Awaiting first submission...")
