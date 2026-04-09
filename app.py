import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import altair as alt

# --- 1. SETTINGS & GEODATA ---
st.set_page_config(page_title="Heat Perception Map", page_icon="🌡️", layout="wide")

# Standard Indian Cities Dictionary (Instant Fallback)
CITY_FALLBACK = {
    "Mumbai": [19.0760, 72.8777],
    "Agra": [27.1767, 78.0081],
    "Delhi": [28.6139, 77.2090],
    "Pune": [18.5204, 73.8567],
    "Bangalore": [12.9716, 77.5946],
    "Chennai": [13.0827, 80.2707],
    "Kolkata": [22.5726, 88.3639],
    "Hyderabad": [17.3850, 78.4867]
}

def get_location_smart(city_name):
    name_clean = city_name.strip().title()
    if name_clean in CITY_FALLBACK:
        return CITY_FALLBACK[name_clean][0], CITY_FALLBACK[name_clean][1]
    try:
        geolocator = Nominatim(user_agent="wri_heat_tracker_2026") 
        location = geolocator.geocode(city_name, timeout=5)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return 20.5937, 78.9629 # Default: Center of India

def calculate_heat_index(T, rh):
    """Rothfusz Regression for Heat Index"""
    return -8.7846947556 + 1.61139411 * T + 2.33854883889 * rh + \
           -0.14611605 * T * rh + -0.012308094 * (T**2) + \
           -0.0164248277778 * (rh**2) + 0.002211732 * (T**2) * rh + \
           0.00072546 * T * (rh**2) + -0.000003582 * (T**2) * (rh**2)

def get_thermal_color(temp):
    if temp < 20: return "#008000"       # Green
    elif 20 <= temp < 26: return "#ADFF2F" # Greenish Yellow
    elif 26 <= temp < 32: return "#FFFF00" # Yellow
    elif 32 <= temp < 38: return "#FFA500" # Orange
    elif 38 <= temp < 46: return "#8B0000" # Deep Red
    else: return "#4B0000"                # Dark Brownish Red

# --- 2. DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. INPUT FORM ---
st.title("🌡️ Live Heat Perception Map")
st.write("How does the heat feel in your city? Add your local data to see the real-time 'Perception Gap'.")

with st.form("input_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        city_input = st.text_input("City/Area Name", placeholder="e.g., Mumbai")
        air_temp = st.number_input("Air Temperature (°C)", value=30.0, step=0.5)
    with col2:
        humidity = st.slider("Humidity (%)", 0, 100, 50)
        st.info("Humidity significantly increases how the body perceives heat.")

    submit = st.form_submit_button("Submit to Live Map")

    if submit:
        if not city_input:
            st.error("Please enter a location.")
        else:
            with st.spinner("Geocoding and saving..."):
                lat, lon = get_location_smart(city_input)
                feels_like = round(calculate_heat_index(air_temp, humidity), 1)

                new_entry = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "City": city_input,
                    "lat": lat,
                    "lon": lon,
                    "Air_Temp": air_temp,
                    "Feels_Like": feels_like
                }])

                try:
                    df = conn.read(ttl=0)
                    updated_df = pd.concat([df, new_entry], ignore_index=True) if df is not None else new_entry
                    conn.update(data=updated_df)
                    st.success(f"Added {city_input}!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- 4. VISUALIZATION ---
st.divider()
try:
    live_df = conn.read(ttl=0)
    if live_df is not None and not live_df.empty:
        
        # 1. THE MAP
        st.subheader("🌍 Live Thermal Distribution")
        live_df['color'] = live_df['Feels_Like'].apply(get_thermal_color)
        st.map(live_df, size=60, color='color')
        st.caption("Dots colored by 'Feels Like' temperature: 🟢 <20° | 🟡 26-32° | 🟠 32-38° | 🔴 38-46° | 🟤 >46°")

        # 2. THE BAR CHART
        st.subheader("Perception Gap: Air Temp vs. Body Stress")
        plot_df = live_df.tail(10)[['City', 'Air_Temp', 'Feels_Like']].copy()
        chart_data = plot_df.melt(id_vars=["City"], value_vars=["Air_Temp", "Feels_Like"],
                                 var_name="Type", value_name="Temp")

        bar_chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('City:N', title="Location"),
            y=alt.Y('Temp:Q', title="Temperature (°C)"),
            xOffset='Type:N',
            color=alt.Color('Type:N', 
                            scale=alt.Scale(domain=['Air_Temp', 'Feels_Like'], 
                                           range=['#FFD700', '#E63946']),
                            legend=alt.Legend(title="Type")),
            tooltip=['City', 'Type', 'Temp']
        ).properties(height=400)

        st.altair_chart(bar_chart, use_container_width=True)

except:
    st.info("Awaiting the first participant entry...")
