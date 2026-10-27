/**
 * FarmerConnect - Price History & Trend Visualization Module
 */

window.FarmerHistory = (() => {
  async function init() {
    await loadCropAndMarketFilters();

    const cropSelect = document.getElementById('historyCropSelect');
    const marketSelect = document.getElementById('historyMarketSelect');
    const limitSelect = document.getElementById('historyLimitSelect');
    const btnLoad = document.getElementById('btnLoadHistory');

    // Default load
    if (cropSelect && cropSelect.value) {
      loadHistory(cropSelect.value, marketSelect?.value || 'all', limitSelect?.value || 30);
    }

    if (btnLoad && cropSelect) {
      btnLoad.addEventListener('click', () => {
        loadHistory(cropSelect.value, marketSelect?.value || 'all', limitSelect?.value || 30);
      });
    }

    if (cropSelect) {
      cropSelect.addEventListener('change', () => {
        loadHistory(cropSelect.value, marketSelect?.value || 'all', limitSelect?.value || 30);
      });
    }
  }

  async function loadCropAndMarketFilters() {
    try {
      const resp = await fetch('/api/markets/filters');
      const res = await resp.json();

      if (res.status === 'success') {
        const cropSelect = document.getElementById('historyCropSelect');
        const marketSelect = document.getElementById('historyMarketSelect');

        if (cropSelect && res.crops) {
          cropSelect.innerHTML = res.crops
            .map((c) => `<option value="${FarmerApp.escapeHtml(c)}">${FarmerApp.escapeHtml(c)}</option>`)
            .join('');
        }

        if (marketSelect && res.markets) {
          marketSelect.innerHTML =
            `<option value="all">All Mandis (Consolidated)</option>` +
            res.markets.map((m) => `<option value="${FarmerApp.escapeHtml(m)}">${FarmerApp.escapeHtml(m)}</option>`).join('');
        }
      }
    } catch (err) {
      console.error('Failed to load history filters:', err);
    }
  }

  async function loadHistory(crop, market = 'all', limit = 30) {
    if (!crop) return;

    let url = `/api/markets/history?crop=${encodeURIComponent(crop)}&limit=${limit}`;
    if (market && market !== 'all') url += `&market=${encodeURIComponent(market)}`;

    try {
      const resp = await fetch(url);
      const res = await resp.json();

      updateSummary(res.summary, crop);
      drawSvgChart(res.observations, crop);
      renderHistoryTable(res.observations);
    } catch (err) {
      console.error('Failed to load price history:', err);
      FarmerApp.showToast('Failed to load historical price trend', 'error');
    }
  }

  function updateSummary(summary, crop) {
    const cropHeader = document.getElementById('chartCropHeader');
    if (cropHeader) cropHeader.textContent = crop;

    const latestPrice = document.getElementById('histLatestPrice');
    const latestDate = document.getElementById('histLatestDate');
    const avgPrice = document.getElementById('histAvgPrice');
    const trendPct = document.getElementById('histTrendPct');
    const trendDiff = document.getElementById('histTrendDiff');
    const rangeEl = document.getElementById('histMinMaxRange');
    const pointsEl = document.getElementById('histDataPoints');

    if (!summary) {
      if (latestPrice) latestPrice.textContent = '₹--';
      if (avgPrice) avgPrice.textContent = '₹--';
      if (trendPct) trendPct.textContent = '--%';
      if (rangeEl) rangeEl.textContent = 'No records';
      return;
    }

    if (latestPrice) latestPrice.textContent = FarmerApp.formatCurrency(summary.latest_price);
    if (latestDate) latestDate.textContent = `As of: ${summary.end_date}`;
    if (avgPrice) avgPrice.textContent = FarmerApp.formatCurrency(summary.avg_recorded);

    if (trendPct) {
      const sign = summary.percentage_change >= 0 ? '+' : '';
      trendPct.textContent = `${sign}${summary.percentage_change}%`;
      trendPct.style.color = summary.percentage_change >= 0 ? 'var(--status-live)' : 'var(--status-error)';
    }

    if (trendDiff) {
      const sign = summary.price_change >= 0 ? '+' : '';
      trendDiff.textContent = `${sign}${FarmerApp.formatCurrency(summary.price_change)} shift`;
    }

    if (rangeEl) {
      rangeEl.textContent = `${FarmerApp.formatCurrency(summary.min_recorded)} to ${FarmerApp.formatCurrency(summary.max_recorded)}`;
    }

    if (pointsEl) {
      pointsEl.textContent = `${summary.total_points} verified observations`;
    }
  }

  function drawSvgChart(observations, crop) {
    const svg = document.getElementById('historySvgChart');
    const tooltip = document.getElementById('chartTooltip');
    const chartWrapper = document.getElementById('chartWrapper');
    if (!svg || !chartWrapper) return;

    if (!observations || observations.length === 0) {
      svg.innerHTML = `
        <text x="450" y="160" text-anchor="middle" fill="#7b8a7f" font-size="16" font-family="inherit">
          Insufficient historical records available for ${FarmerApp.escapeHtml(crop)}.
        </text>
      `;
      return;
    }

    const width = 900;
    const height = 320;
    const padding = { top: 30, right: 40, bottom: 50, left: 70 };

    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;

    const prices = observations.map((o) => o.modal_price);
    let minPrice = Math.min(...prices);
    let maxPrice = Math.max(...prices);

    // Add padding to range
    if (minPrice === maxPrice) {
      minPrice = minPrice * 0.9;
      maxPrice = maxPrice * 1.1;
    } else {
      const range = maxPrice - minPrice;
      minPrice = Math.max(0, Math.floor((minPrice - range * 0.1) / 50) * 50);
      maxPrice = Math.ceil((maxPrice + range * 0.1) / 50) * 50;
    }

    const n = observations.length;
    const getX = (index) => padding.left + (n === 1 ? plotWidth / 2 : (index / (n - 1)) * plotWidth);
    const getY = (val) => padding.top + plotHeight - ((val - minPrice) / (maxPrice - minPrice)) * plotHeight;

    let elements = '';

    // Draw horizontal grid lines & Y labels (5 steps)
    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      const yVal = minPrice + ((maxPrice - minPrice) / steps) * i;
      const yPos = getY(yVal);

      elements += `
        <line x1="${padding.left}" y1="${yPos}" x2="${width - padding.right}" y2="${yPos}"
              stroke="#e4e9e2" stroke-width="1" stroke-dasharray="4,4" />
        <text x="${padding.left - 10}" y="${yPos + 4}" text-anchor="end" fill="#7b8a7f" font-size="11" font-family="inherit">
          ₹${Math.round(yVal)}
        </text>
      `;
    }

    // Generate Path Data for the trend line
    let pathD = '';
    const points = [];
    observations.forEach((obs, idx) => {
      const x = getX(idx);
      const y = getY(obs.modal_price);
      points.push({ x, y, obs });
      if (idx === 0) {
        pathD += `M ${x} ${y}`;
      } else {
        pathD += ` L ${x} ${y}`;
      }
    });

    // Filled area under curve
    const areaD = `${pathD} L ${points[points.length - 1].x} ${padding.top + plotHeight} L ${points[0].x} ${padding.top + plotHeight} Z`;

    elements += `
      <defs>
        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#4caf50" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="#4caf50" stop-opacity="0.02"/>
        </linearGradient>
      </defs>
      <path d="${areaD}" fill="url(#areaGradient)" />
      <path d="${pathD}" fill="none" stroke="#25663d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
    `;

    // Draw X Axis dates & interactive circle nodes
    const labelInterval = Math.max(1, Math.ceil(n / 7));
    points.forEach((pt, idx) => {
      // Date label
      if (idx % labelInterval === 0 || idx === n - 1) {
        const shortDate = pt.obs.recorded_date.substring(5); // MM-DD
        elements += `
          <text x="${pt.x}" y="${height - 20}" text-anchor="middle" fill="#7b8a7f" font-size="11" font-family="inherit">
            ${shortDate}
          </text>
        `;
      }

      // Interactive circle
      elements += `
        <circle cx="${pt.x}" cy="${pt.y}" r="4.5" fill="#ffffff" stroke="#1a4d2e" stroke-width="2.5"
                class="chart-dot" data-date="${pt.obs.recorded_date}" data-price="${pt.obs.modal_price}"
                data-market="${FarmerApp.escapeHtml(pt.obs.market_name)}" style="cursor: pointer;" />
      `;
    });

    svg.innerHTML = elements;

    // Attach hover listeners for interactive tooltip
    svg.querySelectorAll('.chart-dot').forEach((dot) => {
      dot.addEventListener('mouseenter', (e) => {
        dot.setAttribute('r', '7');
        dot.setAttribute('fill', '#4caf50');

        const date = dot.dataset.date;
        const price = dot.dataset.price;
        const market = dot.dataset.market;

        const rect = dot.getBoundingClientRect();
        const wrapperRect = chartWrapper.getBoundingClientRect();

        tooltip.innerHTML = `
          <strong>${FarmerApp.formatCurrency(price)}</strong> / Quintal<br>
          <span style="font-size: 0.75rem; color: #81c784;">${date}</span><br>
          <span style="font-size: 0.7rem; color: #e8f5e9;">${market}</span>
        `;
        tooltip.style.left = `${rect.left - wrapperRect.left + rect.width / 2}px`;
        tooltip.style.top = `${rect.top - wrapperRect.top}px`;
        tooltip.style.opacity = '1';
      });

      dot.addEventListener('mouseleave', () => {
        dot.setAttribute('r', '4.5');
        dot.setAttribute('fill', '#ffffff');
        tooltip.style.opacity = '0';
      });
    });
  }

  function renderHistoryTable(observations) {
    const tbody = document.getElementById('historyTableBody');
    if (!tbody) return;

    if (!observations || observations.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);">
            No historical observations available.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = observations
      .slice()
      .reverse()
      .map((obs) => {
        const isLive = obs.source_type === 'LIVE';
        return `
        <tr>
          <td><strong>${obs.recorded_date}</strong></td>
          <td>${FarmerApp.escapeHtml(obs.crop_name)}</td>
          <td>${FarmerApp.escapeHtml(obs.market_name)}</td>
          <td>${FarmerApp.formatCurrency(obs.min_price)}</td>
          <td>${FarmerApp.formatCurrency(obs.max_price)}</td>
          <td><span class="price-pill">${FarmerApp.formatCurrency(obs.modal_price)}</span></td>
          <td>${obs.price_unit || '₹/Quintal'}</td>
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

  document.addEventListener('DOMContentLoaded', init);

  return {
    loadHistory,
  };
})();
