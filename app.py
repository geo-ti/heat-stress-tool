import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

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
            # GEOCODING LOGIC
            location = geocode(city_input)
            
            if location:
                feels_base = calculate_heat_index(air_temp, humidity)
                # Surface adjustment (Simplified LST proxy)
                adj = {"Asphalt": 5, "Concrete": 3, "Green Space": -3, "Indoor": 0}
                final_score = round(feels_base + adj.get(surface, 0), 1)

                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%H:%M"),
                    "City": city_input,
                    "lat": location.latitude,
                    "lon": location.longitude,
                    "Air_Temp": air_temp,
                    "Feels_Like": final_score,
                    "Surface": surface
                }])

                try:
                    df = conn.read(ttl=0)
                    updated_df = pd.concat([df, new_row], ignore_index=True) if df is not None else new_row
                    conn.update(data=updated_df)
                    st.success(f"Mapped {city_input} successfully!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Could not find that location. Try a nearby major city name.")

# --- 4. VISUALIZATION ---
st.divider()
try:
    live_df = conn.read(ttl=0)
    if live_df is not None and not live_df.empty:
        
        # 1. THE MAP
        st.subheader("🌍 Interactive Heat Stress Map")
        st.map(live_df, size=40, color='#E63946')

        # 2. THE CUSTOM BAR CHART
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("Air Temp vs. Body Stress")
            
            # We need to "melt" the dataframe to make it Altair-friendly
            # This turns columns [Air_Temp, Feels_Like] into a 'Category' column
            chart_data = live_df.tail(10).melt(
                id_vars=["City"], 
                value_vars=["Air_Temp", "Feels_Like"],
                var_name="Measurement", 
                value_name="Temperature"
            )

            # Creating the Altair Chart
            bar_chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X("Measurement:N", title=None, axis=alt.Axis(labels=False)), # Hides internal labels
                y=alt.Y("Temperature:Q", title="Temperature (°C)"),
                color=alt.Color("Measurement:N", 
                                scale=alt.Scale(domain=["Air_Temp", "Feels_Like"], 
                                               range=["#FFD700", "#E63946"]), # Yellow and Red
                                legend=alt.Legend(title="Type")),
                column=alt.Column("City:N", title="Location", spacing=10) # Groups bars by City
            ).properties(width=80, height=300)

            st.altair_chart(bar_chart)

        with c2:
            st.subheader("Live Submissions")
            st.dataframe(live_df[['City', 'Feels_Like', 'Surface']].tail(8), hide_index=True)

except Exception as e:
    st.info(f"Awaiting the first submission... (System Check: {e})")
