/**
 * FarmerConnect - Markets Module Controller
 */

window.FarmerMarkets = (() => {
  let currentPage = 1;
  const pageSize = 15;
  let totalPages = 1;

  async function init() {
    await loadFilterDropdowns();
    loadMarketPrices(1);

    // Bind controls
    const cropInput = document.getElementById('filterCrop');
    const districtSelect = document.getElementById('filterDistrict');
    const marketSelect = document.getElementById('filterMarket');
    const sortSelect = document.getElementById('filterSort');
    const sourceSelect = document.getElementById('filterSource');
    const btnRefresh = document.getElementById('btnRefreshMarkets');
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');

    let debounceTimer;
    if (cropInput) {
      cropInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          loadMarketPrices(1);
        }, 300);
      });
    }

    if (districtSelect) {
      districtSelect.addEventListener('change', async () => {
        await updateMarketDropdown(districtSelect.value);
        loadMarketPrices(1);
      });
    }

    if (marketSelect) {
      marketSelect.addEventListener('change', () => loadMarketPrices(1));
    }

    if (sortSelect) {
      sortSelect.addEventListener('change', () => loadMarketPrices(1));
    }

    if (sourceSelect) {
      sourceSelect.addEventListener('change', () => loadMarketPrices(1));
    }

    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        loadMarketPrices(currentPage);
        FarmerApp.showToast('Mandi prices refreshed.');
      });
    }

    if (btnPrev) {
      btnPrev.addEventListener('click', () => {
        if (currentPage > 1) loadMarketPrices(currentPage - 1);
      });
    }

    if (btnNext) {
      btnNext.addEventListener('click', () => {
        if (currentPage < totalPages) loadMarketPrices(currentPage + 1);
      });
    }
  }

  async function loadFilterDropdowns() {
    try {
      const resp = await fetch('/api/markets/filters');
      const res = await resp.json();

      if (res.status === 'success') {
        const distSelect = document.getElementById('filterDistrict');
        const mktSelect = document.getElementById('filterMarket');

        if (distSelect && res.districts) {
          distSelect.innerHTML =
            `<option value="all">All Tamil Nadu Districts</option>` +
            res.districts.map((d) => `<option value="${FarmerApp.escapeHtml(d)}">${FarmerApp.escapeHtml(d)}</option>`).join('');
        }

        if (mktSelect && res.markets) {
          mktSelect.innerHTML =
            `<option value="all">All Mandis</option>` +
            res.markets.map((m) => `<option value="${FarmerApp.escapeHtml(m)}">${FarmerApp.escapeHtml(m)}</option>`).join('');
        }
      }
    } catch (err) {
      console.error('Failed to load market filters:', err);
    }
  }

  async function updateMarketDropdown(district) {
    const mktSelect = document.getElementById('filterMarket');
    if (!mktSelect) return;

    try {
      const url = `/api/markets/filters${district && district !== 'all' ? `?district=${encodeURIComponent(district)}` : ''}`;
      const resp = await fetch(url);
      const res = await resp.json();

      if (res.status === 'success' && res.markets) {
        mktSelect.innerHTML =
          `<option value="all">All Mandis</option>` +
          res.markets.map((m) => `<option value="${FarmerApp.escapeHtml(m)}">${FarmerApp.escapeHtml(m)}</option>`).join('');
      }
    } catch (err) {
      console.error('Error updating market dropdown:', err);
    }
  }

  async function loadMarketPrices(page = 1) {
    currentPage = page;

    const crop = document.getElementById('filterCrop')?.value.trim() || '';
    const district = document.getElementById('filterDistrict')?.value || 'all';
    const market = document.getElementById('filterMarket')?.value || 'all';
    const sort = document.getElementById('filterSort')?.value || 'date_desc';
    const source = document.getElementById('filterSource')?.value || 'all';

    let url = `/api/markets?page=${page}&limit=${pageSize}&sort=${sort}`;
    if (crop) url += `&crop=${encodeURIComponent(crop)}`;
    if (district && district !== 'all') url += `&district=${encodeURIComponent(district)}`;
    if (market && market !== 'all') url += `&market=${encodeURIComponent(market)}`;
    if (source && source !== 'all') url += `&source_type=${encodeURIComponent(source)}`;

    const tbody = document.getElementById('marketTableBody');
    if (!tbody) return;

    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; padding: 2rem;">
          <div class="skeleton skeleton-text" style="width: 50%; margin: 0 auto 0.5rem;"></div>
          <div class="skeleton skeleton-text" style="width: 30%; margin: 0 auto;"></div>
        </td>
      </tr>
    `;

    try {
      const resp = await fetch(url);
      const res = await resp.json();

      if (res.status === 'success') {
        const records = res.records;
        const pagination = res.pagination;
        totalPages = pagination.total_pages;

        // Update Top Source Banner
        updateSourceBanner(res.provider, res.overall_source_type);

        // Update Pagination controls
        const pageInfo = document.getElementById('paginationInfo');
        const pageInd = document.getElementById('pageIndicator');
        const btnPrev = document.getElementById('btnPrevPage');
        const btnNext = document.getElementById('btnNextPage');

        if (pageInfo) {
          pageInfo.textContent = `Showing page ${pagination.page} of ${pagination.total_pages || 1} (${pagination.total_records} total records)`;
        }
        if (pageInd) pageInd.textContent = `Page ${pagination.page}`;
        if (btnPrev) btnPrev.disabled = !pagination.has_prev;
        if (btnNext) btnNext.disabled = !pagination.has_next;

        if (records.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="10" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🔍</div>
                <strong>No mandi market records found matching your filters.</strong>
                <p style="font-size: 0.85rem; margin-top: 0.25rem;">Try changing or resetting your crop search or district filters.</p>
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
              <td><strong>${FarmerApp.escapeHtml(r.crop_name)}</strong></td>
              <td><span style="font-size: 0.8rem; color: var(--text-muted);">${FarmerApp.escapeHtml(r.variety || 'Standard')}</span></td>
              <td>${FarmerApp.escapeHtml(r.market_name)}</td>
              <td>${FarmerApp.escapeHtml(r.district)}</td>
              <td>${FarmerApp.formatCurrency(r.min_price)}</td>
              <td>${FarmerApp.formatCurrency(r.max_price)}</td>
              <td><span class="price-pill">${FarmerApp.formatCurrency(r.modal_price)}</span></td>
              <td><span style="font-size: 0.825rem; color: var(--text-muted);">${r.arrival_date}</span></td>
              <td>
                <span class="status-badge ${isLive ? 'live' : 'demo'}" style="font-size: 0.7rem; padding: 0.2rem 0.5rem;" title="${FarmerApp.escapeHtml(r.source_name)}">
                  ${isLive ? '🟢 LIVE GOV' : '🔶 DEMO'}
                </span>
              </td>
              <td>
                <a href="/compare?crop=${encodeURIComponent(r.crop_name)}" class="btn btn-outline btn-sm" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;">
                  Compare
                </a>
              </td>
            </tr>
          `;
          })
          .join('');
      }
    } catch (err) {
      console.error('Error loading market prices:', err);
      tbody.innerHTML = `
        <tr>
          <td colspan="10" style="text-align: center; color: var(--status-error); padding: 2rem;">
            Failed to load market price data. Please verify your connection.
          </td>
        </tr>
      `;
    }
  }

  function updateSourceBanner(provider, overallSource) {
    const banner = document.getElementById('marketSourceBanner');
    const icon = document.getElementById('marketSourceIcon');
    const title = document.getElementById('marketSourceTitle');
    const subtitle = document.getElementById('marketSourceSubtitle');
    const badge = document.getElementById('marketSourceBadge');

    if (!banner) return;

    if (overallSource === 'LIVE' || provider.is_configured) {
      banner.style.borderLeftColor = 'var(--primary-600)';
      if (icon) icon.textContent = '🟢';
      if (title) title.textContent = 'Live Government Data (data.gov.in / Agmarknet)';
      if (subtitle) subtitle.textContent = 'Streaming official daily agricultural commodity prices reported by APMC mandis.';
      if (badge) {
        badge.className = 'status-badge live';
        badge.textContent = '🟢 LIVE GOVERNMENT DATA';
      }
    } else {
      banner.style.borderLeftColor = 'var(--accent-amber)';
      if (icon) icon.textContent = '🔶';
      if (title) title.textContent = 'Demonstration Dataset Mode';
      if (subtitle) {
        subtitle.textContent =
          'Displaying verified Tamil Nadu agricultural sample records. To enable live data.gov.in prices, set DATA_GOV_IN_API_KEY in .env.';
      }
      if (badge) {
        badge.className = 'status-badge demo';
        badge.textContent = '🔶 DEMONSTRATION DATA';
      }
    }
  }

  document.addEventListener('DOMContentLoaded', init);

  return {
    loadMarketPrices,
  };
})();
