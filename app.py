import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. SETTINGS & CALCULATIONS ---
st.set_page_config(page_title="Geospatial Heat Tool", page_icon="🌍", layout="wide")

def calculate_heat_index(T, rh):
    """Standard Heat Index (Apparent Temperature)"""
    return -8.7846947556 + 1.61139411 * T + 2.33854883889 * rh + \
           -0.14611605 * T * rh + -0.14611605 * T * rh + \
           -0.012308094 * (T**2) + -0.0164248277778 * (rh**2) + \
           0.002211732 * (T**2) * rh + 0.00072546 * T * (rh**2) + \
           -0.000003582 * (T**2) * (rh**2)

# --- 2. DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. INPUT FORM ---
st.title("🌡️ Live Geospatial Heat Mapping")
st.write("Enter your precise coordinates and local conditions to contribute to our live thermal stress map.")

with st.form("gis_input_form", clear_on_submit=True):
    st.subheader("📍 Spatial & Thermal Data Entry")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        city_label = st.text_input("Location Label", placeholder="e.g., BKC Office, Mumbai")
        air_temp = st.number_input("Air Temp (°C)", value=32.0, step=0.5)
        
    with col2:
        # Latitude and Longitude inputs
        lat_input = st.number_input("Latitude (Decimal)", format="%.4f", value=19.0760)
        lon_input = st.number_input("Longitude (Decimal)", format="%.4f", value=72.8777)
        
    with col3:
        humidity = st.slider("Humidity (%)", 0, 100, 60)
        surface = st.selectbox("Surface Type", ["Asphalt", "Concrete", "Green Space", "Water Body", "Shaded/Indoor"])

    submit = st.form_submit_button("Log Spatial Data")

    if submit:
        # Calculate scores
        feels_base = calculate_heat_index(air_temp, humidity)
        # Adjusting for surface-level reality (LST proxy)
        surface_adj = {"Asphalt": 6, "Concrete": 4, "Green Space": -3, "Water Body": -4, "Shaded/Indoor": 0}
        final_feels = round(feels_base + surface_adj.get(surface, 0), 1)

        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%H:%M:%S"),
            "Label": city_label,
            "lat": lat_input,
            "lon": lon_input,
            "Air_Temp": air_temp,
            "Feels_Like": final_feels,
            "Surface": surface
        }])

        try:
            df = conn.read(ttl=0)
            updated_df = pd.concat([df, new_row], ignore_index=True) if df is not None else new_row
            conn.update(data=updated_df)
            st.success(f"Data point logged for {city_label}!")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. THE GEOSPATIAL DASHBOARD ---
st.divider()

try:
    live_df = conn.read(ttl=0)
    if live_df is not None and not live_df.empty:
        
        # Live Map
        st.subheader("🌍 Real-Time Thermal Distribution")
        # Scaling dot size based on how hot it feels
        live_df['dot_size'] = (live_df['Feels_Like'] - 20) * 2 
        st.map(live_df, size='dot_size', color='#E63946')

        # Data Visualization
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Perception Gap: Air vs. Surface-Adjusted Heat")
            st.bar_chart(live_df.tail(15), x="Label", y=["Air_Temp", "Feels_Like"])
        
        with c2:
            st.subheader("Latest Logs")
            st.dataframe(
                live_df[['Label', 'Surface', 'Feels_Like']].tail(8),
                hide_index=True, 
                use_container_width=True
            )
except:
    st.info("Waiting for the first GIS data point...")
