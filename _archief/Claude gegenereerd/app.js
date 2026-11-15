// ============================================================
// POLITIEK TRANSPARANT NL — APP.JS
// Volledige interactiviteit, grafieken en data-rendering
// ============================================================

'use strict';

// --- GLOBALS ---
let currentPage = 'home';
let activePartij = null;
let zetelsChart = null;
let financienChart = null;
let aanwezigheidChart = null;
let overviewChart = null;
let currentFilter = 'alle';
let currentFilter2 = 'alle';

// Grote partijen voor overzichtsgrafiek
const HOOFD_PARTIJEN = ['VVD', 'PvdA', 'CDA', 'D66', 'GL', 'SP', 'PVV', 'NSC'];
const COALITIE_2024  = ['PVV', 'VVD', 'NSC', 'BBB'];

// Ideologie → linksspectrum mapping
const IDEOLOGIE_KLEUR = {
  'Liberaal-conservatief':     'rechts',
  'Sociaaldemocratie':         'links',
  'Christendemocratie':        'christen',
  'Progressief liberalisme':   'links',
  'Groen-links':               'links',
  'Socialisme':                'links',
  'Populistisch rechts':       'rechts',
  'Nationaalconservatief':     'rechts',
  'Christelijk-sociaal':       'christen',
  'Orthodox-gereformeerd':     'christen',
  'Dierenrechten / Groen':     'links',
  'Agrarisch-conservatief':    'rechts',
  'Paneuropees progressief':   'links',
  'Nationaal-conservatief':    'rechts',
  'Multicultureel progressief':'links',
  'Ouderenbelangen':           'rechts',
  'Anti-racistisch links':     'links',
  'Gereformeerd-confessioneel':'christen',
  'Reformatorisch':            'christen',
};

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  renderHeroStats();
  renderPartijGrid('partijGrid', 'alle');
  renderPartijGrid('partijGrid2', 'alle');
  renderKabinetTimeline('kabinetTimeline', 'kabinetDetail');
  renderKabinetTimeline('kabinetTimeline2', 'kabinetDetail2');
  renderKabinettenLijst();
  renderOverviewChart();
  populateVergelijkSelects();
  initBackToTop();
});

// ============================================================
// NAVIGATIE
// ============================================================
function showPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const el = document.getElementById('page-' + page);
  if (el) el.classList.add('active');
  currentPage = page;

  // Update nav links
  document.querySelectorAll('.nav-links a').forEach(a => {
    a.classList.toggle('active', a.dataset.page === page);
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });
  closeSearch();

  // Lazy render on first visit
  if (page === 'vergelijk') updateVergelijk();
}

function toggleMenu() {
  const links  = document.getElementById('navLinks');
  const search = document.getElementById('navSearch');
  links.classList.toggle('open');
  search.classList.toggle('open');
}

// ============================================================
// HERO STATS
// ============================================================
function renderHeroStats() {
  const container = document.getElementById('heroStats');
  if (!container) return;

  const actievePartijen = POLITIEK_DATA.partijen.filter(p => p.actief).length;
  const kabinetten = POLITIEK_DATA.kabinetten.length;
  const beloftes   = POLITIEK_DATA.beloftes.length;
  const nagekomen  = POLITIEK_DATA.beloftes.filter(b => b.status === 'nagekomen').length;
  const pct = Math.round((nagekomen / beloftes) * 100);

  const stats = [
    { num: actievePartijen, label: 'Actieve partijen' },
    { num: POLITIEK_DATA.verkiezingen.length, label: 'Verkiezingen (1998–2023)' },
    { num: kabinetten, label: 'Kabinetten in kaart' },
    { num: pct + '%', label: 'Beloftes nagekomen' },
  ];

  container.innerHTML = stats.map(s => `
    <div class="stat-card">
      <span class="stat-num">${s.num}</span>
      <span class="stat-label">${s.label}</span>
    </div>
  `).join('');
}

// ============================================================
// PARTIJEN GRID
// ============================================================
function renderPartijGrid(containerId, filter) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let partijen = POLITIEK_DATA.partijen;

  if (filter === 'actief')     partijen = partijen.filter(p => p.actief);
  if (filter === 'historisch') partijen = partijen.filter(p => !p.actief);
  if (filter === 'coalitie')   partijen = partijen.filter(p => COALITIE_2024.includes(p.id));
  if (filter === 'links')      partijen = partijen.filter(p => IDEOLOGIE_KLEUR[p.ideologie] === 'links');
  if (filter === 'rechts')     partijen = partijen.filter(p => IDEOLOGIE_KLEUR[p.ideologie] === 'rechts');
  if (filter === 'christen')   partijen = partijen.filter(p => IDEOLOGIE_KLEUR[p.ideologie] === 'christen');

  container.innerHTML = partijen.map(p => {
    const inactief = !p.actief;
    return `
      <div class="partij-card ${inactief ? 'partij-inactief' : ''}" onclick="openPartijModal('${p.id}')" title="${p.naam}">
        ${inactief ? '<div class="partij-inactief-badge">Historisch</div>' : ''}
        <div class="partij-card-kleur" style="background:${p.kleur};"></div>
        <div class="partij-card-body">
          <div class="partij-afkorting" style="color:${p.kleur};">${p.id}</div>
          <div class="partij-naam-full">${p.naam}</div>
          <div class="partij-zetels-row">
            <div>
              <div class="partij-zetels">${p.huidigeZetels}</div>
              <div class="partij-zetels-label">zetels 2023</div>
            </div>
          </div>
          <div class="partij-ideologie">${p.ideologie}</div>
        </div>
      </div>
    `;
  }).join('');
}

function filterPartijen(filter, el) {
  document.querySelectorAll('#homeFilterChips .chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  renderPartijGrid('partijGrid', filter);
}

function filterPartijen2(filter, el) {
  document.querySelectorAll('#partijFilterChips .chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  renderPartijGrid('partijGrid2', filter);
}

// ============================================================
// KABINETTEN TIJDLIJN
// ============================================================
function renderKabinetTimeline(timelineId, detailId) {
  const timeline = document.getElementById(timelineId);
  if (!timeline) return;

  // Remove existing items (keep the line)
  timeline.querySelectorAll('.kabinet-item').forEach(el => el.remove());

  POLITIEK_DATA.kabinetten.forEach((kab, i) => {
    const coalitieHTML = kab.coalitie.map(pid => {
      const p = getPartij(pid);
      return `<div class="dot-partij" style="background:${p ? p.kleur : '#999'};" title="${pid}" data-tip="${pid}">${pid.substring(0,3)}</div>`;
    }).join('');

    const item = document.createElement('div');
    item.className = 'kabinet-item';
    item.dataset.id = kab.id;
    item.innerHTML = `
      <div class="kabinet-dot"></div>
      <div class="kabinet-card">
        ${kab.gevallen ? '<div class="kabinet-gevallen" title="Kabinet gevallen"></div>' : ''}
        <div class="kabinet-naam">${kab.naam}</div>
        <div class="kabinet-periode">${formatJaar(kab.start)} – ${formatJaar(kab.eind)}</div>
        <div class="kabinet-coalitie-dots">${coalitieHTML}</div>
      </div>
    `;
    item.onclick = () => showKabinetDetail(kab, detailId, timelineId);
    timeline.appendChild(item);
  });
}

function showKabinetDetail(kab, detailId, timelineId) {
  // Update active state
  document.querySelectorAll(`#${timelineId} .kabinet-item`).forEach(el => {
    el.classList.toggle('active', el.dataset.id === kab.id);
  });

  const detail = document.getElementById(detailId);
  if (!detail) return;

  const coalitieChips = kab.coalitie.map(pid => {
    const p = getPartij(pid);
    return `<div class="coalitie-partij-chip" style="background:${p ? p.kleur : '#999'};">${pid}</div>`;
  }).join('');

  const hoogtepunten = (kab.hoogtepunten || []).map(h => `<li>${h}</li>`).join('');

  // Beloftes for coalition parties
  const coalitieBeloftes = POLITIEK_DATA.beloftes.filter(b => kab.coalitie.includes(b.partij));
  const nagekomen = coalitieBeloftes.filter(b => b.status === 'nagekomen').length;
  const gebroken  = coalitieBeloftes.filter(b => b.status === 'gebroken').length;
  const deels     = coalitieBeloftes.filter(b => b.status === 'deels').length;

  detail.innerHTML = `
    <div class="kabinet-detail-header">
      <div class="kabinet-detail-icon">🏛</div>
      <div style="flex:1;">
        <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;margin-bottom:.35rem;">
          <h2 style="font-size:1.3rem;">${kab.naam}</h2>
          ${kab.gevallen
            ? `<span class="badge-gevallen">⚠ Gevallen</span>`
            : `<span class="badge-stabiel">✓ Voltooid</span>`}
        </div>
        <div style="color:var(--tekst-licht);font-size:.875rem;">
          Premier: <strong>${kab.premier}</strong> &nbsp;·&nbsp;
          ${formatDatum(kab.start)} – ${formatDatum(kab.eind)}&nbsp;·&nbsp;
          ${kab.zetels} zetels
        </div>
        <div class="coalitie-partijen" style="margin-top:.5rem;">
          ${coalitieChips}
          ${kab.gedoogd ? `<div class="coalitie-partij-chip" style="background:#888;font-style:italic;">${kab.gedoogd} (gedoogd)</div>` : ''}
        </div>
      </div>
    </div>

    <div class="kabinet-detail-grid">
      <div>
        <p style="color:var(--tekst-licht);font-size:.9rem;line-height:1.75;margin-bottom:1.25rem;">${kab.beschrijving}</p>

        ${kab.gevallen && kab.valReden ? `
        <div style="background:#FEE2E2;border-radius:var(--radius);padding:.9rem 1rem;margin-bottom:1rem;">
          <strong style="color:var(--rood);font-size:.85rem;">Reden van val:</strong>
          <p style="color:#7F1D1D;font-size:.85rem;margin-top:.2rem;">${kab.valReden}</p>
        </div>` : ''}

        ${hoogtepunten ? `
        <h4 style="margin-bottom:.5rem;font-size:.95rem;">Hoogtepunten & beslissingen</h4>
        <ul class="hoogtepunten-list">${hoogtepunten}</ul>` : ''}
      </div>
      <div>
        <div style="background:var(--grijs-licht);border-radius:var(--radius);padding:1rem;">
          <h4 style="margin-bottom:.75rem;font-size:.9rem;">Coalitiebeloftes nakoming</h4>
          ${coalitieBeloftes.length > 0 ? `
          <div style="font-size:.8rem;color:var(--tekst-licht);margin-bottom:.75rem;">${coalitieBeloftes.length} beloftes geanalyseerd</div>
          <div class="nakoming-stat">
            <div class="nak-pill nagekomen">✅ ${nagekomen} nagekomen</div>
            <div class="nak-pill deels">⚠️ ${deels} deels</div>
            <div class="nak-pill gebroken">❌ ${gebroken} gebroken</div>
          </div>
          <div style="margin-top:1rem;">
            <div style="height:8px;background:var(--grijs);border-radius:4px;overflow:hidden;display:flex;">
              <div style="width:${Math.round(nagekomen/coalitieBeloftes.length*100)}%;background:var(--groen);"></div>
              <div style="width:${Math.round(deels/coalitieBeloftes.length*100)}%;background:var(--oranje);"></div>
              <div style="width:${Math.round(gebroken/coalitieBeloftes.length*100)}%;background:var(--rood);"></div>
            </div>
          </div>
          ` : '<p style="font-size:.8rem;color:var(--grijs-donker);">Geen beloftedata beschikbaar</p>'}
        </div>

        <div style="background:var(--grijs-licht);border-radius:var(--radius);padding:1rem;margin-top:1rem;">
          <h4 style="margin-bottom:.5rem;font-size:.9rem;">Duur van het kabinet</h4>
          <div style="font-size:1.5rem;font-weight:800;color:var(--blauw);">${berekenDagen(kab.start, kab.eind)} dagen</div>
          <div style="font-size:.78rem;color:var(--grijs-donker);">${berekenJaren(kab.start, kab.eind)}</div>
        </div>
      </div>
    </div>
  `;

  detail.classList.add('visible');
  detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ============================================================
// KABINETTEN LIJST (page kabinetten)
// ============================================================
function renderKabinettenLijst() {
  const container = document.getElementById('kabinettenLijst');
  if (!container) return;

  container.innerHTML = `
    <div class="section-title" style="margin-bottom:1.5rem;margin-top:2rem;">Alle Kabinetten</div>
    ${POLITIEK_DATA.kabinetten.map(kab => {
      const coalitieChips = kab.coalitie.map(pid => {
        const p = getPartij(pid);
        return `<div class="coalitie-partij-chip" style="background:${p ? p.kleur : '#999'};font-size:.72rem;padding:.2rem .5rem;">${pid}</div>`;
      }).join('');

      return `
      <div style="background:var(--wit);border-radius:var(--radius-lg);padding:1.5rem;margin-bottom:1rem;box-shadow:var(--schaduw-sm);cursor:pointer;transition:var(--trans);"
           onmouseenter="this.style.boxShadow='var(--schaduw)'"
           onmouseleave="this.style.boxShadow='var(--schaduw-sm)'"
           onclick="showKabinetDetail(POLITIEK_DATA.kabinetten.find(k=>k.id==='${kab.id}'), 'kabinetDetail2', 'kabinetTimeline2')">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
          <div style="flex:1;">
            <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.4rem;flex-wrap:wrap;">
              <h3 style="font-size:1.05rem;">${kab.naam}</h3>
              ${kab.gevallen ? '<span class="badge-gevallen">Gevallen</span>' : '<span class="badge-stabiel">Voltooid</span>'}
            </div>
            <div style="font-size:.85rem;color:var(--tekst-licht);margin-bottom:.6rem;">
              <strong>${kab.premier}</strong> &nbsp;·&nbsp; ${formatDatum(kab.start)} – ${formatDatum(kab.eind)}
            </div>
            <div style="display:flex;gap:.4rem;flex-wrap:wrap;">${coalitieChips}</div>
          </div>
          <div style="text-align:right;flex-shrink:0;">
            <div style="font-size:1.3rem;font-weight:800;color:var(--blauw);">${berekenDagen(kab.start, kab.eind)}</div>
            <div style="font-size:.72rem;color:var(--grijs-donker);">dagen</div>
          </div>
        </div>
      </div>
      `;
    }).join('')}
  `;
}

// ============================================================
// OVERZICHTSGRAFIEK (home)
// ============================================================
function renderOverviewChart() {
  const canvas = document.getElementById('overviewChart');
  if (!canvas) return;

  const jaren = POLITIEK_DATA.verkiezingen.map(v => v.jaar);
  const datasets = HOOFD_PARTIJEN.map(pid => {
    const p = getPartij(pid);
    const data = POLITIEK_DATA.verkiezingen.map(v => v.zetels[pid] || 0);
    return {
      label: pid,
      data,
      borderColor: p ? p.kleur : '#999',
      backgroundColor: p ? hexToRgba(p.kleur, .08) : 'transparent',
      borderWidth: 2.5,
      pointRadius: 4,
      pointHoverRadius: 6,
      tension: 0.3,
      fill: false,
    };
  });

  if (overviewChart) overviewChart.destroy();
  overviewChart = new Chart(canvas, {
    type: 'line',
    data: { labels: jaren, datasets },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} zetels`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,.05)' },
          ticks: { color: '#6B7A8D' },
          title: { display: true, text: 'Zetels', color: '#6B7A8D' }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#6B7A8D' },
        }
      }
    }
  });

  // Legend
  const legend = document.getElementById('overviewLegend');
  if (legend) {
    legend.innerHTML = HOOFD_PARTIJEN.map(pid => {
      const p = getPartij(pid);
      return `<div class="legend-item" style="cursor:pointer;" onclick="openPartijModal('${pid}')">
        <div class="legend-dot" style="background:${p ? p.kleur : '#999'};"></div>
        ${pid}
      </div>`;
    }).join('');
  }
}

// ============================================================
// PARTIJ MODAL
// ============================================================
function openPartijModal(partijId) {
  const partij = getPartij(partijId);
  if (!partij) return;
  activePartij = partij;

  // Color bar
  document.getElementById('modalKleurBar').style.background = partij.kleur;

  // Header
  document.getElementById('modalHeader').innerHTML = `
    <div class="modal-partij-logo" style="background:${partij.kleur};">${partij.id.substring(0,3)}</div>
    <div style="flex:1;">
      <h2 id="modalTitle" style="font-size:1.35rem;margin-bottom:.2rem;color:${partij.kleur};">${partij.id}</h2>
      <p style="color:var(--tekst-licht);font-size:.9rem;margin-bottom:.4rem;">${partij.naam}</p>
      <span style="font-size:.78rem;padding:.2rem .6rem;border-radius:20px;background:var(--grijs-licht);color:var(--tekst-licht);">
        ${partij.ideologie}
      </span>
      ${!partij.actief ? '<span style="font-size:.78rem;padding:.2rem .6rem;border-radius:20px;background:var(--grijs);color:var(--grijs-donker);margin-left:.4rem;">Historisch</span>' : ''}
    </div>
  `;

  // Info cards
  const jaarZetels = getJongsteZetels(partijId);
  const aanwezigheidGem = getGemAanwezigheid(partijId);
  const beloftesPartij = POLITIEK_DATA.beloftes.filter(b => b.partij === partijId);
  const nagekomenPct = beloftesPartij.length
    ? Math.round(beloftesPartij.filter(b => b.status === 'nagekomen').length / beloftesPartij.length * 100)
    : null;

  document.getElementById('modalInfoGrid').innerHTML = `
    <div class="info-card" style="border-left-color:${partij.kleur};">
      <div class="info-card-label">Zetels 2023</div>
      <div class="info-card-value">${partij.huidigeZetels}</div>
    </div>
    <div class="info-card" style="border-left-color:${partij.kleur};">
      <div class="info-card-label">Opgericht</div>
      <div class="info-card-value">${partij.opgericht}</div>
    </div>
    <div class="info-card" style="border-left-color:${partij.kleur};">
      <div class="info-card-label">Gem. aanwezigheid</div>
      <div class="info-card-value">${aanwezigheidGem !== null ? aanwezigheidGem + '%' : 'n.v.t.'}</div>
    </div>
    <div class="info-card" style="border-left-color:${partij.kleur};">
      <div class="info-card-label">Beloftes nagekomen</div>
      <div class="info-card-value">${nagekomenPct !== null ? nagekomenPct + '%' : 'n.v.t.'}</div>
    </div>
  `;

  // Reset tabs
  switchTab('profiel');

  // Fill all tabs
  fillProfielTab(partij);
  fillZetelsTab(partij);
  fillBeloftesTab(partij);
  fillStemgedragTab(partij);
  fillFinancienTab(partij);
  fillAanwezigheidTab(partij);

  // Open modal
  document.getElementById('partijModal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('partijModal').classList.remove('open');
  document.body.style.overflow = '';
}

function closeModalOutside(e) {
  if (e.target === document.getElementById('partijModal')) closeModal();
}

function switchTab(tabName) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));

  const panel = document.getElementById('tab-' + tabName);
  if (panel) panel.classList.add('active');

  document.querySelectorAll('.modal-tab').forEach(t => {
    if (t.getAttribute('onclick') && t.getAttribute('onclick').includes(tabName)) {
      t.classList.add('active');
    }
  });

  // Refresh charts when tab becomes visible
  if (tabName === 'zetels' && zetelsChart)       zetelsChart.update();
  if (tabName === 'financien' && financienChart)  financienChart.update();
  if (tabName === 'aanwezigheid' && aanwezigheidChart) aanwezigheidChart.update();
}

// --- PROFIEL TAB ---
function fillProfielTab(partij) {
  const kabinetten = POLITIEK_DATA.kabinetten.filter(k => k.coalitie.includes(partij.id));
  const kabHTML = kabinetten.length
    ? kabinetten.map(k => `<span onclick="showPage('kabinetten')" style="cursor:pointer;color:var(--blauw);font-weight:600;">${k.naam}</span>`).join(', ')
    : '<em style="color:var(--grijs-donker);">Nooit in coalitie (2000–2025)</em>';

  document.getElementById('profielContent').innerHTML = `
    <p style="color:var(--tekst-licht);line-height:1.8;font-size:.95rem;margin-bottom:1.5rem;">${partij.omschrijving}</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">
      <div style="background:var(--grijs-licht);border-radius:var(--radius);padding:1rem;">
        <div style="font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:var(--grijs-donker);margin-bottom:.3rem;">Ideologie</div>
        <div style="font-weight:600;">${partij.ideologie}</div>
      </div>
      <div style="background:var(--grijs-licht);border-radius:var(--radius);padding:1rem;">
        <div style="font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:var(--grijs-donker);margin-bottom:.3rem;">Status</div>
        <div style="font-weight:600;">${partij.actief ? '✅ Actief' : '🔴 Opgeheven / Niet meer in Kamer'}</div>
      </div>
    </div>
    <div style="background:var(--grijs-licht);border-radius:var(--radius);padding:1rem;">
      <div style="font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:var(--grijs-donker);margin-bottom:.5rem;">Regeringsdeelname 1998–2025</div>
      <div>${kabHTML}</div>
    </div>
  `;
}

// --- ZETELS TAB ---
function fillZetelsTab(partij) {
  const jaren  = POLITIEK_DATA.verkiezingen.map(v => v.jaar);
  const zetels = POLITIEK_DATA.verkiezingen.map(v => v.zetels[partij.id] || 0);

  const canvas = document.getElementById('zetelsChart');
  if (zetelsChart) zetelsChart.destroy();

  zetelsChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: jaren,
      datasets: [{
        label: 'Zetels',
        data: zetels,
        backgroundColor: hexToRgba(partij.kleur, .75),
        borderColor: partij.kleur,
        borderWidth: 2,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${ctx.raw} zetels` } }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: '#6B7A8D', stepSize: 5 },
          grid: { color: 'rgba(0,0,0,.05)' },
        },
        x: { grid: { display: false }, ticks: { color: '#6B7A8D' } }
      }
    }
  });

  // Table
  const tableHTML = `
    <table class="stem-table">
      <thead><tr><th>Jaar</th><th>Zetels</th><th>Trend</th><th>Opkomst</th></tr></thead>
      <tbody>
        ${POLITIEK_DATA.verkiezingen.map((v, i) => {
          const z = v.zetels[partij.id] || 0;
          const prev = i > 0 ? (POLITIEK_DATA.verkiezingen[i-1].zetels[partij.id] || 0) : null;
          const trend = prev === null ? '—'
            : z > prev ? `<span style="color:var(--groen)">▲ +${z-prev}</span>`
            : z < prev ? `<span style="color:var(--rood)">▼ ${z-prev}</span>`
            : '→ ±0';
          return `<tr>
            <td><strong>${v.jaar}</strong></td>
            <td><strong>${z}</strong></td>
            <td>${trend}</td>
            <td>${v.opkomst}%</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  `;
  document.getElementById('zetelsTable').innerHTML = tableHTML;
}

// --- BELOFTES TAB ---
function fillBeloftesTab(partij) {
  const beloftes = POLITIEK_DATA.beloftes.filter(b => b.partij === partij.id);

  if (!beloftes.length) {
    document.getElementById('beloftesContent').innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <h3>Geen beloftesdata</h3>
        <p>Voor ${partij.id} zijn geen beloftes geregistreerd.</p>
      </div>
    `;
    return;
  }

  const nagekomen = beloftes.filter(b => b.status === 'nagekomen').length;
  const deels     = beloftes.filter(b => b.status === 'deels').length;
  const gebroken  = beloftes.filter(b => b.status === 'gebroken').length;

  const statusIcon = { nagekomen: '✅', deels: '⚠️', gebroken: '❌' };

  document.getElementById('beloftesContent').innerHTML = `
    <div class="nakoming-stat" style="margin-bottom:1.25rem;">
      <div class="nak-pill nagekomen">✅ ${nagekomen} nagekomen</div>
      <div class="nak-pill deels">⚠️ ${deels} deels</div>
      <div class="nak-pill gebroken">❌ ${gebroken} gebroken</div>
    </div>
    <div style="height:8px;background:var(--grijs);border-radius:4px;overflow:hidden;display:flex;margin-bottom:1.5rem;">
      <div style="width:${Math.round(nagekomen/beloftes.length*100)}%;background:var(--groen);"></div>
      <div style="width:${Math.round(deels/beloftes.length*100)}%;background:var(--oranje);"></div>
      <div style="width:${Math.round(gebroken/beloftes.length*100)}%;background:var(--rood);"></div>
    </div>
    <ul class="beloftes-list">
      ${beloftes.map(b => `
        <li class="belofte-item">
          <div class="belofte-status status-${b.status}">${statusIcon[b.status] || '?'}</div>
          <div>
            <div class="belofte-text">${b.omschrijving}</div>
            <div class="belofte-cat">${b.categorie} &nbsp;·&nbsp; <span class="belofte-jaar">${b.jaar}</span></div>
          </div>
        </li>
      `).join('')}
    </ul>
  `;
}

// --- STEMGEDRAG TAB ---
function fillStemgedragTab(partij) {
  const table = document.getElementById('stemTable');
  const stemmen = POLITIEK_DATA.stemgedrag.filter(s => s.partij === partij.id);

  const stemMap = {};
  stemmen.forEach(s => { stemMap[s.wetId] = s.stem; });

  const stemLabel = { voor: '✔ Voor', tegen: '✘ Tegen', onthouden: '◐ Onthouden', afwezig: '— Afwezig' };
  const stemClass = { voor: 'stem-voor', tegen: 'stem-tegen', onthouden: 'stem-onthouden', afwezig: 'stem-afwezig' };

  table.innerHTML = `
    <thead>
      <tr>
        <th>Wet / Besluit</th>
        <th>Jaar</th>
        <th>Stem</th>
      </tr>
    </thead>
    <tbody>
      ${POLITIEK_DATA.wetten.map(wet => {
        const stem = stemMap[wet.id];
        const badge = stem
          ? `<span class="stem-badge ${stemClass[stem]}">${stemLabel[stem]}</span>`
          : `<span class="stem-badge stem-afwezig">— Niet geregistreerd</span>`;
        return `
          <tr>
            <td>
              <div style="font-weight:600;font-size:.82rem;">${wet.naam}</div>
              <div style="font-size:.72rem;color:var(--tekst-licht);margin-top:.15rem;">${wet.omschrijving.substring(0, 70)}…</div>
            </td>
            <td style="white-space:nowrap;">${wet.jaar}</td>
            <td>${badge}</td>
          </tr>
        `;
      }).join('')}
    </tbody>
  `;
}

// --- FINANCIEN TAB ---
function fillFinancienTab(partij) {
  const fin = POLITIEK_DATA.financien.filter(f => f.partij === partij.id);

  const canvas = document.getElementById('financienChart');
  if (financienChart) financienChart.destroy();

  if (!fin.length) {
    canvas.parentElement.innerHTML = '<p style="color:var(--grijs-donker);text-align:center;padding:1rem;">Geen financiëndata beschikbaar</p>';
    return;
  }

  const jaren = fin.map(f => f.jaar);

  financienChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: jaren,
      datasets: [
        {
          label: 'Subsidie',
          data: fin.map(f => f.subsidie),
          backgroundColor: hexToRgba('#154273', .8),
          borderRadius: 4,
        },
        {
          label: 'Donaties',
          data: fin.map(f => f.donaties),
          backgroundColor: hexToRgba('#D4A017', .8),
          borderRadius: 4,
        },
        {
          label: 'Contributies',
          data: fin.map(f => f.contributies),
          backgroundColor: hexToRgba('#27AE60', .8),
          borderRadius: 4,
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: €${(ctx.raw/1000000).toFixed(2)} mln`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          stacked: true,
          ticks: {
            color: '#6B7A8D',
            callback: v => '€' + (v/1000000).toFixed(1) + ' mln'
          },
          grid: { color: 'rgba(0,0,0,.05)' },
        },
        x: { stacked: true, grid: { display: false }, ticks: { color: '#6B7A8D' } }
      }
    }
  });
}

// --- AANWEZIGHEID TAB ---
function fillAanwezigheidTab(partij) {
  const data = POLITIEK_DATA.aanwezigheid.filter(a => a.partij === partij.id);

  const canvas = document.getElementById('aanwezigheidChart');
  if (aanwezigheidChart) aanwezigheidChart.destroy();

  if (!data.length) {
    canvas.parentElement.innerHTML = '<p style="color:var(--grijs-donker);text-align:center;padding:1rem;">Geen aanwezigheidsdata beschikbaar</p>';
    document.getElementById('aanwezigheidTable').innerHTML = '';
    return;
  }

  aanwezigheidChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: data.map(d => d.jaar),
      datasets: [{
        label: 'Aanwezigheid %',
        data: data.map(d => d.percentage),
        borderColor: partij.kleur,
        backgroundColor: hexToRgba(partij.kleur, .1),
        borderWidth: 2.5,
        pointRadius: 5,
        fill: true,
        tension: 0.3,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${ctx.raw}% aanwezig` } }
      },
      scales: {
        y: {
          min: 0, max: 100,
          ticks: { color: '#6B7A8D', callback: v => v + '%' },
          grid: { color: 'rgba(0,0,0,.05)' },
        },
        x: { grid: { display: false }, ticks: { color: '#6B7A8D' } }
      }
    }
  });

  // Table
  document.getElementById('aanwezigheidTable').innerHTML = `
    <table class="stem-table">
      <thead><tr><th>Jaar</th><th>Aanwezigheid</th><th>Balk</th></tr></thead>
      <tbody>
        ${data.map(d => `
          <tr>
            <td><strong>${d.jaar}</strong></td>
            <td><strong>${d.percentage}%</strong></td>
            <td style="width:60%;">
              <div class="aanwezigheid-bar">
                <div class="aanwezigheid-fill" style="width:${d.percentage}%;background:${partij.kleur};"></div>
              </div>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

// ============================================================
// VERGELIJKING
// ============================================================
function populateVergelijkSelects() {
  const actievePartijen = POLITIEK_DATA.partijen.filter(p => p.actief);
  const options = actievePartijen.map(p => `<option value="${p.id}">${p.id} — ${p.naam}</option>`).join('');

  ['vsel1','vsel2','vsel3'].forEach(id => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const defaultOpt = id === 'vsel3' ? '<option value="">— Geen —</option>' : '<option value="">— Kies partij —</option>';
    sel.innerHTML = defaultOpt + options;
  });

  // Set defaults
  const sel1 = document.getElementById('vsel1');
  const sel2 = document.getElementById('vsel2');
  if (sel1) sel1.value = 'VVD';
  if (sel2) sel2.value = 'PvdA';
}

let vergelijkChart = null;

function updateVergelijk() {
  const ids = [
    document.getElementById('vsel1')?.value,
    document.getElementById('vsel2')?.value,
    document.getElementById('vsel3')?.value,
  ].filter(Boolean);

  const result = document.getElementById('vergelijkResult');
  if (!result) return;

  if (ids.length < 2) {
    result.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚖️</div>
        <h3>Selecteer minimaal 2 partijen</h3>
        <p>Kies partijen in de dropdowns hierboven.</p>
      </div>
    `;
    return;
  }

  const partijen = ids.map(id => getPartij(id)).filter(Boolean);

  // Columns
  const columns = partijen.map(p => {
    const beloftes    = POLITIEK_DATA.beloftes.filter(b => b.partij === p.id);
    const nagekomen   = beloftes.filter(b => b.status === 'nagekomen').length;
    const nakomingPct = beloftes.length ? Math.round(nagekomen / beloftes.length * 100) : null;
    const aanwGem     = getGemAanwezigheid(p.id);
    const finData     = POLITIEK_DATA.financien.filter(f => f.partij === p.id);
    const totaalGem   = finData.length
      ? Math.round(finData.reduce((a,f) => a + f.subsidie + f.donaties + f.contributies, 0) / finData.length)
      : null;
    const kabinetten  = POLITIEK_DATA.kabinetten.filter(k => k.coalitie.includes(p.id)).length;

    const metrics = [
      { label: 'Zetels 2023',       value: p.huidigeZetels + ' zetels' },
      { label: 'Ideologie',          value: p.ideologie },
      { label: 'Opgericht',          value: p.opgericht },
      { label: 'Kabinetten',         value: kabinetten + 'x in coalitie' },
      { label: 'Beloftes nagekomen', value: nakomingPct !== null ? nakomingPct + '%' : 'n.v.t.' },
      { label: 'Gem. aanwezigheid',  value: aanwGem !== null ? aanwGem + '%' : 'n.v.t.' },
      { label: 'Gem. financiën/jr',  value: totaalGem ? '€' + (totaalGem/1000000).toFixed(1) + ' mln' : 'n.v.t.' },
    ];

    return { partij: p, metrics };
  });

  result.innerHTML = `
    <div class="vergelijk-columns" style="grid-template-columns: repeat(${partijen.length}, 1fr);">
      ${columns.map(col => `
        <div class="vergelijk-col">
          <div class="vergelijk-col-header" style="background:${col.partij.kleur};">
            <h3>${col.partij.id}</h3>
            <p>${col.partij.naam}</p>
          </div>
          <div class="vergelijk-col-body">
            ${col.metrics.map(m => `
              <div class="vergelijk-metric">
                <span class="vergelijk-metric-label">${m.label}</span>
                <span class="vergelijk-metric-value">${m.value}</span>
              </div>
            `).join('')}
            <div style="margin-top:1rem;">
              <button class="btn btn-primary" style="width:100%;font-size:.8rem;" onclick="openPartijModal('${col.partij.id}')">
                Volledig profiel →
              </button>
            </div>
          </div>
        </div>
      `).join('')}
    </div>

    <!-- Zetels vergelijkgrafiek -->
    <div class="vergelijk-chart-area">
      <h4 style="margin-bottom:1rem;font-size:1rem;">Zetels door de jaren</h4>
      <div class="vergelijk-chart-wrap">
        <canvas id="vergelijkChart" height="80"></canvas>
      </div>
    </div>

    <!-- Stemgedrag vergelijking -->
    <div style="margin-top:2rem;">
      <h4 style="margin-bottom:1rem;font-size:1rem;">Stemgedrag vergelijking</h4>
      ${renderStemgedragVergelijk(partijen)}
    </div>
  `;

  // Render zetels vergelijkgrafiek
  const vCanvas = document.getElementById('vergelijkChart');
  if (vCanvas) {
    if (vergelijkChart) vergelijkChart.destroy();
    const jaren = POLITIEK_DATA.verkiezingen.map(v => v.jaar);
    vergelijkChart = new Chart(vCanvas, {
      type: 'line',
      data: {
        labels: jaren,
        datasets: partijen.map(p => ({
          label: p.id,
          data: POLITIEK_DATA.verkiezingen.map(v => v.zetels[p.id] || 0),
          borderColor: p.kleur,
          backgroundColor: hexToRgba(p.kleur, .08),
          borderWidth: 2.5,
          pointRadius: 4,
          fill: false,
          tension: 0.3,
        }))
      },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: true, labels: { color: '#1A2332', font: { size: 12 } } },
          tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} zetels` } }
        },
        scales: {
          y: { beginAtZero: true, ticks: { color: '#6B7A8D' }, grid: { color: 'rgba(0,0,0,.05)' } },
          x: { grid: { display: false }, ticks: { color: '#6B7A8D' } }
        }
      }
    });
  }
}

function renderStemgedragVergelijk(partijen) {
  const stemLabel = { voor: '✔', tegen: '✘', onthouden: '◐' };
  const stemClass = { voor: 'stem-voor', tegen: 'stem-tegen', onthouden: 'stem-onthouden' };

  return `<div style="overflow-x:auto;">
    <table class="stem-table">
      <thead>
        <tr>
          <th>Wet</th>
          <th>Jaar</th>
          ${partijen.map(p => `<th style="color:${p.kleur};">${p.id}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${POLITIEK_DATA.wetten.map(wet => {
          const stemmen = partijen.map(p => {
            const s = POLITIEK_DATA.stemgedrag.find(sg => sg.partij === p.id && sg.wetId === wet.id);
            if (!s) return `<td>—</td>`;
            return `<td><span class="stem-badge ${stemClass[s.stem] || 'stem-afwezig'}">${stemLabel[s.stem] || '—'} ${s.stem}</span></td>`;
          }).join('');
          return `<tr>
            <td style="font-weight:600;font-size:.8rem;">${wet.naam}</td>
            <td>${wet.jaar}</td>
            ${stemmen}
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  </div>`;
}

// ============================================================
// ZOEKFUNCTIE
// ============================================================
function handleSearch(query) {
  const results = document.getElementById('searchResults');
  if (!results) return;

  if (!query || query.length < 2) {
    results.classList.remove('open');
    return;
  }

  const q = query.toLowerCase();
  const partijMatches = POLITIEK_DATA.partijen.filter(p =>
    p.id.toLowerCase().includes(q) ||
    p.naam.toLowerCase().includes(q) ||
    p.ideologie.toLowerCase().includes(q)
  );
  const kabMatches = POLITIEK_DATA.kabinetten.filter(k =>
    k.naam.toLowerCase().includes(q) ||
    k.premier.toLowerCase().includes(q)
  );

  if (!partijMatches.length && !kabMatches.length) {
    results.innerHTML = '<div style="padding:1rem;color:var(--grijs-donker);font-size:.85rem;">Geen resultaten gevonden.</div>';
    results.classList.add('open');
    return;
  }

  const html = [
    ...partijMatches.map(p => `
      <div class="search-result-item" onclick="closeSearch(); openPartijModal('${p.id}')">
        <div class="search-result-icon" style="background:${p.kleur};">${p.id.substring(0,3)}</div>
        <div>
          <div style="font-weight:600;font-size:.875rem;">${p.id}</div>
          <div style="font-size:.75rem;color:var(--tekst-licht);">${p.naam}</div>
        </div>
      </div>
    `),
    ...kabMatches.map(k => `
      <div class="search-result-item" onclick="closeSearch(); showPage('kabinetten');">
        <div class="search-result-icon" style="background:var(--blauw);">🏛</div>
        <div>
          <div style="font-weight:600;font-size:.875rem;">${k.naam}</div>
          <div style="font-size:.75rem;color:var(--tekst-licht);">${k.premier} · ${formatJaar(k.start)}–${formatJaar(k.eind)}</div>
        </div>
      </div>
    `)
  ].join('');

  results.innerHTML = html;
  results.classList.add('open');
}

function closeSearch() {
  const results = document.getElementById('searchResults');
  if (results) results.classList.remove('open');
  const input = document.getElementById('searchInput');
  if (input) input.value = '';
}

// ============================================================
// BACK TO TOP
// ============================================================
function initBackToTop() {
  const btn = document.getElementById('backToTop');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 400);
  });
}

// ============================================================
// HELPER FUNCTIONS
// ============================================================
function getPartij(id) {
  return POLITIEK_DATA.partijen.find(p => p.id === id) || null;
}

function getGemAanwezigheid(partijId) {
  const data = POLITIEK_DATA.aanwezigheid.filter(a => a.partij === partijId);
  if (!data.length) return null;
  return Math.round(data.reduce((sum, a) => sum + a.percentage, 0) / data.length);
}

function getJongsteZetels(partijId) {
  for (let i = POLITIEK_DATA.verkiezingen.length - 1; i >= 0; i--) {
    const z = POLITIEK_DATA.verkiezingen[i].zetels[partijId];
    if (z !== undefined) return { jaar: POLITIEK_DATA.verkiezingen[i].jaar, zetels: z };
  }
  return null;
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1,3), 16);
  const g = parseInt(hex.slice(3,5), 16);
  const b = parseInt(hex.slice(5,7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function formatDatum(d) {
  if (!d) return '?';
  const maanden = ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec'];
  const parts = d.split('-');
  return `${parseInt(parts[2])} ${maanden[parseInt(parts[1])-1]} ${parts[0]}`;
}

function formatJaar(d) {
  if (!d) return '?';
  return d.split('-')[0];
}

function berekenDagen(start, eind) {
  if (!start || !eind) return '?';
  const ms = new Date(eind) - new Date(start);
  return Math.round(ms / 86400000).toLocaleString('nl-NL');
}

function berekenJaren(start, eind) {
  if (!start || !eind) return '';
  const dagen = Math.round((new Date(eind) - new Date(start)) / 86400000);
  const jaren = Math.floor(dagen / 365);
  const rest  = Math.round((dagen % 365) / 30);
  if (jaren > 0) return `${jaren} jaar en ${rest} maanden`;
  return `${Math.round(dagen/30)} maanden`;
}

// Keyboard: ESC closes modal
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});
