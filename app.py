import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Standard Indian Cities Dictionary (Fallback/Instant)
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
    
    # Check if it's in our local dictionary first (instant)
    if name_clean in CITY_FALLBACK:
        return CITY_FALLBACK[name_clean][0], CITY_FALLBACK[name_clean][1]
    
    # If not, try the live geocoder
    try:
        # Change the user_agent to something very unique here!
        geolocator = Nominatim(user_agent="wri_heat_tool_v2_2026") 
        location = geolocator.geocode(city_name, timeout=5)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    
    # Absolute Fallback (Central India) so the app never fails
    return 20.5937, 78.9629

# --- 1. SETTINGS & CALCULATIONS ---
st.set_page_config(page_title="Heat Perception Map", page_icon="🌡️", layout="wide")

# Initialize Geocoder
geolocator = Nominatim(user_agent="heat_session_tool")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def calculate_heat_index(T, rh):
    return -8.7846947556 + 1.61139411 * T + 2.33854883889 * rh + \
           -0.14611605 * T * rh + -0.012308094 * (T**2) + \
           -0.0164248277778 * (rh**2) + 0.002211732 * (T**2) * rh + \
           0.00072546 * T * (rh**2) + -0.000003582 * (T**2) * (rh**2)

# --- 2. DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. INPUT FORM ---
st.title("🌡️ Live Heat Perception Map")
st.write("Type your city name and current conditions to see how heat varies across the region.")

with st.form("input_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        city_input = st.text_input("Enter your City/Area", placeholder="e.g., Bandra, Mumbai")
        air_temp = st.number_input("Air Temp (°C)", value=32.0)
    with col2:
        humidity = st.slider("Humidity (%)", 0, 100, 60)
        surface = st.selectbox("Surface Type", ["Asphalt", "Concrete", "Green Space", "Indoor"])

    submit = st.form_submit_button("Submit Location & Data")

    if submit:
        if not city_input:
            st.error("Please enter a location name.")
        else:
            with st.spinner("Processing Location..."):
                # Use our new smart function
                lat, lon = get_location_smart(city_input)
                
                # The rest of your calculation logic
                feels_base = calculate_heat_index(air_temp, humidity)
                adj = {"Asphalt": 5, "Concrete": 3, "Green Space": -3, "Indoor": 0}
                final_score = round(feels_base + adj.get(surface, 0), 1)

                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%H:%M"),
                    "City": city_input,
                    "lat": lat,
                    "lon": lon,
                    "Air_Temp": air_temp,
                    "Feels_Like": final_score,
                    "Surface": surface
                }])

                try:
                    df = conn.read(ttl=0)
                    updated_df = pd.concat([df, new_row], ignore_index=True) if df is not None else new_row
                    conn.update(data=updated_df)
                    st.success(f"Added {city_input} to map!")
                    st.cache_data.clear()
                    st.rerun() # Forces the charts to update immediately
                except Exception as e:
                    st.error(f"Save Error: {e}")

# --- 4. VISUALIZATION DASHBOARD ---
st.divider()
try:
    # Read the latest data
    live_df = conn.read(ttl=0)
    
    if live_df is not None and not live_df.empty:
        
        # 1. THE MAP
        st.subheader("🌍 Interactive Heat Stress Map")
        st.map(live_df, size=40, color='#E63946')

        # 2. THE CUSTOM BAR CHART
        st.subheader("Air Temp (Yellow) vs. Body Stress (Red)")
        
        # --- DATA PREP ---
        # Get the last 10 entries and only the columns we need
        plot_df = live_df.tail(10)[['City', 'Air_Temp', 'Feels_Like']].copy()
        
        # Melt the data: This turns it from "Wide" to "Long" format for Altair
        chart_data = plot_df.melt(
            id_vars=["City"], 
            value_vars=["Air_Temp", "Feels_Like"],
            var_name="Type", 
            value_name="Temp"
        )

        # --- ALTAIR CHART ---
        # We use xOffset to put the bars side-by-side
        combined_chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('City:N', title="Location"),
            y=alt.Y('Temp:Q', title="Temperature (°C)", scale=alt.Scale(domainMin=0)),
            xOffset='Type:N',  # This creates the side-by-side (grouped) effect
            color=alt.Color('Type:N', 
                            scale=alt.Scale(domain=['Air_Temp', 'Feels_Like'], 
                                           range=['#FFD700', '#E63946']),
                            legend=alt.Legend(title="Measurement")),
            tooltip=['City', 'Type', 'Temp']
        ).properties(
            width=alt.Step(40),  # Adjusts bar width
            height=400
        ).configure_view(
            stroke=None
        )

        st.altair_chart(combined_chart, use_container_width=True)

        # 3. RAW DATA TABLE
        st.subheader("Recent Submissions")
        st.dataframe(live_df[['Timestamp', 'City', 'Surface', 'Feels_Like']].tail(10), hide_index=True, use_container_width=True)

    else:
        st.info("The dashboard is currently empty. Be the first to add data!")
        
except Exception as e:
    # This will help us debug if it still fails
    st.error(f"Visualization Error: {e}")
    st.write("Current Data Preview:", live_df.tail(5) if 'live_df' in locals() else "No data found")
