# ⚡ RenewCast — Smart Renewable Energy Generation & Power Grid Forecasting Platform
> **Hackathon Project:** Internal SIES SIH / Smart India Hackathon | **Team:** RenewCast (Members: Krutika Chaskar, Pratyush Deshmukh, Rohit Hazra, Saksham Alme, Ritika Devendra, Berish Joel) | **Domain:** Renewable Energy • Power Grid Intelligence • Time-Series Forecasting • Physics-Informed ML • Full-Stack Development

---

## 📌 Project Summary ("What is RenewCast?")

**RenewCast** is an end-to-end, physics-informed machine learning and telemetry platform engineered to forecast hourly and multi-day power generation for Solar Photovoltaic (PV) arrays and Wind Turbine installations.

Modern clean energy grids struggle with **renewable intermittency**—the rapid, unpredictable swings in electricity production driven by shifting weather patterns. RenewCast resolves this challenge by bridging real-time numerical weather prediction (NWP) APIs, classical aerodynamic and thermodynamic principles, gradient-boosted decision tree regression (`XGBoost`), and an interactive dark-mode telemetry dashboard.

Designed for utility dispatchers and plant operators, RenewCast provides reliable day-ahead and intra-day generation projections to stabilize grid dispatch, prevent costly curtailment, and reduce reliance on fossil-fuel peaker plants.

---

## ⚡ Problem Context & Industry Motivation

### The Intermittency Challenge
Unlike conventional thermal or hydro plants whose fuel supplies can be throttled on demand, solar and wind generation depend entirely on environmental variables. When renewable penetration in the power grid surges, unchecked intermittency causes:
- **Grid Instability & Frequency Deviations:** Mismatches between instantaneous power generation and demand threaten grid frequency standards (e.g., 50 Hz ± 0.05 Hz), risking regional blackouts.
- **Power Curtailment Penalties:** Without predictive foresight, grid operators order renewable operators to artificially disconnect arrays ("curtailment") during peak overproduction to protect transmission lines.
- **Spinning Reserve Inefficiencies:** Utilities must keep expensive, polluting gas peaker turbines running on standby to cover sudden generation shortfalls when clouds block solar farms or winds die down.

### The RenewCast Solution
RenewCast replaces guesswork with a **physics-informed data science architecture**:
1. **Automated Meteorological Ingestion:** Pulls high-resolution ERA5 reanalysis history and 7-day live weather predictions for target coordinates (Panvel, Maharashtra, India: 18.99° N, 73.12° E).
2. **Domain-Specific Physics Encodings:** Injects physical laws—photovoltaic thermal degradation, power-law wind shear extrapolation, and IEC turbine power curves—directly into the feature pipeline.
3. **Supervised Gradient Boosting:** Deploys `XGBRegressor` ensembles trained on cyclical harmonics and autoregressive lag indicators.
4. **Zero-Dependency Micro-API:** Delivers sub-millisecond predictions via Python's native multi-threaded HTTP server without heavy external web frameworks.
5. **Real-Time Vector Telemetry:** Dynamically renders SVG power curves and critical grid KPIs in a glassmorphic dashboard.

---

## 🏗️ End-to-End System Architecture

```
+-----------------------------------------------------------------------------------+
|                                 1. DATA LAYER                                     |
|  - Open-Meteo ERA5 Historical Reanalysis (8,760 hourly records / 1 full year)     |
|  - Open-Meteo 7-Day Live Numerical Weather Prediction (NWP) Hourly Forecast       |
|  - Variables: Irradiance (GHI), Wind Speed, Direction, Temp, Humidity, Pressure   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                        2. PHYSICS & FEATURE ENGINEERING                           |
|  [Solar Physics Engine]                 |  [Wind Aerodynamics Engine]             |
|  - Thermal Derating (-0.4%/°C > 25°C)   |  - Power-Law Wind Shear (10m -> 80m)    |
|  - Solar Geometry & GHI Multiplier      |  - IEC Cubic-Ramp Turbine Power Curve   |
|  - Cyclical Time Harmonics (Sin/Cos)    |  - Directional Vectors + Lag & Rolling  |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                           3. MACHINE LEARNING ENGINE                              |
|  - Model Architecture: Gradient Boosted Trees (XGBRegressor)                     |
|  - Chronological 80/20 Train-Test Validation (Zero future-lookahead leakage)     |
|  - Uncertainty Quantification: Residual standard deviation (+/- 1 sigma)         |
|  - System Loss Derating: 6.5% electrical/aerodynamic loss factor                  |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             4. SERVING & API LAYER                                |
|  - backend/app.py: Native Python ThreadingHTTPServer (Port 8000)                  |
|  - Zero external framework overhead (No Flask/FastAPI required for serving)       |
|  - Endpoints: /api/health, /api/forecast/solar, /api/forecast/wind                |
|  - database/app.py: SQLite3 + Flask service for user account authentication       |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                           5. USER & TELEMETRY DASHBOARD                           |
|  - Dark-mode glassmorphic interface (HTML5 / Modern CSS / Vanilla JavaScript)    |
|  - Dynamic SVG Path Renderer: Generates cubic curves & area fills on-the-fly     |
|  - Real-time generation cards, peak power indicators, and environmental telemetry |
+-----------------------------------------------------------------------------------+
```

---

## 📊 Data Engineering & Meteorological Pipeline

### Meteorological Data Ingestion
- **Target Coordinates:** 18.9894° N, 73.1175° E (Panvel, Raigad, Maharashtra, India).
- **Historical Baseline:** 8,760 hourly records extracted from high-resolution ERA5 atmospheric reanalysis (2024 calendar year).
- **Operational Horizon:** 168 hours (7-day ahead rolling forecast).
- **Core Atmospheric Features:**
  - `ghi`: Global Horizontal Irradiance (Solar Shortwave Radiation in W/m²).
  - `wind_speed`: 10-meter surface wind velocity (m/s).
  - `wind_direction`: Compass heading (0°–360°).
  - `temperature`: Ambient 2-meter air temperature (°C).
  - `humidity`: Relative humidity (%).
  - `pressure`: Surface barometric pressure (hPa).

---

## 🔬 Physics-Informed Modeling & Domain Equations

### 1. Solar Power Physics & Feature Engineering
- **Rated Array Capacity:** 5.0 kWp photovoltaic installation.
- **Photovoltaic Thermal Derating Model:**
  Standard silicon solar panels lose operating efficiency as cell temperature rises above Standard Test Conditions (STC: 25°C, 1000 W/m²). The target generation formula incorporates this physical degradation coefficient (-0.4% per °C above 25°C):
  $$\text{Power}_{\text{Solar}} (\text{kW}) = \max\left(0, \text{GHI} \times 0.005 \times \left(1 - 0.004 \times (\text{Temperature} - 25)\right)\right)$$
- **Cyclical Temporal Embeddings:**
  Standard numerical representations of time (e.g., hours 0–23, months 1–12) create an artificial discontinuity between 23:00 and 00:00 or December and January. We project time onto cyclical harmonics using sine and cosine transformations:
  $$\text{hour\_sin} = \sin\left(\frac{2\pi \cdot \text{hour}}{24}\right), \quad \text{hour\_cos} = \cos\left(\frac{2\pi \cdot \text{hour}}{24}\right)$$
  $$\text{month\_sin} = \sin\left(\frac{2\pi \cdot \text{month}}{12}\right), \quad \text{month\_cos} = \cos\left(\frac{2\pi \cdot \text{month}}{12}\right)$$
- **Feature Vector:** `[ghi, temperature, humidity, hour_sin, hour_cos, month_sin, month_cos]`.

---

### 2. Wind Turbine Physics & Feature Engineering
- **Rated Asset Capacity:** 10.0 MW utility-scale wind installation.
- **Hub Height Wind Shear Law (Hellmann's Exponent):**
  Surface wind measurements from meteorological stations are typically recorded at 10 meters above ground level. Utility turbine nacelles operate at elevated altitudes (80 meters). Surface velocities are adjusted to hub height using the standard power-law exponent ($\alpha = 1/7 \approx 0.143$):
  $$v_{\text{hub}} = v_{10} \times \left(\frac{h_{\text{hub}}}{10}\right)^{1/7} = v_{10} \times \left(\frac{80}{10}\right)^{0.143}$$
- **IEC Standard Turbine Power Curve:**
  Wind turbines do not generate power linearly with wind speed; they follow a characteristic physical response curve defined by three critical velocity thresholds:
  - **Cut-in Speed ($v_{\text{cut\_in}} = 3.5\text{ m/s}$):** Minimum velocity required to overcome friction and turn the rotor. Below this threshold, generation is zero.
  - **Rated Speed ($v_{\text{rated}} = 13.0\text{ m/s}$):** Velocity at which the generator reaches its rated 10 MW output. Between cut-in and rated speed, power output ramps cubically:
    $$P_{\text{norm}} = \left(\frac{v_{\text{hub}} - v_{\text{cut\_in}}}{v_{\text{rated}} - v_{\text{cut\_in}}}\right)^3$$
  - **Cut-out Speed ($v_{\text{cut\_out}} = 25.0\text{ m/s}$):** Maximum safe operating velocity. Above 25 m/s, aerodynamic pitch brakes feather the blades to prevent structural failure, bringing generation to zero.
- **Autoregressive & Time-Series Dynamics:**
  Wind exhibits strong momentum and atmospheric persistence. We extract:
  - Autoregressive lag terms: $t - 1\text{h}$, $t - 2\text{h}$, $t - 24\text{h}$
  - Moving window statistics: 6-hour rolling mean of normalized generation
  - Vector wind direction: $\sin(2\pi \cdot \theta / 360)$ and $\cos(2\pi \cdot \theta / 360)$
- **Systemic Loss Engine:**
  Applies a 6.5% derating factor to gross generator output to account for wake aerodynamic interference, transformer step-up losses, and high-voltage transmission resistance.

---

## 🤖 Machine Learning Pipeline & Evaluation

### Algorithm Choice
Both solar and wind estimators are trained using **Extreme Gradient Boosting (`XGBRegressor`)**. Decision tree ensembles are exceptionally well-suited for tabular meteorological data:
- They capture non-linear aerodynamic and thermal relationships without requiring artificial normalization.
- Subsampling and tree depth constraints provide strong regularization against atmospheric sensor noise.

### Training Configurations
| Parameter | Solar XGBoost Regressor | Wind XGBoost Regressor |
| :--- | :--- | :--- |
| **Target Variable** | Generated Power (`kW`) | Normalized Output (`0.0 to 1.0`) |
| **Number of Estimators** | 200 trees | 300 trees |
| **Max Tree Depth** | 6 | 4 |
| **Learning Rate ($\eta$)** | 0.04 | 0.05 |
| **Subsample Ratio** | 0.8 | 0.8 |
| **Feature Fraction (`colsample_bytree`)** | 1.0 | 0.8 |
| **Evaluation Strategy** | 80/20 Chronological Split | 80/20 Chronological Split |

### Prevention of Temporal Data Leakage
In time-series forecasting, traditional k-fold cross-validation or random train-test splitting causes **data leakage** because future timestamps leak into the past. RenewCast enforces a strict **chronological train-test split** (first 80% for training, remaining 20% for testing), guaranteeing that the model only predicts forward in time.

### Evaluation Metrics
- **Mean Absolute Error (MAE):** Quantifies average magnitude of prediction deviations.
- **Root Mean Squared Error (RMSE):** Penalizes large forecast misses, crucial for avoiding grid blackouts.
- **Coefficient of Determination ($R^2$):** Assesses the proportion of variance explained by the model.
- **Uncertainty Quantification:** The standard deviation of the test set residuals ($\sigma_{\text{residuals}}$) is preserved in the model bundle to compute dynamic $\pm 1\sigma$ prediction confidence intervals.
- **Observed Accuracy:**
  - Solar generation model: **~96.1%** accuracy
  - Wind generation model: **~94.2%** accuracy

---

## 💻 Software Architecture & Implementation

### 1. Lightweight Backend Server (`backend/app.py`)
Rather than introducing heavy web framework dependencies (such as Django, FastAPI, or Flask) for serving predictions, the core runtime is implemented using Python's standard library:
- **Server:** `http.server.ThreadingHTTPServer` configured for asynchronous multi-threaded request dispatching.
- **Static File Serving:** Serves client assets directly from the `Front-end/` directory.
- **REST API Endpoints:**
  - `GET /api/health`: Healthcheck heartbeat endpoint (`{"status": "ok"}`).
  - `GET /api/forecast/solar`: Returns a rolling 24-hour solar forecast containing timestamps, predicted kW, irradiance, temperature, humidity, calculated cloud cover, UV index, and automated dispatch insights.
  - `GET /api/forecast/wind`: Returns a rolling 24-hour wind forecast containing timestamps, predicted kW, wind velocity, compass direction labels (e.g., `210° SSW`), barometric pressure, turbine status, and peak generation insights.

### 2. User Management & Authentication (`database/`)
- **Backend:** Flask microservice (`database/app.py`) with CORS and session management.
- **Storage:** SQLite3 relational database (`database/renewcast.db`).
- **Security:** Passwords are cryptographically salted and hashed using `werkzeug.security` (PBKDF2-SHA256).
- **Endpoints:** User registration (`/api/signup`), session authentication (`/api/login`), and profile retrieval (`/api/me`).

### 3. Frontend Client & Mathematical SVG Rendering (`Front-end/`)
- **Philosophy:** Zero external visualization dependencies (no Chart.js, D3.js, or heavyweight bundles).
- **Dynamic Vector Path Generation (`api.js`):**
  The client takes the raw 24-hour forecast array from the API and mathematically maps each time-point into normalized SVG coordinate space (700px width by 228px height):
  - Automatically calculates SVG cubic/linear command strings (`M... L...`).
  - Computes the bounding area polygon (`... L700 228 L0 228Z`) to render a smooth translucent gradient under the power curve.
  - Identifies peak generation coordinates ($x_{\text{peak}}, y_{\text{peak}}$) and dynamically anchors pulsating indicator rings and tooltips.
- **Interface Screens:**
  - `index.html`: Landing page featuring live grid status chips, orbital generation visualizers, and system metrics.
  - `solar.html`: Solar Farm telemetric dashboard (hourly solar curve, irradiance meters, thermal tracking).
  - `wind.html`: Wind Farm telemetric dashboard (hourly generation, anemometer readings, compass bearings, turbine active status).
  - `about.html`, `learn.html`, `contact.html`, `login.html`: Auxiliary documentation and authentication views.

---

## 📁 Repository Structure

```
Renewable-Generation-Forcasting/
│
├── README.md                              # Comprehensive project overview & documentation
├── PROJECT_RAG_SUMMARY.md                 # Technical RAG summary and system notes
├── start.py                               # CLI execution helper script
│
├── backend/
│   ├── app.py                             # Multi-threaded HTTP server & REST API router
│   ├── Solar data.py                      # Solar data acquisition, thermal derating & XGBoost training
│   ├── wind forcast model.py              # Wind data acquisition, turbine physics & XGBoost training
│   ├── ok.py                              # Environment verification script
│   ├── solar_xgboost_model.pkl            # Serialized XGBoost solar model artifact
│   ├── solar_full_year_8760_hourly.csv    # 8,760 hourly solar training records
│   ├── solar_full_year_daily_summary.csv  # 365 daily aggregated historical records
│   ├── solar_7day_hourly_forecast.csv     # 168-hour live solar forecast output
│   ├── solar_7day_daily_summary.csv       # 7-day daily aggregated solar forecast
│   ├── wind dataset.csv                   # Historical wind dataset (speed, dir, temp, pressure, power)
│   └── ml/
│       └── saved_models/
│           └── wind_model.joblib          # Serialized XGBoost wind model bundle
│
├── database/
│   ├── database.py                        # SQLite database initialization & table schema
│   ├── app.py                             # Flask authentication microservice (signup/login/me)
│   └── renewcast.db                       # SQLite database file
│
└── Front-end/
    ├── index.html                         # Platform landing page & overview
    ├── solar.html                         # Solar farm operational dashboard
    ├── wind.html                          # Wind farm operational dashboard
    ├── about.html                         # Platform background & project vision
    ├── learn.html                         # Educational guide to forecasting physics
    ├── contact.html                       # Feedback and inquiry form
    ├── login.html                         # User portal authentication view
    ├── api.js                             # API consumer & dynamic SVG path generator
    ├── dashboard.js                       # Horizon switching (24h/48h) & UI state management
    ├── site.js                            # Navigation drawers, transitions, and accessibility
    └── styles.css / *.css                 # Responsive glassmorphism stylesheets
```

---

## 🚀 How to Run the Project

### Prerequisites
- Python 3.9+
- Standard data science libraries:
```bash
pip install xgboost scikit-learn pandas numpy joblib requests
```
*(Optional for database/authentication service):*
```bash
pip install flask flask-cors werkzeug
```

### 1. Launch the Main Dashboard & Forecast API
Run the built-in HTTP server from the project root:
```bash
python backend/app.py
```
Open a browser and navigate to:
```
http://localhost:8000
```
- Solar dashboard: `http://localhost:8000/solar.html`
- Wind dashboard: `http://localhost:8000/wind.html`

### 2. Retrain or Update Solar Forecasts
To fetch fresh meteorological data from Open-Meteo, retrain the solar model, and export new 7-day forecast CSVs:
```bash
python "backend/Solar data.py"
```

### 3. Retrain or Run Wind Forecasting via CLI
To retrain the wind model with custom capacity and loss parameters:
```bash
python "backend/wind forcast model.py" --capacity 10.0 --loss_pct 6.5
```
Or to run inference with live user parameters:
```bash
python "backend/wind forcast model.py" --wind_speed 8.4 --wind_direction 210 --temperature 29 --humidity 63 --pressure 1012
```

### 4. (Optional) Run the User Authentication Service
```bash
python database/app.py
```
Runs the authentication API on `http://127.0.0.1:5000`.

---

## 💡 Key Engineering & Data Science Takeaways

This project demonstrates core competencies across the full machine learning and software engineering lifecycle:

1. **Physics-Informed Feature Engineering:** Rather than feeding raw weather data into a generic regressor, the model leverages domain physics (photovoltaic cell thermal derating, wind shear extrapolation, and IEC cubic power curves) to guide machine learning convergence.
2. **Temporal Integrity (Zero Data Leakage):** Time-series models strictly preserve temporal order via chronological splits and autoregressive lag structures ($t-1$, $t-2$, $t-24$), preventing lookahead bias.
3. **Cyclical Temporal Encoding:** Deployed trigonometric transformations ($\sin / \cos$) on diurnal and annual intervals to accurately reflect natural cycles.
4. **End-to-End System Ownership:** Spans data acquisition (APIs), feature modeling, ML model training, serialization (`joblib`), backend microservices, database design, and frontend vector visualization.
5. **Architectural Efficiency:** Built a complete, responsive operational dashboard with zero client-side charting libraries (custom SVG generator) and zero external runtime web frameworks for the main forecast server.
