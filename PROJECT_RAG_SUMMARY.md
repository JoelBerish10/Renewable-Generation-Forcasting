# RenewCast: Renewable Energy Generation Forecasting — RAG Knowledge Base & System Overview

> **Target System:** RenewCast AI Forecasting Platform  
> **Repository:** `JoelBerish10/Renewable-Generation-Forcasting`  
> **Domain:** Renewable Energy, Power Grid Intelligence, Time-Series Forecasting  
> **Target Coordinates:** Panvel, Raigad, Maharashtra, India (18.99° N, 73.12° E)  
> **Key Technologies:** Python, XGBoost, Scikit-Learn, Pandas, NumPy, Open-Meteo APIs, HTML5, CSS3, Vanilla JavaScript, Built-in HTTP Server

---

## 1. Executive Summary & Problem Context

The integration of variable renewable energy sources (Solar Photovoltaic and Wind Energy) into the electrical power grid poses significant challenges due to atmospheric intermittency, cloud dynamics, and fluctuating wind patterns. Grid operators face dispatch imbalance, curtailment costs, and reliability risks without accurate day-ahead and intra-day generation forecasting.

**RenewCast** is an end-to-end forecasting and visualization platform engineered to deliver hyperlocal, high-confidence power generation predictions for solar farms and wind installations. It combines:
1. Automated ingestion of meteorological archives (ERA5 reanalysis) and multi-day live weather forecasts.
2. Physical engineering models (IEC turbine power curves, wind shear law, and photovoltaic thermal degradation).
3. Supervised gradient boosted regression trees (`XGBoost`).
4. A lightweight, dependency-free Python API runtime.
5. An interactive, responsive, glassmorphic dashboard interface for grid dispatchers and facility managers.

---

## 2. System Architecture & Data Flow

```mermaid
graph TD
    subgraph Data Layer
        A1[Open-Meteo Archive API<br/>1-Year Historical Weather] --> B1[Feature Engineering]
        A2[Open-Meteo Forecast API<br/>7-Day Live Weather] --> B2[Feature Pipeline]
        A3[Historical SCADA/CSV Data<br/>wind dataset.csv] --> B1
    end

    subgraph Physics & Modeling Layer
        B1 --> C1[Solar Thermal Loss Engine]
        B1 --> C2[Wind Shear & IEC Power Curve]
        C1 --> D1[XGBoost Solar Regressor]
        C2 --> D2[XGBoost Wind Regressor]
        D1 --> E1[Saved Models & Forecast CSVs]
        D2 --> E2[Saved Models & Forecast CSVs]
    end

    subgraph Serving Layer
        E1 --> F[backend/app.py<br/>ThreadingHTTPServer :8000]
        E2 --> F
        F --> G1[/api/health]
        F --> G2[/api/forecast/solar]
        F --> G3[/api/forecast/wind]
    end

    subgraph Presentation Layer
        F --> H[Front-end UI]
        H --> I1[index.html - Landing & Grid KPIs]
        H --> I2[solar.html - Solar Farm Dashboard]
        H --> I3[wind.html - Wind Farm Dashboard]
        H --> I4[api.js & dashboard.js - Dynamic SVG Rendering]
    end
```

---

## 3. Component Deep Dive

### 3.1. Solar Forecasting Pipeline (`backend/Solar data.py`)
- **Site Parameters:** Latitude 18.9894° N, Longitude 73.1175° E (Panvel, Maharashtra).
- **Array Configuration:** 5 kWp rated photovoltaic capacity.
- **Data Acquisition:**
  - `https://archive-api.open-meteo.com/v1/archive` (Historical: 2024 full year, 8,760 hourly records).
  - Variables: Global Horizontal Irradiance (`ghi` / shortwave radiation in W/m²), 2m temperature (°C), relative humidity (%).
  - `https://api.open-meteo.com/v1/forecast` (7-day ahead live forecast).
- **Physics Model (Thermal Loss Adjustment):**
  $$\text{power\_kw} = \max\left(0, \text{GHI} \times 0.005 \times (1 - 0.004 \times (\text{temperature} - 25))\right)$$
  Accounts for panel nominal operating temperature coefficient ($-0.4\%/\text{°C}$ above 25°C).
- **Feature Set:**
  - Meteorological: `ghi`, `temperature`, `humidity`
  - Cyclical Temporal: $\sin(2\pi \cdot \text{hour}/24)$, $\cos(2\pi \cdot \text{hour}/24)$, $\sin(2\pi \cdot \text{month}/12)$, $\cos(2\pi \cdot \text{month}/12)$
- **Algorithm:** `XGBRegressor(n_estimators=200, learning_rate=0.04, max_depth=6, subsample=0.8, random_state=42)`
- **Generated Outputs:**
  - `solar_xgboost_model.pkl` (Serialized model weights)
  - `solar_full_year_8760_hourly.csv` (Hourly historical ground truth & baseline predictions)
  - `solar_full_year_daily_summary.csv` (Daily aggregated kWh, peak kW, max GHI)
  - `solar_7day_hourly_forecast.csv` (Live hourly forecast for the upcoming 7 days)
  - `solar_7day_daily_summary.csv` (Daily summary for the upcoming week)

---

### 3.2. Wind Forecasting Pipeline (`backend/wind forcast model.py`)
- **Site Parameters:** Latitude 18.99° N, Longitude 73.12° E.
- **Wind Farm Configuration:** 10.0 MW rated capacity, 80m hub height, 6.5% system loss factor.
- **Turbine Physics Engine:**
  - **Wind Shear Law:** Extrapolates 10m surface winds to 80m hub height using the standard power-law exponent ($\alpha = 1/7$):
    $$v_{\text{hub}} = v_{10} \times \left(\frac{h_{\text{hub}}}{10}\right)^{1/7}$$
  - **IEC Standard Power Curve:**
    - Cut-in wind speed: $3.5\text{ m/s}$
    - Rated wind speed: $13.0\text{ m/s}$
    - Cut-out wind speed: $25.0\text{ m/s}$
    - Cubic ramp progression: $P_{\text{norm}} = \left(\frac{v_{\text{hub}} - v_{\text{cut\_in}}}{v_{\text{rated}} - v_{\text{cut\_in}}}\right)^3$
- **Feature Set:**
  - Direct atmospheric: `wind_speed`, `temperature`, `humidity`, `pressure`
  - Directional components: $\sin(2\pi \cdot \text{direction}/360)$, $\cos(2\pi \cdot \text{direction}/360)$
  - Diurnal and annual harmonics: `hour_sin`, `hour_cos`, `month_sin`, `month_cos`
  - Autoregressive dynamic features: `lag_1h`, `lag_2h`, `lag_24h`
  - Window aggregations: `rolling_mean_6h`
- **Algorithm:** `XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8)`
- **Evaluation & Uncertainty Estimation:**
  - Chronological 80/20 train-test split (avoids future-lookahead leakage).
  - Metrics tracked: MAE, RMSE, and $R^2$.
  - Prediction confidence intervals ($\pm 1\sigma$) calculated via model residual standard deviation (`residual_std`).
- **Loss Engine:** Computes gross output (MW) minus transmission/aerodynamic losses ($6.5\%$) to output net power (MW).
- **Generated Outputs:**
  - `backend/ml/saved_models/wind_model.joblib`
  - `backend/wind dataset.csv` (2,881 records of meteorological and generation parameters)

---

### 3.3. Backend Server & API Gateway (`backend/app.py`)
Built using Python's standard library (`http.server.ThreadingHTTPServer` and `SimpleHTTPRequestHandler`), requiring **zero** external web framework dependencies (no Flask/FastAPI installation required for runtime execution).

- **Port:** `8000` (Binding: `127.0.0.1:8000`)
- **Static Hosting:** Serves all assets located in the `Front-end/` directory.
- **REST API Endpoints:**

| Endpoint | Method | Response Description |
| :--- | :--- | :--- |
| `/api/health` | `GET` | Returns `{"status": "ok"}` for service heartbeat and liveness checks. |
| `/api/forecast/solar` | `GET` | Returns rolling 24-hour solar forecast: hourly kW, irradiance, temperature, humidity, calculated cloud cover, UV index, capacity (5 kW), 96.1% model accuracy, and text insights. |
| `/api/forecast/wind` | `GET` | Returns rolling 24-hour wind forecast: hourly kW, wind velocity, compass direction (e.g. `210° SSW`), barometric pressure, capacity (10,000 kW), 94.2% model accuracy, and text insights. |

---

### 3.4. Frontend Client Architecture (`Front-end/`)
A responsive, high-aesthetic dark-mode UI styled with modern CSS typography (DM Mono, Manrope) and custom SVG charts.

- **`index.html`**: Entry landing page introducing RenewCast, orbital animated visualizer, real-time KPI chips, and quick-links to wind/solar dashboards.
- **`solar.html`**: Solar farm telemetry screen with 24-hour generation curve, peak solar wattage indicator, irradiance meters, and environmental sensors.
- **`wind.html`**: Wind farm telemetry screen with real-time generation graph, wind speed, turbine status, and compass bearings.
- **`api.js`**:
  - Connects to `/api/forecast/solar` and `/api/forecast/wind`.
  - Dynamically computes SVG cubic/linear path strings (`M... L...`) and area polygons based on hourly forecast values.
  - Automatically calculates and positions peak generation rings and labels.
  - Updates stat cards (kW, W/m², m/s, accuracy %, temperature, pressure).
- **`dashboard.js`**: Manages farm location selection (Farm A, Farm B, Array C), 24h vs. 48h horizon switches, collapsible navigation drawer, and scroll-spy observer.
- **`site.js`**: Handles page transitions, keyboard accessibility, ARIA tags, and mobile navigation burger menu.
- **Additional Pages**: `about.html`, `contact.html`, `learn.html`, `login.html`.

---

## 4. Repository File Map

```
Renewable-Generation-Forcasting/
├── README.md                              # Quickstart documentation
├── start.py                               # Sample CLI runner command
├── PROJECT_RAG_SUMMARY.md                 # Complete system overview & RAG document (this file)
├── backend/
│   ├── app.py                             # Main ThreadingHTTPServer & REST API router
│   ├── Solar data.py                      # Solar data acquisition, feature engineering & XGBoost trainer
│   ├── wind forcast model.py              # Wind data acquisition, turbine physics, XGBoost trainer
│   ├── ok.py                              # Environment verification test script
│   ├── solar_xgboost_model.pkl            # Serialized XGBoost solar model
│   ├── solar_full_year_8760_hourly.csv    # 8,760 hourly historical solar dataset
│   ├── solar_full_year_daily_summary.csv  # 365 daily aggregated historical solar records
│   ├── solar_7day_hourly_forecast.csv     # 168 hourly solar forecast data points
│   ├── solar_7day_daily_summary.csv       # 7-day daily solar forecast summaries
│   ├── wind dataset.csv                   # Historical wind dataset (wind speed, dir, temp, humidity, pressure, power)
│   └── ml/
│       └── saved_models/
│           └── wind_model.joblib          # Serialized XGBoost wind model bundle
└── Front-end/
    ├── index.html                         # Platform landing page
    ├── solar.html                         # Solar forecasting dashboard
    ├── wind.html                          # Wind forecasting dashboard
    ├── about.html                         # Team and vision page
    ├── contact.html                       # Inquiry form page
    ├── learn.html                         # Educational overview of forecasting physics
    ├── login.html                         # User portal authentication UI
    ├── api.js                             # API consumption & SVG chart generator
    ├── dashboard.js                       # Dashboard controls, state & scroll tracking
    ├── site.js                            # Navigation, drawer toggle & transitions
    ├── styles.css                         # Primary landing page stylesheet
    ├── solar.css                          # Solar dashboard stylesheet
    ├── wind.css                           # Wind dashboard stylesheet
    ├── about.css / contact.css / learn.css / login.css
```

---

## 5. Execution & Operational Commands

### 5.1. Running the Platform
From the repository root:
```powershell
python backend/app.py
```
Access the application at: `http://localhost:8000`

### 5.2. Retraining / Generating Solar Forecasts
```powershell
python "backend/Solar data.py"
```
*Fetches live Open-Meteo weather data, trains XGBoost, and updates the 7-day CSV forecasts.*

### 5.3. Retraining / Generating Wind Forecasts
```powershell
python "backend/wind forcast model.py" --capacity 10.0 --loss_pct 6.5
```
Or with custom operational SCADA data:
```powershell
python "backend/wind forcast model.py" --data your_generation_history.csv --capacity 10.0
```

---

## 6. Key Takeaways & RAG Query Answering Guide

- **What problem does RenewCast solve?** Mitigates grid uncertainty and power curtailment by providing hour-by-hour solar and wind power generation forecasts using machine learning and atmospheric physics.
- **What models are utilized?** Gradient Boosted Decision Trees (`xgboost.XGBRegressor`) trained on meteorological variables, cyclical temporal features, and autoregressive lag indicators.
- **Where does weather data come from?** Open-Meteo API (free, no API key required, utilizing ERA5 reanalysis for historical training and high-resolution numerical weather prediction models for live 7-day outlooks).
- **How are physical losses handled?**
  - **Solar:** Temperature derating coefficient ($-0.4\%/\text{°C}$ above 25°C).
  - **Wind:** Hub height power-law wind shear extrapolation ($\alpha = 1/7$) and standard IEC turbine power curves, with a configurable 6.5% overall system loss deduction.
- **What is the backend architecture?** A self-contained Python HTTP server (`backend/app.py`) with zero external web framework dependencies serving static files and JSON APIs.
