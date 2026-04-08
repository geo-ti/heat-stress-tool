import streamlit as st

def calculate_heat_index(T, rh):
    """Simple Heat Index formula (Steadman)"""
    return -8.7846947556 + 1.61139411 * T + 2.33854883889 * rh + \
           -0.14611605 * T * rh + -0.012308094 * (T**2) + \
           -0.0164248277778 * (rh**2) + 0.002211732 * (T**2) * rh + \
           0.00072546 * T * (rh**2) + -0.000003582 * (T**2) * (rh**2)

st.set_page_config(page_title="Heat Stress Tool", page_icon="🌡️")

st.title("🌡️ How Hot Does it Actually Feel?")
st.write("Input your current city conditions to see the gap between the thermometer and your body.")

# --- Sidebar Inputs ---
st.sidebar.header("Current Conditions")
city = st.sidebar.text_input("City Name", "Mumbai")
temp = st.sidebar.slider("Air Temperature (°C)", 20, 50, 32)
humidity = st.sidebar.slider("Relative Humidity (%)", 0, 100, 65)

# --- Calculations ---
feels_like = calculate_heat_index(temp, humidity)
gap = feels_like - temp

# --- Main Dashboard ---
col1, col2, col3 = st.columns(3)
col1.metric("Air Temp", f"{temp}°C")
col2.metric("Feels Like", f"{round(feels_like, 1)}°C", f"{round(gap, 1)}°C increase")
col3.metric("Humidity", f"{humidity}%")

st.divider()

# --- Interpretation Logic ---
if feels_like < 30:
    st.success("✅ **Comfortable:** Low risk of heat stress.")
elif 30 <= feels_like < 40:
    st.warning("⚠️ **Caution:** Fatigue is possible with prolonged exposure. Stay hydrated!")
elif 40 <= feels_like < 54:
    st.error("🚨 **Danger:** Heat cramps and exhaustion likely. Limit outdoor activity.")
else:
    st.critical("🛑 **Extreme Danger:** High risk of heatstroke! Seek shade and cooling immediately.")

st.info(f"**Insight:** In {city}, the 'Perception Gap' is {round(gap, 1)}°C. This means your body is working significantly harder to cool down than the air temperature suggests.")