/**
 * FarmerConnect - Core Application Logic & Global Utilities
 */

const FarmerApp = (() => {
  // Application State
  const state = {
    currentLocation: {
      name: 'Coimbatore',
      district: 'Coimbatore',
      state: 'Tamil Nadu',
      latitude: 11.0055,
      longitude: 76.9661,
    },
  };

  // Weather condition icons mapping
  const weatherIcons = {
    sun: '☀️',
    'cloud-sun': '🌤️',
    cloud: '☁️',
    'cloud-fog': '🌫️',
    'cloud-drizzle': '🌦️',
    'cloud-rain': '🌧️',
    'cloud-lightning': '⛈️',
  };

  /**
   * Display toast notification
   */
  function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'error' : ''}`;
    toast.innerHTML = `
      <span style="font-size: 1.1rem;">${type === 'error' ? '❌' : '✅'}</span>
      <span>${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  /**
   * Format numeric value as Indian Rupee
   */
  function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '₹0';
    return '₹' + Number(amount).toLocaleString('en-IN');
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    if (!text) return '';
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
  }

  /**
   * Initialize mobile hamburger menu
   */
  function initMobileNav() {
    const btn = document.getElementById('mobileMenuBtn');
    const sidebar = document.getElementById('appSidebar');
    if (!btn || !sidebar) return;

    btn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !btn.contains(e.target)
      ) {
        sidebar.classList.remove('open');
      }
    });
  }

  /**
   * Initialize location modal & picker
   */
  function initLocationModal() {
    const modal = document.getElementById('locationModal');
    const btnOpen = document.getElementById('btnOpenLocModal');
    const btnTop = document.getElementById('btnTopLocSwitcher');
    const btnClose = document.getElementById('btnCloseLocModal');
    const input = document.getElementById('locSearchInput');
    const listContainer = document.getElementById('locationListContainer');

    function openModal() {
      if (modal) modal.classList.add('open');
      if (input) input.focus();
    }

    function closeModal() {
      if (modal) modal.classList.remove('open');
    }

    if (btnOpen) btnOpen.addEventListener('click', openModal);
    if (btnTop) btnTop.addEventListener('click', openModal);
    if (btnClose) btnClose.addEventListener('click', closeModal);

    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
      });
    }

    // Bind existing location buttons
    if (listContainer) {
      listContainer.addEventListener('click', async (e) => {
        const btn = e.target.closest('.location-item-btn');
        if (!btn) return;

        const name = btn.dataset.name;
        const lat = parseFloat(btn.dataset.lat);
        const lon = parseFloat(btn.dataset.lon);
        const district = btn.dataset.district;

        await selectLocation(name, lat, lon, district);
        closeModal();
      });
    }

    // Dynamic search debounce in modal
    let searchTimeout;
    if (input) {
      input.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const q = e.target.value.trim();
        if (q.length < 2) return;

        searchTimeout = setTimeout(async () => {
          try {
            const resp = await fetch(`/api/locations?q=${encodeURIComponent(q)}`);
            const data = await resp.json();
            if (data.status === 'success' && data.locations.length > 0) {
              listContainer.innerHTML = data.locations
                .map(
                  (loc) => `
                <button type="button" class="location-item-btn"
                        data-name="${escapeHtml(loc.name)}"
                        data-lat="${loc.latitude}"
                        data-lon="${loc.longitude}"
                        data-district="${escapeHtml(loc.admin1 || loc.name)}">
                  <strong>${escapeHtml(loc.name)}</strong>
                  <span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(loc.display_name || loc.admin1 || 'Tamil Nadu')}</span>
                </button>
              `
                )
                .join('');
            }
          } catch (err) {
            console.error('Location search error:', err);
          }
        }, 300);
      });
    }
  }

  /**
   * Set active location via backend API
   */
  async function selectLocation(name, lat, lon, district) {
    try {
      const resp = await fetch('/api/locations/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          location_name: name,
          latitude: lat,
          longitude: lon,
          district: district,
        }),
      });

      const res = await resp.json();
      if (res.status === 'success') {
        state.currentLocation = { name, latitude: lat, longitude: lon, district };

        // Update UI Labels
        const sideName = document.getElementById('sidebarLocName');
        const topLabel = document.getElementById('topLocLabel');
        const dashText = document.getElementById('dashCurrentLocText');
        if (sideName) sideName.textContent = name;
        if (topLabel) topLabel.textContent = name;
        if (dashText) dashText.textContent = name;

        showToast(`Location changed to ${name}`);

        // Trigger reload on active pages if needed
        if (window.location.pathname === '/') {
          initDashboard();
        } else if (window.location.pathname === '/weather' && window.FarmerWeather) {
          window.FarmerWeather.loadWeather(lat, lon, name);
        }
      }
    } catch (err) {
      showToast('Failed to update location', 'error');
    }
  }

  /**
   * Initialize Dashboard page
   */
  async function initDashboard() {
    loadDashboardWeather();
    loadDashboardMarkets();

    const btnRefresh = document.getElementById('btnRefreshDashboard');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        btnRefresh.classList.add('loading');
        loadDashboardWeather(true);
        loadDashboardMarkets();
        setTimeout(() => btnRefresh.classList.remove('loading'), 1000);
      });
    }

    const cropSearch = document.getElementById('dashCropSearch');
    let debounceTimer;
    if (cropSearch) {
      cropSearch.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          loadDashboardMarkets(e.target.value.trim(), getSelectedDistrict());
        }, 300);
      });
    }

    const distFilter = document.getElementById('dashDistrictFilter');
    if (distFilter) {
      distFilter.addEventListener('change', (e) => {
        const cropVal = cropSearch ? cropSearch.value.trim() : '';
        loadDashboardMarkets(cropVal, e.target.value);
      });
    }
  }

  function getSelectedDistrict() {
    const sel = document.getElementById('dashDistrictFilter');
    return sel ? sel.value : 'all';
  }

  /**
   * Load Weather on Dashboard
   */
  async function loadDashboardWeather(forceRefresh = false) {
    const loc = state.currentLocation;
    const url = `/api/weather?lat=${loc.latitude}&lon=${loc.longitude}&location=${encodeURIComponent(loc.name)}${forceRefresh ? '&refresh=1' : ''}`;

    try {
      const resp = await fetch(url);
      const res = await resp.json();

      if (res.status === 'success' && res.data) {
        const d = res.data;
        const cur = d.current;

        const tempEl = document.getElementById('dashWeatherTemp');
        const condEl = document.getElementById('dashWeatherCondition');
        const locTitle = document.getElementById('dashWeatherLocTitle');
        const iconEl = document.getElementById('dashWeatherIcon');
        const timeEl = document.getElementById('dashWeatherTimestamp');

        if (tempEl) tempEl.innerHTML = `${cur.temperature} <span class="unit">°C</span>`;
        if (condEl) condEl.textContent = cur.condition;
        if (locTitle) locTitle.textContent = `Station: ${d.location_name}, Tamil Nadu`;
        if (iconEl) iconEl.textContent = weatherIcons[cur.icon] || '🌤️';
        if (timeEl) timeEl.textContent = res.source === 'live' ? 'Live Now' : 'Cached';

        const humEl = document.getElementById('dashHumidity');
        const windEl = document.getElementById('dashWind');
        const precipEl = document.getElementById('dashPrecip');
        const feelsEl = document.getElementById('dashFeelsLike');

        if (humEl) humEl.textContent = `${cur.humidity}%`;
        if (windEl) windEl.textContent = `${cur.wind_speed} km/h`;
        if (precipEl) precipEl.textContent = `${cur.precipitation} mm`;
        if (feelsEl) feelsEl.textContent = `${cur.apparent_temperature} °C`;

        // Update Advisory
        const advText = document.getElementById('dashAdvisoryText');
        if (advText) advText.textContent = cur.advisory;

        // Render mini 5-day forecast
        renderMiniForecast(d.forecast);
      }
    } catch (err) {
      console.error('Failed to load dashboard weather:', err);
    }
  }

  /**
   * Render 5-day mini forecast on dashboard
   */
  function renderMiniForecast(forecast) {
    const container = document.getElementById('dashForecastGrid');
    if (!container || !forecast) return;

    container.innerHTML = forecast
      .map((day) => {
        const dateObj = new Date(day.date);
        const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        const icon = weatherIcons[day.icon] || '🌤️';

        return `
        <div class="forecast-card">
          <div class="forecast-date">${dayName}</div>
          <div class="forecast-icon">${icon}</div>
          <div>
            <span class="forecast-temp">${day.temp_max}°</span>
            <span class="forecast-temp-min">${day.temp_min}°</span>
          </div>
          <div class="forecast-rain">💧 ${day.precipitation_probability}% rain</div>
        </div>
      `;
      })
      .join('');
  }

  /**
   * Load Featured Mandi Prices on Dashboard
   */
  async function loadDashboardMarkets(crop = '', district = 'all') {
    let url = `/api/markets?limit=8`;
    if (crop) url += `&crop=${encodeURIComponent(crop)}`;
    if (district && district !== 'all') url += `&district=${encodeURIComponent(district)}`;

    const tbody = document.getElementById('dashMarketTableBody');
    if (!tbody) return;

    try {
      const resp = await fetch(url);
      const res = await resp.json();

      if (res.status === 'success') {
        const records = res.records;
        if (records.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                No matching mandi records found. Try adjusting crop or district filters.
              </td>
            </tr>
          `;
          return;
        }

        tbody.innerHTML = records
          .map((r) => {
            const isLive = r.source_type === 'LIVE';
            return `
            <tr>
              <td><strong>${escapeHtml(r.crop_name)}</strong></td>
              <td><span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(r.variety || 'Standard')}</span></td>
              <td>${escapeHtml(r.market_name)}</td>
              <td>${escapeHtml(r.district)}</td>
              <td>${formatCurrency(r.min_price)}</td>
              <td>${formatCurrency(r.max_price)}</td>
              <td><span class="price-pill">${formatCurrency(r.modal_price)}</span></td>
              <td><span style="font-size: 0.8rem; color: var(--text-muted);">${r.arrival_date}</span></td>
              <td>
                <span class="status-badge ${isLive ? 'live' : 'demo'}" style="font-size: 0.7rem; padding: 0.2rem 0.5rem;">
                  ${isLive ? '🟢 LIVE' : '🔶 DEMO'}
                </span>
              </td>
            </tr>
          `;
          })
          .join('');
      }
    } catch (err) {
      console.error('Failed to load dashboard markets:', err);
      tbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; color: var(--status-error); padding: 1.5rem;">
            Failed to load market prices.
          </td>
        </tr>
      `;
    }
  }

  // Self initialize on DOM load
  document.addEventListener('DOMContentLoaded', () => {
    initMobileNav();
    initLocationModal();
  });

  return {
    state,
    showToast,
    formatCurrency,
    formatDate: (d) => d,
    escapeHtml,
    weatherIcons,
    initDashboard,
    selectLocation,
  };
})();
