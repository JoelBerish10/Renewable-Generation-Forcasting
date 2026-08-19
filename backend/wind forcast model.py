"""
RenewCast — Wind Panel Forecasting Model (real weather data)
==============================================================
Pulls ONE YEAR of real historical weather from Open-Meteo (free, no API
key, ERA5 reanalysis back to 1940), trains an XGBoost model, then pulls
the NEXT 7 DAYS forecast from Open-Meteo and predicts total expected
wind output for that week.

IMPORTANT — what's real and what's estimated
----------------------------------------------
- Weather (wind speed, direction, temperature, humidity, pressure) is
  REAL, pulled live from Open-Meteo for your exact coordinates.
- "power" (historical generation) is NOT available from any free public
  API for an arbitrary site — that's private SCADA data. So the power
  label used to train the model is derived from real wind speed using a
  standard IEC-style turbine power curve (cut-in / rated / cut-out
  speeds) plus a wind-shear correction from 10 m to hub height. This is
  a normal engineering approximation, not random synthetic noise — but
  it is an approximation, not measured generation. Swap in real SCADA
  history via --data if/when you have it and the model instantly
  becomes more accurate.

ESSENTIAL PARAMETERS (unchanged from before):
    timestamp, wind_speed, wind_direction, temperature, humidity,
    pressure, power (historical), rated_capacity_mw

--------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------
1. Install dependencies (once):
       pip install xgboost scikit-learn pandas numpy joblib requests

2. Edit LOCATION / DEFAULTS below (already set to Panvel, Raigad, MH).

3. Run:
       python "forcast model.py"

   This fetches 1 year of real historical weather for the configured
   location, trains the model, fetches the next 7 days forecast, and
   prints hourly + daily + total weekly expected output (gross & net).

4. To use your own real generation data instead of the power-curve
   estimate, pass --data with a CSV of columns:
       timestamp, wind_speed, wind_direction, temperature, humidity,
       pressure, power
   and the script will use that instead of fetching+estimating.
--------------------------------------------------------------------------
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import requests
    from xgboost import XGBRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    import joblib
except ModuleNotFoundError as e:
    sys.exit(
        f"\nMissing package: {e.name}\n"
        f"Install everything needed with:\n\n"
        f"    pip install xgboost scikit-learn pandas numpy joblib requests\n"
    )

# ---------------------------------------------------------------------------
# EDIT-ME: location + asset defaults
# ---------------------------------------------------------------------------
DEFAULTS = {
    "data": None,              # set to a CSV path to use real generation data instead
    "latitude": 18.99,          # Panvel, Raigad, Maharashtra
    "longitude": 73.12,
    "capacity": 10.0,           # rated capacity, MW
    "loss_pct": 6.5,            # overall system loss, %
    "history_days": 365,        # how much history to pull
    "forecast_days": 7,         # how far ahead to predict
    "hub_height_m": 80,         # for wind-shear correction, 10m -> hub height
    "cut_in": 3.5,               # turbine power-curve params, m/s
    "rated_speed": 13,
    "cut_out": 25,
}

HOURLY_VARS = "wind_speed_10m,wind_direction_10m,temperature_2m,relative_humidity_2m,surface_pressure"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

REQUIRED_COLUMNS = ["timestamp", "wind_speed", "wind_direction", "temperature", "humidity", "pressure", "power"]
FEATURE_COLUMNS = [
    "wind_speed", "temperature", "humidity", "pressure",
    "hour_sin", "hour_cos", "month_sin", "month_cos",
    "wind_dir_sin", "wind_dir_cos",
    "lag_1h", "lag_2h", "lag_24h", "rolling_mean_6h",
]
MODEL_CACHE_PATH = Path(__file__).parent / "ml" / "saved_models" / "wind_model.joblib"


# ---------------------------------------------------------------------------
# 1. Real weather fetching (Open-Meteo — free, no API key)
# ---------------------------------------------------------------------------
def _fetch_open_meteo(url: str, lat: float, lon: float, extra_params: dict) -> pd.DataFrame:
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": HOURLY_VARS,
        "wind_speed_unit": "ms",
        "timezone": "auto",
        **extra_params,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    hourly = resp.json()["hourly"]
    return pd.DataFrame({
        "timestamp": hourly["time"],
        "wind_speed": hourly["wind_speed_10m"],
        "wind_direction": hourly["wind_direction_10m"],
        "temperature": hourly["temperature_2m"],
        "humidity": hourly["relative_humidity_2m"],
        "pressure": hourly["surface_pressure"],
    })


def fetch_historical_weather(lat: float, lon: float, history_days: int) -> pd.DataFrame:
    """Real ERA5 reanalysis weather. Archive has ~5-day latency, so we
    end just before that to avoid requesting unavailable days."""
    end_date = date.today() - timedelta(days=5)
    start_date = end_date - timedelta(days=history_days)
    print(f"[i] Fetching {history_days} days of real historical weather "
          f"({start_date} to {end_date}) for ({lat}, {lon})...")
    df = _fetch_open_meteo(ARCHIVE_URL, lat, lon, {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    })
    print(f"[i] Received {len(df)} hourly records.\n")
    return df


def fetch_forecast_weather(lat: float, lon: float, forecast_days: int) -> pd.DataFrame:
    print(f"[i] Fetching {forecast_days}-day real weather forecast for ({lat}, {lon})...")
    df = _fetch_open_meteo(FORECAST_URL, lat, lon, {"forecast_days": forecast_days})
    print(f"[i] Received {len(df)} hourly forecast records.\n")
    return df


# ---------------------------------------------------------------------------
# 2. Turbine power curve — derives a power label from real wind speed
#    (used only when the user hasn't supplied real SCADA generation data)
# ---------------------------------------------------------------------------
def wind_shear_to_hub_height(v10: np.ndarray, hub_height_m: float, alpha: float = 1 / 7) -> np.ndarray:
    """Power-law extrapolation of wind speed from 10 m to hub height."""
    return v10 * (hub_height_m / 10) ** alpha


def turbine_power_curve(v_hub: np.ndarray, cut_in: float, rated_speed: float, cut_out: float) -> np.ndarray:
    """Standard cubic-ramp IEC-style power curve -> normalized output (0-1)."""
    p = np.zeros_like(v_hub, dtype=float)
    ramp = (v_hub >= cut_in) & (v_hub < rated_speed)
    p[ramp] = ((v_hub[ramp] - cut_in) / (rated_speed - cut_in)) ** 3
    p[(v_hub >= rated_speed) & (v_hub < cut_out)] = 1.0
    return p


def estimate_power_from_weather(df: pd.DataFrame, rated_capacity_mw: float, cfg: dict) -> pd.DataFrame:
    df = df.copy()
    v_hub = wind_shear_to_hub_height(df["wind_speed"].values, cfg["hub_height_m"])
    normalized = turbine_power_curve(v_hub, cfg["cut_in"], cfg["rated_speed"], cfg["cut_out"])
    df["power"] = normalized * rated_capacity_mw
    return df


# ---------------------------------------------------------------------------
# 3. Feature engineering (unchanged)
# ---------------------------------------------------------------------------
def engineer_features(df: pd.DataFrame, rated_capacity_mw: float) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["hour"] = df["timestamp"].dt.hour
    df["month"] = df["timestamp"].dt.month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    df["wind_dir_sin"] = np.sin(2 * np.pi * df["wind_direction"] / 360)
    df["wind_dir_cos"] = np.cos(2 * np.pi * df["wind_direction"] / 360)

    df["normalized_output"] = (df["power"] / rated_capacity_mw).clip(0, 1)

    df["lag_1h"] = df["normalized_output"].shift(1)
    df["lag_2h"] = df["normalized_output"].shift(2)
    df["lag_24h"] = df["normalized_output"].shift(24)
    df["rolling_mean_6h"] = df["normalized_output"].shift(1).rolling(6).mean()

    return df.dropna().reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Train / evaluate (chronological split — no future leakage)
# ---------------------------------------------------------------------------
def train_model(df: pd.DataFrame, use_cache: bool = True):
    split_idx = int(len(df) * 0.8)
    train, test = df.iloc[:split_idx], df.iloc[split_idx:]

    X_train, y_train = train[FEATURE_COLUMNS], train["normalized_output"]
    X_test, y_test = test[FEATURE_COLUMNS], test["normalized_output"]

    model = XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
    )
    model.fit(X_train, y_train)

    preds = np.clip(model.predict(X_test), 0, 1)
    metrics = {
        "MAE": mean_absolute_error(y_test, preds),
        "RMSE": mean_squared_error(y_test, preds) ** 0.5,
        "R2": r2_score(y_test, preds),
    }
    residual_std = float(np.std(y_test.values - preds))

    if use_cache:
        MODEL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "metrics": metrics, "residual_std": residual_std}, MODEL_CACHE_PATH)

    return model, metrics, residual_std


# ---------------------------------------------------------------------------
# 5. Loss engine
# ---------------------------------------------------------------------------
def apply_losses(gross_mw: float, loss_pct: float) -> dict:
    loss_mw = gross_mw * (loss_pct / 100)
    return {"loss_mw": round(loss_mw, 3), "net_power_mw": round(gross_mw - loss_mw, 3)}


# ---------------------------------------------------------------------------
# 6. Predict across the next N days, hour by hour, using real forecast data
# ---------------------------------------------------------------------------
def predict_week(model, df_hist_features: pd.DataFrame, residual_std: float,
                  rated_capacity_mw: float, loss_pct: float,
                  forecast_raw: pd.DataFrame) -> pd.DataFrame:
    forecast_raw = forecast_raw.copy()
    forecast_raw["timestamp"] = pd.to_datetime(forecast_raw["timestamp"])

    # seed lag/rolling context from the tail of history, then roll forward
    normalized_history = list(df_hist_features["normalized_output"].values[-24:])

    rows = []
    for _, r in forecast_raw.iterrows():
        ts = r["timestamp"]
        row = {
            "wind_speed": r["wind_speed"],
            "temperature": r["temperature"],
            "humidity": r["humidity"],
            "pressure": r["pressure"],
            "hour_sin": np.sin(2 * np.pi * ts.hour / 24),
            "hour_cos": np.cos(2 * np.pi * ts.hour / 24),
            "month_sin": np.sin(2 * np.pi * ts.month / 12),
            "month_cos": np.cos(2 * np.pi * ts.month / 12),
            "wind_dir_sin": np.sin(2 * np.pi * r["wind_direction"] / 360),
            "wind_dir_cos": np.cos(2 * np.pi * r["wind_direction"] / 360),
            "lag_1h": normalized_history[-1],
            "lag_2h": normalized_history[-2],
            "lag_24h": normalized_history[-24],
            "rolling_mean_6h": float(np.mean(normalized_history[-6:])),
        }
        X = pd.DataFrame([row])[FEATURE_COLUMNS]
        normalized_pred = float(np.clip(model.predict(X)[0], 0, 1))
        normalized_history.append(normalized_pred)

        gross_mw = normalized_pred * rated_capacity_mw
        losses = apply_losses(gross_mw, loss_pct)
        lower = max(0, normalized_pred - residual_std) * rated_capacity_mw
        upper = min(1, normalized_pred + residual_std) * rated_capacity_mw

        rows.append({
            "timestamp": ts, "wind_speed": r["wind_speed"],
            "normalized_output": round(normalized_pred, 4),
            "gross_power_mw": round(gross_mw, 3),
            "net_power_mw": losses["net_power_mw"],
            "range_lower_mw": round(lower, 3),
            "range_upper_mw": round(upper, 3),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 7. CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="RenewCast Wind Output Forecast — real weather, 1yr -> next week")
    parser.add_argument("--data", type=str, default=DEFAULTS["data"], help="Optional: real generation-history CSV")
    parser.add_argument("--latitude", type=float, default=DEFAULTS["latitude"])
    parser.add_argument("--longitude", type=float, default=DEFAULTS["longitude"])
    parser.add_argument("--capacity", type=float, default=DEFAULTS["capacity"])
    parser.add_argument("--loss_pct", type=float, default=DEFAULTS["loss_pct"])
    parser.add_argument("--history_days", type=int, default=DEFAULTS["history_days"])
    parser.add_argument("--forecast_days", type=int, default=DEFAULTS["forecast_days"])
    parser.add_argument("--no_cache", action="store_true", help="Force retraining even if a cached model exists")
    args = parser.parse_args()

    cfg = {**DEFAULTS, "capacity": args.capacity}

    # --- get historical data (real weather always; power = real if --data given, else estimated) ---
    if args.data:
        raw = pd.read_csv(args.data)
        missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
        if missing:
            sys.exit(f"Dataset missing required columns: {missing}")
        print(f"[i] Using real generation history from {args.data}\n")
    else:
        weather_hist = fetch_historical_weather(args.latitude, args.longitude, args.history_days)
        raw = estimate_power_from_weather(weather_hist, args.capacity, cfg)
        print("[!] No real generation CSV given — 'power' is estimated from real wind speed "
              "via a turbine power curve, not measured generation. Pass --data to use real "
              "SCADA history if you have it.\n")

    df = engineer_features(raw, args.capacity)

    if MODEL_CACHE_PATH.exists() and not args.no_cache:
        cached = joblib.load(MODEL_CACHE_PATH)
        model, metrics, residual_std = cached["model"], cached["metrics"], cached["residual_std"]
        print(f"[i] Loaded cached model from {MODEL_CACHE_PATH} (use --no_cache to force retraining)\n")
    else:
        model, metrics, residual_std = train_model(df)

    print("Model evaluation (held-out, chronological split):")
    print(f"  MAE  : {metrics['MAE']:.4f}  (normalized units)")
    print(f"  RMSE : {metrics['RMSE']:.4f}")
    print(f"  R2   : {metrics['R2']:.4f}\n")

    # --- real forecast for the next N days ---
    forecast_raw = fetch_forecast_weather(args.latitude, args.longitude, args.forecast_days)
    result = predict_week(model, df, residual_std, args.capacity, args.loss_pct, forecast_raw)

    result["date"] = result["timestamp"].dt.date
    daily = result.groupby("date").agg(
        net_energy_mwh=("net_power_mw", "sum"),   # hourly MW summed over 24h = MWh
        avg_wind_speed=("wind_speed", "mean"),
    ).round(3)

    print(f"Daily expected NET output — next {args.forecast_days} days "
          f"({args.capacity} MW system, {args.loss_pct}% loss):")
    print(daily.to_string())

    total_net_mwh = round(result["net_power_mw"].sum(), 2)
    total_gross_mwh = round(result["gross_power_mw"].sum(), 2)
    avg_utilization = round(result["gross_power_mw"].mean() / args.capacity, 3)

    print(f"\nTOTAL expected wind output — next {args.forecast_days} days:")
    print(f"  Gross energy : {total_gross_mwh} MWh")
    print(f"  Net energy   : {total_net_mwh} MWh")
    print(f"  Avg capacity utilization: {avg_utilization}")


if __name__ == "__main__":
    main()