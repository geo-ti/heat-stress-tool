import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. SETTINGS & CALCULATIONS ---
st.set_page_config(page_title="Heat Perception Tool", page_icon="🌡️", layout="wide")

def calculate_heat_index(T, rh):
    """Formula for Heat Index (Apparent Temperature)"""
    return -8.7846947556 + 1.61139411 * T + 2.33854883889 * rh + \
           -0.14611605 * T * rh + -0.012308094 * (T**2) + \
           -0.0164248277778 * (rh**2) + 0.002211732 * (T**2) * rh + \
           0.00072546 * T * (rh**2) + -0.000003582 * (T**2) * (rh**2)

# --- 2. DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. HEADER & INTRO ---
st.title("🌡️ Heat Perception: Live Session")
st.write("How does your city feel today? Help us map the 'Perception Gap' by entering your local conditions.")

# --- 4. DATA ENTRY FORM ---
with st.form("input_form", clear_on_submit=True):
    st.subheader("Step 1: Your Current Conditions")
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        city_name = st.text_input("City/Location Name", placeholder="e.g. Mumbai")
        air_temp = st.number_input("Air Temperature (°C)", min_value=15, max_value=55, value=30)
    
    with col_input2:
        humidity = st.slider("Humidity (%)", 0, 100, 50)
        surface = st.selectbox("What are you standing on?", ["Asphalt/Road", "Grass/Park", "Cool Roof", "Indoor/Office"])

    submit_button = st.form_submit_button("Submit to Live Dashboard")

    if submit_button:
        if not city_name:
            st.error("Please enter a city name.")
        else:
            # Calculation Logic
            feels_like_base = calculate_heat_index(air_temp, humidity)
            surface_factor = 5 if surface == "Asphalt/Road" else -2 if surface == "Grass/Park" else 0
            final_score = round(feels_like_base + surface_factor, 1)

            # Create new entry
            new_entry = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "City": city_name,
                "Air_Temp": air_temp,
                "Humidity": humidity,
                "Surface": surface,
                "Feels_Like": final_score
            }])

            try:
                # READ existing data (ttl=0 ensures we don't use a cached old version)
                existing_data = conn.read(ttl=0)
                
                # APPEND logic
                if existing_data is not None and not existing_data.empty:
                    # Filter out empty or all-NA columns before concatenating
                    existing_data = existing_data.dropna(axis=1, how='all')
                    updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                else:
                    updated_df = new_entry

                # WRITE back to Google Sheets
                conn.update(data=updated_df)
                
                st.success(f"Successfully added {city_name}!")
                st.balloons()
                
                # Clear the internal app cache so the dashboard updates immediately
                st.cache_data.clear()
                
            except Exception as e:
                st.error(f"Error connecting to Google Sheets: {e}")

# --- 5. LIVE VISUALIZATION ---
st.divider()
st.header("📍 Live Session Dashboard")

try:
    # Always read with ttl=0 to keep the session dashboard live
    live_df = conn.read(ttl=0)
    
    if live_df is not None and not live_df.empty:
        # Metric Section
        avg_air = live_df['Air_Temp'].mean()
        avg_feels = live_df['Feels_Like'].mean()
        gap = avg_feels - avg_air
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Avg Room Air Temp", f"{round(avg_air, 1)}°C")
        m2.metric("Avg 'Feels Like' Temp", f"{round(avg_feels, 1)}°C")
        m3.metric("The Perception Gap", f"{round(gap, 1)}°C", delta_color="inverse")

        # Visualization Section
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            st.subheader("Comparison by City (Last 15 entries)")
            # Using the last 15 for better readability on screen
            chart_subset = live_df.tail(15)
            st.bar_chart(data=chart_subset, x="City", y=["Air_Temp", "Feels_Like"])
        
        with col_table:
            st.subheader("Recent Activity")
            # Show the most recent entries at the top
            st.dataframe(
                live_df[['Timestamp', 'City', 'Feels_Like']].sort_values(by="Timestamp", ascending=False), 
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("The dashboard is currently empty. Be the first to add data!")
        
except Exception as e:
    st.warning("Dashboard will be available once the first data point is submitted.")

st.divider()
st.caption("Data is collected live for educational purposes. Visualizations are based on real-time participant inputs.")
