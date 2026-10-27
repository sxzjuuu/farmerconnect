/**
 * FarmerConnect - Market Comparison Module Controller
 */

window.FarmerCompare = (() => {
  let currentComparison = null;

  async function init() {
    await loadCropSelector();

    // Check URL parameters for ?crop=...
    const urlParams = new URLSearchParams(window.location.search);
    const initialCrop = urlParams.get('crop');

    const cropSelect = document.getElementById('compareCropSelect');
    if (initialCrop && cropSelect) {
      cropSelect.value = initialCrop;
      executeCompare(initialCrop);
    } else if (cropSelect && cropSelect.options.length > 0) {
      executeCompare(cropSelect.value);
    }

    // Bind compare button
    const btnCompare = document.getElementById('btnExecuteCompare');
    if (btnCompare && cropSelect) {
      btnCompare.addEventListener('click', () => {
        if (cropSelect.value) executeCompare(cropSelect.value);
      });

      cropSelect.addEventListener('change', () => {
        if (cropSelect.value) executeCompare(cropSelect.value);
      });
    }

    // Bind Calculator inputs
    const calcQty = document.getElementById('calcQuantity');
    const calcDist = document.getElementById('calcDistance');
    const calcRate = document.getElementById('calcFreightRate');

    [calcQty, calcDist, calcRate].forEach((input) => {
      if (input) input.addEventListener('input', updateCalculator);
    });
  }

  async function loadCropSelector() {
    const select = document.getElementById('compareCropSelect');
    if (!select) return;

    try {
      const resp = await fetch('/api/markets/filters');
      const res = await resp.json();

      if (res.status === 'success' && res.crops) {
        select.innerHTML = res.crops
          .map((c) => `<option value="${FarmerApp.escapeHtml(c)}">${FarmerApp.escapeHtml(c)}</option>`)
          .join('');
      }
    } catch (err) {
      console.error('Failed to load crop selector:', err);
    }
  }

  async function executeCompare(cropName) {
    if (!cropName) return;

    try {
      const resp = await fetch(`/api/markets/compare?crop=${encodeURIComponent(cropName)}`);
      const res = await resp.json();

      currentComparison = res;
      renderComparison(res);
      updateCalculator();
    } catch (err) {
      console.error('Error executing market comparison:', err);
      FarmerApp.showToast('Failed to compare market prices', 'error');
    }
  }

  function renderComparison(data) {
    const cropTitle = document.getElementById('comparedCropTitle');
    if (cropTitle) cropTitle.textContent = data.crop;

    const highName = document.getElementById('highMandiName');
    const highPrice = document.getElementById('highMandiPrice');
    const highDist = document.getElementById('highMandiDistrict');

    const lowName = document.getElementById('lowMandiName');
    const lowPrice = document.getElementById('lowMandiPrice');
    const lowDist = document.getElementById('lowMandiDistrict');

    const spreadEl = document.getElementById('maxPriceSpread');
    const avgEl = document.getElementById('avgMandiPrice');

    if (data.highest_market) {
      if (highName) highName.textContent = data.highest_market.market_name;
      if (highPrice) highPrice.textContent = FarmerApp.formatCurrency(data.highest_market.modal_price);
      if (highDist) highDist.textContent = `District: ${data.highest_market.district}`;
    } else {
      if (highName) highName.textContent = 'None';
      if (highPrice) highPrice.textContent = '₹0';
      if (highDist) highDist.textContent = '';
    }

    if (data.lowest_market) {
      if (lowName) lowName.textContent = data.lowest_market.market_name;
      if (lowPrice) lowPrice.textContent = FarmerApp.formatCurrency(data.lowest_market.modal_price);
      if (lowDist) lowDist.textContent = `District: ${data.lowest_market.district}`;
    } else {
      if (lowName) lowName.textContent = 'None';
      if (lowPrice) lowPrice.textContent = '₹0';
      if (lowDist) lowDist.textContent = '';
    }

    if (spreadEl) spreadEl.textContent = FarmerApp.formatCurrency(data.max_price_spread);
    if (avgEl) avgEl.textContent = `Average: ${FarmerApp.formatCurrency(data.average_modal_price)} / Quintal`;

    // Render Table Rows
    const tbody = document.getElementById('compareTableBody');
    if (!tbody) return;

    if (!data.records || data.records.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">
            No comparative mandi records found for ${FarmerApp.escapeHtml(data.crop)}.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = data.records
      .map((r) => {
        const isLive = r.source_type === 'LIVE';
        const isHighest = data.highest_market && r.id === data.highest_market.id;
        const isLowest = data.lowest_market && r.id === data.lowest_market.id;

        return `
        <tr style="${isHighest ? 'background-color: #f0fdf4;' : isLowest ? 'background-color: #fefce8;' : ''}">
          <td>
            <strong>${FarmerApp.escapeHtml(r.market_name)}</strong>
            ${isHighest ? ' <span class="card-badge high" style="position: static; font-size: 0.65rem;">Highest</span>' : ''}
            ${isLowest ? ' <span class="card-badge low" style="position: static; font-size: 0.65rem;">Lowest</span>' : ''}
          </td>
          <td>${FarmerApp.escapeHtml(r.district)}</td>
          <td>${FarmerApp.formatCurrency(r.min_price)}</td>
          <td>${FarmerApp.formatCurrency(r.max_price)}</td>
          <td><span class="price-pill">${FarmerApp.formatCurrency(r.modal_price)}</span></td>
          <td>
            <span style="font-weight: 700; color: ${r.diff_from_lowest > 0 ? 'var(--status-live)' : 'var(--text-muted)'};">
              +${FarmerApp.formatCurrency(r.diff_from_lowest)}
            </span>
          </td>
          <td>
            <span style="color: ${r.diff_from_avg >= 0 ? 'var(--primary-700)' : 'var(--accent-amber)'}; font-weight: 600;">
              ${r.diff_from_avg >= 0 ? '+' : ''}${FarmerApp.formatCurrency(r.diff_from_avg)}
            </span>
          </td>
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

  function updateCalculator() {
    if (!currentComparison || !currentComparison.max_price_spread) return;

    const qty = parseFloat(document.getElementById('calcQuantity')?.value || 1);
    const dist = parseFloat(document.getElementById('calcDistance')?.value || 0);
    const rate = parseFloat(document.getElementById('calcFreightRate')?.value || 0);

    const priceSpread = currentComparison.max_price_spread || 0;
    const grossGain = priceSpread * qty;
    const transportCost = dist * rate;
    const netGain = grossGain - transportCost;

    const grossEl = document.getElementById('calcGrossGain');
    const netEl = document.getElementById('calcNetGain');
    const verdictEl = document.getElementById('calcVerdict');

    if (grossEl) grossEl.textContent = FarmerApp.formatCurrency(grossGain);
    if (netEl) {
      netEl.textContent = (netGain >= 0 ? '+' : '') + FarmerApp.formatCurrency(netGain);
      netEl.style.color = netGain >= 0 ? 'var(--status-live)' : 'var(--status-error)';
    }

    if (verdictEl) {
      if (netGain > 0) {
        verdictEl.innerHTML = `
          <span style="color: var(--status-live);">Economically Viable!</span>
          Transport cost (${FarmerApp.formatCurrency(transportCost)}) is covered. Net gain is <strong>${FarmerApp.formatCurrency(netGain)}</strong>.
        `;
      } else {
        verdictEl.innerHTML = `
          <span style="color: var(--status-error);">Transit Not Recommended!</span>
          Transport cost (${FarmerApp.formatCurrency(transportCost)}) exceeds gross gain (${FarmerApp.formatCurrency(grossGain)}). Selling at local mandi saves money.
        `;
      }
    }
  }

  document.addEventListener('DOMContentLoaded', init);

  return {
    executeCompare,
  };
})();
