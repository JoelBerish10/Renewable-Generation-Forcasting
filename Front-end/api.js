/* Loads model output from the local RenewCast API without changing the dashboard layout. */
(() => {
  const energy = document.body.classList.contains('solar-body') ? 'solar' : 'wind';
  const one = (selector) => document.querySelector(selector);
  const text = (selector, value) => { const element = one(selector); if (element) element.textContent = value; };
  const power = (value) => `${Math.round(value).toLocaleString()} kW`;
  const chartPath = (values) => {
    const max = Math.max(...values, 1);
    return values.map((value, index) => `${index ? 'L' : 'M'}${(index / Math.max(values.length - 1, 1) * 700).toFixed(1)} ${(228 - value / max * 190).toFixed(1)}`).join(' ');
  };
  const updateChart = (forecast, capacity) => {
    const values = forecast.map((row) => row.power_kw), path = chartPath(values), peak = values.indexOf(Math.max(...values));
    const peakX = peak / Math.max(values.length - 1, 1) * 700, peakY = 228 - values[peak] / Math.max(...values, 1) * 190;
    const line = one(energy === 'solar' ? '.solar-line' : '.chart-line'), area = one(energy === 'solar' ? '.solar-area' : '.chart-area');
    if (line) line.setAttribute('d', path); if (area) area.setAttribute('d', `${path} L700 228 L0 228Z`);
    [one(energy === 'solar' ? '.solar-point' : '.chart-point'), one(energy === 'solar' ? '.solar-ring' : '.chart-ring')].forEach((node) => { if (node) { node.setAttribute('cx', peakX); node.setAttribute('cy', peakY); } });
    [...document.querySelectorAll('.x-labels span')].forEach((label, index, labels) => { const row = forecast[Math.round(index * (forecast.length - 1) / Math.max(labels.length - 1, 1))]; if (row) label.textContent = row.time; });
    const axisMax = Math.ceil(Math.max(capacity, ...values) / 100) * 100;
    [...document.querySelectorAll('.axis-labels span')].forEach((label, index, labels) => label.textContent = Math.round(axisMax - axisMax * index / Math.max(labels.length - 1, 1)));
  };
  const updateCards = (data) => {
    const c = data.current, cards = document.querySelectorAll('.stat-grid .stat-card');
    const values = energy === 'solar'
      ? [`${c.irradiance} <small>W/m²</small>`, `${power(c.power_kw).replace(' kW', '')} <small>kW</small>`, `${data.accuracy}<small>%</small>`, `${c.cloud_cover}<small>%</small>`]
      : [`${c.wind_speed} <small>m/s</small>`, `${power(c.power_kw).replace(' kW', '')} <small>kW</small>`, `${data.accuracy}<small>%</small>`, `${c.temperature}<small>°C</small>`];
    values.forEach((value, index) => { if (cards[index]) cards[index].querySelector('strong').innerHTML = value; });
    const conditions = energy === 'solar'
      ? [`${c.irradiance} W/m²`, `${c.temperature}°C`, `${c.cloud_cover}%`, `${c.humidity}%`, `${c.wind_speed} m/s`, `${c.uv_index} ${c.uv_index > 6 ? 'high' : 'moderate'}`]
      : [`${c.wind_speed} m/s`, c.direction_label, `${c.humidity}%`, `${c.temperature}°C`, `${c.pressure} hPa`, '12 / 12'];
    const selector = energy === 'solar' ? '.solar-condition-list strong' : '.condition-list strong';
    conditions.forEach((value, index) => { const field = document.querySelectorAll(selector)[index]; if (field) field.textContent = value; });
  };
  fetch(`/api/forecast/${energy}`)
    .then((response) => response.ok ? response.json() : Promise.reject())
    .then((data) => {
      updateCards(data); updateChart(data.forecast, data.capacity_kw); text('.insight-panel h3', data.insight.headline);
      const insight = one('.insight-panel > p:not(.panel-kicker):not(.insight-label)'); if (insight) insight.textContent = data.insight.detail;
      text('.sidebar-bottom small', `Forecast loaded ${new Date(data.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`); text('.model-status small', 'FORECAST DATA CONNECTED');
    })
    .catch(() => text('.sidebar-bottom small', 'Backend unavailable — showing last view'));
})();
