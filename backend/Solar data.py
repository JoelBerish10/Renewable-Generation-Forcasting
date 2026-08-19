import os
import joblib
import numpy as np
import pandas as pd
import requests
import xgboost as xgb

# Site coordinates (Panvel, Raigad, Maharashtra)
LATITUDE = 18.9894
LONGITUDE = 73.1175

# Set export directory to current script location
script_dir = (
    os.path.dirname(os.path.abspath(__file__))
    if "__file__" in locals()
    else os.getcwd()
)

# =====================================================================
# Step 1: Fetch 1 Year of Historical Weather Data (8,760 Hours)
# =====================================================================
print("--- Step 1: Fetching 1 Year of Historical Data ---")
archive_url = "https://archive-api.open-meteo.com/v1/archive"
archive_params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "hourly": "shortwave_radiation,temperature_2m,relative_humidity_2m",
    "timezone": "Asia/Kolkata",
}

res_hist = requests.get(archive_url, params=archive_params)
data_hist = res_hist.json()

df_year = pd.DataFrame({
    "timestamp": pd.to_datetime(data_hist["hourly"]["time"]),
    "ghi": data_hist["hourly"]["shortwave_radiation"],
    "temperature": data_hist["hourly"]["temperature_2m"],
    "humidity": data_hist["hourly"]["relative_humidity_2m"],
})

# =====================================================================
# Step 2: Feature Engineering & Target Generation
# =====================================================================
print("\n--- Step 2: Feature Engineering ---")
hours = df_year["timestamp"].dt.hour.to_numpy()
months = df_year["timestamp"].dt.month.to_numpy()

df_year["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
df_year["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)
df_year["month_sin"] = np.sin(2 * np.pi * months / 12.0)
df_year["month_cos"] = np.cos(2 * np.pi * months / 12.0)

# Target generation (5 kWp array yield with thermal loss)
df_year["power_kw"] = np.maximum(
    0, df_year["ghi"] * 0.005 * (1 - 0.004 * (df_year["temperature"] - 25))
)

features = [
    "ghi",
    "temperature",
    "humidity",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
]

# =====================================================================
# Step 3: Train XGBoost Model & Export Annual CSVs
# =====================================================================
print("\n--- Step 3: Training XGBoost Model ---")
model = xgb.XGBRegressor(
    n_estimators=200,
    learning_rate=0.04,
    max_depth=6,
    subsample=0.8,
    random_state=42,
)
model.fit(df_year[features], df_year["power_kw"])

# Run annual predictions
df_year["predicted_power_kw"] = model.predict(df_year[features])
df_year["predicted_power_kw"] = np.where(
    df_year["ghi"] == 0, 0, np.maximum(0, df_year["predicted_power_kw"])
)

# Save Model .pkl
joblib.dump(model, os.path.join(script_dir, "solar_xgboost_model.pkl"))

# Save 1-Year Hourly Predictions
df_year.to_csv(
    os.path.join(script_dir, "solar_full_year_8760_hourly.csv"), index=False
)

# Save 1-Year Daily Totals
df_year["date"] = df_year["timestamp"].dt.date
annual_daily_summary = (
    df_year.groupby("date")
    .agg(
        total_energy_kwh=("predicted_power_kw", "sum"),
        peak_power_kw=("predicted_power_kw", "max"),
        max_ghi_w_m2=("ghi", "max"),
        avg_temp_c=("temperature", "mean"),
    )
    .reset_index()
)
annual_daily_summary.to_csv(
    os.path.join(script_dir, "solar_full_year_daily_summary.csv"), index=False
)
print("Saved 1-Year CSVs and 'solar_xgboost_model.pkl' to disk.")

# =====================================================================
# Step 4: Fetch Live 7-Day Forecast & Export Forecast CSVs
# =====================================================================
print("\n--- Step 4: Fetching Live 7-Day Forecast ---")
forecast_url = "https://api.open-meteo.com/v1/forecast"
forecast_params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "hourly": "shortwave_radiation,temperature_2m,relative_humidity_2m",
    "timezone": "Asia/Kolkata",
    "forecast_days": 7,
}

res_fc = requests.get(forecast_url, params=forecast_params)
data_fc = res_fc.json()

df_forecast = pd.DataFrame({
    "timestamp": pd.to_datetime(data_fc["hourly"]["time"]),
    "ghi": data_fc["hourly"]["shortwave_radiation"],
    "temperature": data_fc["hourly"]["temperature_2m"],
    "humidity": data_fc["hourly"]["relative_humidity_2m"],
})

hours_fc = df_forecast["timestamp"].dt.hour.to_numpy()
months_fc = df_forecast["timestamp"].dt.month.to_numpy()

df_forecast["hour_sin"] = np.sin(2 * np.pi * hours_fc / 24.0)
df_forecast["hour_cos"] = np.cos(2 * np.pi * hours_fc / 24.0)
df_forecast["month_sin"] = np.sin(2 * np.pi * months_fc / 12.0)
df_forecast["month_cos"] = np.cos(2 * np.pi * months_fc / 12.0)

df_forecast["predicted_power_kw"] = model.predict(df_forecast[features])
df_forecast["predicted_power_kw"] = np.where(
    df_forecast["ghi"] == 0,
    0,
    np.maximum(0, df_forecast["predicted_power_kw"]),
)

df_forecast["date"] = df_forecast["timestamp"].dt.date
forecast_daily_summary = (
    df_forecast.groupby("date")
    .agg(
        total_energy_kwh=("predicted_power_kw", "sum"),
        peak_power_kw=("predicted_power_kw", "max"),
        max_ghi_w_m2=("ghi", "max"),
        avg_temp_c=("temperature", "mean"),
    )
    .reset_index()
)

# Save 7-Day Forecast CSVs
df_forecast.to_csv(
    os.path.join(script_dir, "solar_7day_hourly_forecast.csv"), index=False
)
forecast_daily_summary.to_csv(
    os.path.join(script_dir, "solar_7day_daily_summary.csv"), index=False
)

print("\n--- 7-Day Live Solar Generation Forecast ---")
print(forecast_daily_summary.to_string(index=False))
print("\nSUCCESS: All annual and 7-day forecast files generated successfully!")