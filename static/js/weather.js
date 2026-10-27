/**
 * FarmerConnect - Weather Module Controller
 */

window.FarmerWeather = (() => {
  let activeLat = 11.0055;
  let activeLon = 76.9661;
  let activeLocName = 'Coimbatore';

  async function init() {
    // Check if state has location or read default
    if (FarmerApp && FarmerApp.state && FarmerApp.state.currentLocation) {
      activeLat = FarmerApp.state.currentLocation.latitude;
      activeLon = FarmerApp.state.currentLocation.longitude;
      activeLocName = FarmerApp.state.currentLocation.name;
    }

    loadWeather(activeLat, activeLon, activeLocName);

    // Bind refresh button
    const btnRefresh = document.getElementById('btnRefreshWeather');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        loadWeather(activeLat, activeLon, activeLocName, true);
        FarmerApp.showToast('Refreshing live weather data...');
      });
    }

    // Bind location search
    const searchInput = document.getElementById('weatherLocationInput');
    const btnSearch = document.getElementById('btnWeatherSearchLoc');
    const suggestionsBox = document.getElementById('weatherLocationSuggestions');

    if (btnSearch && searchInput) {
      btnSearch.addEventListener('click', () => {
        const query = searchInput.value.trim();
        if (query) searchAndLoad(query);
      });

      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const query = searchInput.value.trim();
          if (query) searchAndLoad(query);
        }
      });

      // Suggestion auto-complete
      let timeout;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(timeout);
        const q = e.target.value.trim();
        if (q.length < 2) {
          if (suggestionsBox) suggestionsBox.style.display = 'none';
          return;
        }

        timeout = setTimeout(async () => {
          try {
            const resp = await fetch(`/api/locations?q=${encodeURIComponent(q)}`);
            const res = await resp.json();
            if (res.status === 'success' && res.locations && res.locations.length > 0) {
              suggestionsBox.innerHTML = res.locations
                .map(
                  (loc) => `
                <div class="suggestion-item" style="padding: 0.65rem 1rem; border-bottom: 1px solid var(--border-light); cursor: pointer;"
                     data-lat="${loc.latitude}" data-lon="${loc.longitude}" data-name="${loc.name}">
                  <strong>${loc.name}</strong>, <span style="font-size: 0.8rem; color: var(--text-muted);">${loc.display_name || 'Tamil Nadu'}</span>
                </div>
              `
                )
                .join('');
              suggestionsBox.style.display = 'block';

              // Bind suggestion clicks
              suggestionsBox.querySelectorAll('.suggestion-item').forEach((item) => {
                item.addEventListener('click', () => {
                  const lat = parseFloat(item.dataset.lat);
                  const lon = parseFloat(item.dataset.lon);
                  const name = item.dataset.name;
                  searchInput.value = name;
                  suggestionsBox.style.display = 'none';
                  loadWeather(lat, lon, name);
                });
              });
            } else {
              if (suggestionsBox) suggestionsBox.style.display = 'none';
            }
          } catch (err) {
            console.error('Suggestion error:', err);
          }
        }, 250);
      });

      // Close suggestions on outside click
      document.addEventListener('click', (e) => {
        if (suggestionsBox && !suggestionsBox.contains(e.target) && e.target !== searchInput) {
          suggestionsBox.style.display = 'none';
        }
      });
    }
  }

  async function searchAndLoad(query) {
    try {
      const resp = await fetch(`/api/locations?q=${encodeURIComponent(query)}`);
      const res = await resp.json();
      if (res.status === 'success' && res.locations && res.locations.length > 0) {
        const topLoc = res.locations[0];
        loadWeather(topLoc.latitude, topLoc.longitude, topLoc.name);
      } else {
        FarmerApp.showToast(`Location '${query}' not found. Please try another Tamil Nadu city.`, 'error');
      }
    } catch (err) {
      FarmerApp.showToast('Failed to resolve location search', 'error');
    }
  }

  async function loadWeather(lat, lon, name = '', forceRefresh = false) {
    activeLat = lat;
    activeLon = lon;
    if (name) activeLocName = name;

    const url = `/api/weather?lat=${lat}&lon=${lon}&location=${encodeURIComponent(activeLocName)}${forceRefresh ? '&refresh=1' : ''}`;

    try {
      const resp = await fetch(url);
      const res = await resp.json();

      if (res.status === 'success' && res.data) {
        const d = res.data;
        const cur = d.current;

        // Populate Hero Card
        const tempEl = document.getElementById('weatherCurrentTemp');
        const condEl = document.getElementById('weatherCurrentCondition');
        const locDisplay = document.getElementById('weatherLocationDisplay');
        const iconEl = document.getElementById('weatherHeroIcon');
        const humEl = document.getElementById('weatherHumidity');
        const windEl = document.getElementById('weatherWind');
        const precipEl = document.getElementById('weatherPrecip');
        const feelsEl = document.getElementById('weatherFeelsLike');
        const timeEl = document.getElementById('weatherUpdatedTime');

        if (tempEl) tempEl.innerHTML = `${cur.temperature} <span class="unit">°C</span>`;
        if (condEl) condEl.textContent = cur.condition;
        if (locDisplay) locDisplay.textContent = `Station: ${d.location_name}, Tamil Nadu (Lat: ${d.latitude}, Lon: ${d.longitude})`;
        if (iconEl) iconEl.textContent = FarmerApp.weatherIcons[cur.icon] || '🌤️';
        if (humEl) humEl.textContent = `${cur.humidity}%`;
        if (windEl) windEl.textContent = `${cur.wind_speed} km/h`;
        if (precipEl) precipEl.textContent = `${cur.precipitation} mm`;
        if (feelsEl) feelsEl.textContent = `${cur.apparent_temperature} °C`;
        if (timeEl) timeEl.textContent = res.source === 'live' ? 'Live Observation' : 'Cached (10m TTL)';

        // Populate Advisories
        const advBox = document.getElementById('weatherAdvisoryDetails');
        if (advBox) advBox.textContent = cur.advisory;

        const sprayEl = document.getElementById('advisorySpraying');
        const irrigEl = document.getElementById('advisoryIrrigation');
        const protEl = document.getElementById('advisoryProtection');

        if (sprayEl) {
          if (cur.wind_speed > 18) {
            sprayEl.innerHTML = `<span style="color: var(--status-error); font-weight: 600;">Unfavorable.</span> High wind speed (${cur.wind_speed} km/h) causes spray drift. Wait for calmer morning/evening hours.`;
          } else if (cur.precipitation > 1.0) {
            sprayEl.innerHTML = `<span style="color: var(--status-error); font-weight: 600;">Not Recommended.</span> Precipitation will wash off chemical sprays. Postpone application.`;
          } else {
            sprayEl.innerHTML = `<span style="color: var(--status-live); font-weight: 600;">Favorable.</span> Low wind and zero rain. Excellent window for foliar nutrient and pest sprays.`;
          }
        }

        if (irrigEl) {
          if (cur.precipitation > 5.0) {
            irrigEl.innerHTML = `<span style="color: var(--status-live); font-weight: 600;">Suspend Irrigation.</span> Natural rainfall is sufficient. Conserve tube-well electricity and water.`;
          } else if (cur.temperature > 34) {
            irrigEl.innerHTML = `<span style="color: var(--accent-amber); font-weight: 600;">High Evaporation.</span> Irrigate vegetable and banana crops during evening hours to minimize evaporation.`;
          } else {
            irrigEl.innerHTML = `Maintain normal drip or flood irrigation schedule according to soil moisture profile.`;
          }
        }

        if (protEl) {
          if (cur.humidity > 80) {
            protEl.innerHTML = `<span style="color: var(--accent-amber); font-weight: 600;">High Fungal Risk.</span> Elevated humidity (${cur.humidity}%) favors fungal blast in paddy and fruit rot in tomato.`;
          } else {
            protEl.innerHTML = `Standard pest monitoring. Inspect undersides of leaves for sucking pests (thrips, aphids).`;
          }
        }

        // Render 5-Day Detailed Forecast Grid
        renderFullForecast(d.forecast);
      } else {
        FarmerApp.showToast(res.message || 'Error fetching weather data', 'error');
      }
    } catch (err) {
      console.error('Weather load error:', err);
      FarmerApp.showToast('Network error contacting weather service', 'error');
    }
  }

  function renderFullForecast(forecast) {
    const grid = document.getElementById('weatherFullForecastGrid');
    if (!grid || !forecast) return;

    grid.innerHTML = forecast
      .map((day) => {
        const dateObj = new Date(day.date);
        const dayStr = dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        const icon = FarmerApp.weatherIcons[day.icon] || '🌤️';

        return `
        <div class="forecast-card">
          <div class="forecast-date">${dayStr}</div>
          <div class="forecast-icon">${icon}</div>
          <div style="font-size: 0.825rem; font-weight: 600; color: var(--text-main); margin-bottom: 0.4rem;">
            ${day.condition}
          </div>
          <div>
            <span class="forecast-temp">${day.temp_max}°C</span>
            <span class="forecast-temp-min">${day.temp_min}°C</span>
          </div>
          <div class="forecast-rain">💧 Rain: ${day.precipitation_probability}% (${day.precipitation_sum}mm)</div>
          <div style="font-size: 0.75rem; color: var(--text-light); margin-top: 0.25rem;">UV Index: ${day.uv_index}</div>
          <div style="font-size: 0.725rem; color: var(--text-muted); margin-top: 0.5rem; border-top: 1px dashed var(--border-light); padding-top: 0.4rem; line-height: 1.3;">
            ${day.advisory}
          </div>
        </div>
      `;
      })
      .join('');
  }

  // Initialize on script load
  document.addEventListener('DOMContentLoaded', init);

  return {
    loadWeather,
  };
})();
