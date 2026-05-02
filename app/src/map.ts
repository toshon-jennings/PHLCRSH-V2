import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { query } from './db';

function segmentPopupHTML(p: { crash_count?: number; canopy_pct?: number; cartway_width_ft?: number; grade_range_smooth?: number; maxspeed_final?: number }) {
  const row = (label: string, value: string) =>
    `<div class="seg-row"><span>${label}</span><strong>${value}</strong></div>`;
  const canopy = p.canopy_pct != null ? `${(p.canopy_pct * 100).toFixed(0)}%` : '—';
  const width  = p.cartway_width_ft != null ? `${(+p.cartway_width_ft).toFixed(0)} ft` : '—';
  const grade  = p.grade_range_smooth != null ? `${(p.grade_range_smooth * 100).toFixed(1)}%` : '—';
  const speed  = p.maxspeed_final != null ? `${(+p.maxspeed_final).toFixed(0)} mph` : '—';
  return `<div class="seg-popup">
    ${row('Crashes', String(p.crash_count ?? '—'))}
    ${row('Canopy', canopy)}
    ${row('Grade', grade)}
    ${row('Speed', speed)}
    ${row('Width', width)}
  </div>`;
}

export async function initMap(container: string) {
  let map = new maplibregl.Map({
    container,
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    center: [-75.1652, 39.9526],
    zoom: 11,
  });

  await map.once('load');

  const result = await query(`
  SELECT
    CAST(seg_id AS INTEGER)             AS seg_id,
    CAST(crash_count AS INTEGER)        AS crash_count,
    CAST(cartway_width_ft AS FLOAT)     AS cartway_width_ft,
    CAST(canopy_pct AS FLOAT)           AS canopy_pct,
    CAST(grade_range_smooth AS FLOAT)   AS grade_range_smooth,
    CAST(maxspeed_final AS FLOAT)       AS maxspeed_final,
    CAST(state_total_width_ft AS FLOAT) AS state_total_width_ft,
    CAST(state_lane_cnt AS INTEGER)     AS state_lane_cnt,
    GEOID,
    st_name,
    st_type,
    class                               AS road_class,
    state_divisor_type,
    ST_AsGeoJSON(geometry)              AS geojson
  FROM segments
`);


  const features = result.toArray().map((r: any) => ({
    type: 'Feature' as const,
    properties: {
      seg_id: r.seg_id,
      crash_count: r.crash_count,
      cartway_width_ft: r.cartway_width_ft,
      canopy_pct: r.canopy_pct,
      grade_range_smooth: r.grade_range_smooth,
      maxspeed_final: r.maxspeed_final,
      state_total_width_ft: r.state_total_width_ft,
      state_lane_cnt: r.state_lane_cnt,
      GEOID: r.GEOID,
      st_name: r.st_name,
      st_type: r.st_type,
      road_class: r.road_class,
      state_divisor_type: r.state_divisor_type,
    },
    geometry: JSON.parse(r.geojson),
  }));


  map = map.addSource('segments', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features },
    promoteId: 'seg_id',
  });

  map = map.addLayer({
    id: 'segments-line',
    type: 'line',
    source: 'segments',
    paint: {
      'line-color': [
        'step', ['get', 'crash_count'],
        '#ffffff',
        1, '#fee5d9',
        5, '#fcae91',
        25, '#fb6a4a',
        50, '#de2d26',
        100, '#a50f15',
      ],
      "line-width": [
        'step', ['get', 'cartway_width_ft'],
        1,
        5, 1,
        10, 1.5,
        50, 3.5,
        100, 5.5,
      ]
    },
  });


  map = map.addLayer({
    id: "canopy-pct",
    type: "line",
    source: "segments",
    paint: {
      "line-color": [
        'step', ['get', 'canopy_pct'],
        '#fff',
       0.05, '#e5f5e0',
       0.1, '#a1d99b',
       0.5, '#31a354'
      ],
      "line-width": [
        'step', ['get', 'cartway_width_ft'],
        1,
        5, 2,
        10, 3,
        50, 5,
        100, 8,
      ]
    }
  })

  map.addLayer({
    id: 'grade',
    type: 'line',
    source: 'segments',
    paint: {
      'line-color': [
        'step', ['get', 'grade_range_smooth'],
        '#f7f4f9',
        0.005, '#d4b9da',
        0.020, '#d281b3',
        0.060, '#cf27f1',
        0.100, '#ff0000',
      ],
      'line-width': [
        'step', ['get', 'cartway_width_ft'],
        1,
        5, 1,
        10, 1.5,
        50, 3.5,
        100, 5.5,
      ],
    },
  });

  map.addLayer({
    id: 'grade-outliers',
    type: 'line',
    source: 'segments',
    filter: ['>', ['get', 'grade_range_smooth'], 0.15],
    layout: { visibility: 'none' },
    paint: {
      'line-color': '#ffe500',
      'line-width': [
        'step', ['get', 'cartway_width_ft'],
        2, 5, 2, 10, 3, 50, 5, 100, 7,
      ],
      'line-opacity': 0.9,
    },
  });

  const dotSize = 16;
  const dotCanvas = document.createElement('canvas');
  dotCanvas.width = dotSize;
  dotCanvas.height = dotSize;
  const dotCtx = dotCanvas.getContext('2d')!;
  dotCtx.beginPath();
  dotCtx.arc(dotSize / 2, dotSize / 2, dotSize / 2 - 1.5, 0, Math.PI * 2);
  dotCtx.fillStyle = '#ffe500';
  dotCtx.fill();
  dotCtx.strokeStyle = '#222';
  dotCtx.lineWidth = 2.5;
  dotCtx.stroke();
  map.addImage('grade-outlier-dot', {
    width: dotSize,
    height: dotSize,
    data: new Uint8Array(dotCtx.getImageData(0, 0, dotSize, dotSize).data.buffer),
  });

  map.addLayer({
    id: 'grade-outlier-markers',
    type: 'symbol',
    source: 'segments',
    filter: ['>', ['get', 'grade_range_smooth'], 0.15],
    layout: {
      visibility: 'none',
      'symbol-placement': 'line-center',
      'icon-image': 'grade-outlier-dot',
      'icon-size': 1,
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
    },
  });

  // Interaction: canopy × cartway width
  // Quadrants: (low canopy / narrow), (high canopy / narrow), (low canopy / wide), (high canopy / wide)
  map.addLayer({
    id: 'inter-canopy-width',
    type: 'line',
    source: 'segments',
    layout: { visibility: 'none' },
    paint: {
      'line-color': [
        'case',
        ['all', ['<', ['get', 'cartway_width_ft'], 35], ['<', ['get', 'canopy_pct'], 0.1]],  '#d9d9d9',
        ['all', ['<', ['get', 'cartway_width_ft'], 35], ['>=', ['get', 'canopy_pct'], 0.1]], '#91cf60',
        ['all', ['>=', ['get', 'cartway_width_ft'], 35], ['<', ['get', 'canopy_pct'], 0.1]], '#fc8d59',
        ['all', ['>=', ['get', 'cartway_width_ft'], 35], ['>=', ['get', 'canopy_pct'], 0.1]],'#1a9850',
        '#d9d9d9',
      ],
      'line-width': [
        'step', ['get', 'cartway_width_ft'],
        1, 5, 1.5, 10, 2, 50, 4, 100, 6,
      ],
    },
  });

  // Interaction: grade × max speed
  map.addLayer({
    id: 'inter-grade-speed',
    type: 'line',
    source: 'segments',
    layout: { visibility: 'none' },
    paint: {
      'line-color': [
        'case',
        ['all', ['<', ['get', 'grade_range_smooth'], 0.02], ['<', ['get', 'maxspeed_final'], 35]],  '#d9d9d9',
        ['all', ['>=', ['get', 'grade_range_smooth'], 0.02], ['<', ['get', 'maxspeed_final'], 35]], '#fee08b',
        ['all', ['<', ['get', 'grade_range_smooth'], 0.02], ['>=', ['get', 'maxspeed_final'], 35]], '#fc8d59',
        ['all', ['>=', ['get', 'grade_range_smooth'], 0.02], ['>=', ['get', 'maxspeed_final'], 35]],'#d73027',
        '#d9d9d9',
      ],
      'line-width': [
        'step', ['get', 'cartway_width_ft'],
        1, 5, 1.5, 10, 2, 50, 4, 100, 6,
      ],
    },
  });

  const bgResult = await query(`
    SELECT
      GEOID,
      CAST(population AS INTEGER) AS population,
      CASE WHEN median_income < 0 THEN NULL ELSE CAST(median_income AS INTEGER) END AS median_income,
      ST_AsGeoJSON(geometry) AS geojson
    FROM block_groups
  `);

  const bgFeatures = bgResult.toArray().map((r: any) => ({
    type: 'Feature' as const,
    properties: { GEOID: r.GEOID, population: r.population, median_income: r.median_income },
    geometry: JSON.parse(r.geojson),
  }));

  map.addSource('block-groups', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: bgFeatures },
  });

  map.addLayer({
    id: 'population',
    type: 'fill',
    source: 'block-groups',
    paint: {
      'fill-color': [
        'step', ['get', 'population'],
        '#fff7ec',
        500,  '#fdd49e',
        1000, '#fdbb84',
        1500, '#fc8d59',
        2500, '#d7301f',
        3500, '#7f0000',
      ],
      'fill-opacity': 0.55,
    },
  });

  map.addLayer({
    id: 'median-income',
    type: 'fill',
    source: 'block-groups',
    paint: {
      'fill-color': [
        'case', ['==', ['get', 'median_income'], null as any], '#e8e8e8',
        ['step', ['get', 'median_income'],
          '#f7fbff',
          25000, '#c6dbef',
          50000, '#6baed6',
          75000, '#2171b5',
          125000, '#08306b',
        ]
      ],
      'fill-opacity': 0.55,
    },
  });

  // Glow highlight driven by feature-state
  map.addLayer({
    id: 'segments-highlight',
    type: 'line',
    source: 'segments',
    paint: {
      'line-color': '#fff',
      'line-width': ['case', ['boolean', ['feature-state', 'hover'], false], 5, 0],
      'line-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.85, 0],
      'line-blur': 2,
    },
  });

  // Pinned segment highlight
  map.addLayer({
    id: 'segments-pinned',
    type: 'line',
    source: 'segments',
    paint: {
      'line-color': '#ffe500',
      'line-width': ['case', ['boolean', ['feature-state', 'pinned'], false], 5, 0],
      'line-opacity': ['case', ['boolean', ['feature-state', 'pinned'], false], 1, 0],
    },
  });

  // Invisible wide layer on top for reliable hit detection
  map.addLayer({
    id: 'segments-hit',
    type: 'line',
    source: 'segments',
    paint: { 'line-color': 'transparent', 'line-width': 10, 'line-opacity': 0 },
  });

  let hoveredId: number | string | null = null;
  let pinnedSegId: number | string | null = null;
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });

  map.on('mousemove', 'segments-hit', (e) => {
    if (!e.features?.length) return;
    map.getCanvas().style.cursor = 'pointer';

    const id = e.features[0].id as number | string;
    if (hoveredId !== null && hoveredId !== id) {
      map.setFeatureState({ source: 'segments', id: hoveredId }, { hover: false });
    }
    hoveredId = id;
    map.setFeatureState({ source: 'segments', id }, { hover: true });

    if (id === pinnedSegId) { popup.remove(); return; }
    const p = e.features[0].properties as any;
    popup.setLngLat(e.lngLat).setHTML(segmentPopupHTML(p)).addTo(map);
  });

  map.on('mouseleave', 'segments-hit', () => {
    map.getCanvas().style.cursor = '';
    if (hoveredId !== null) {
      map.setFeatureState({ source: 'segments', id: hoveredId }, { hover: false });
      hoveredId = null;
    }
    popup.remove();
  });

  type LegendStop = { color: string; label: string };
  type Legend =
    | { kind: 'steps'; stops: LegendStop[] }
    | {
        kind: 'bivariate';
        xLabel: string; xLo: string; xHi: string;
        yLabel: string; yLo: string; yHi: string;
        // cells in order: yHi+xLo, yHi+xHi, yLo+xLo, yLo+xHi  (top-left, top-right, bottom-left, bottom-right)
        cells: [string, string, string, string];
      };

  const LEGENDS: Record<string, Legend> = {
    'segments-line': { kind: 'steps', stops: [
      { color: '#ffffff', label: '0' },
      { color: '#fee5d9', label: '1' },
      { color: '#fcae91', label: '5' },
      { color: '#fb6a4a', label: '25' },
      { color: '#de2d26', label: '50' },
      { color: '#a50f15', label: '100+' },
    ]},
    'canopy-pct': { kind: 'steps', stops: [
      { color: '#ffffff', label: '0%' },
      { color: '#e5f5e0', label: '5%' },
      { color: '#a1d99b', label: '10%' },
      { color: '#31a354', label: '50%+' },
    ]},
    'grade': { kind: 'steps', stops: [
      { color: '#f7f4f9', label: '0%' },
      { color: '#d4b9da', label: '0.5%' },
      { color: '#d281b3', label: '2%' },
      { color: '#cf27f1', label: '6%' },
      { color: '#ff0000', label: '10%+' },
    ]},
    'population': { kind: 'steps', stops: [
      { color: '#fff7ec', label: '0' },
      { color: '#fdd49e', label: '500' },
      { color: '#fdbb84', label: '1k' },
      { color: '#fc8d59', label: '1.5k' },
      { color: '#d7301f', label: '2.5k' },
      { color: '#7f0000', label: '3.5k+' },
    ]},
    'median-income': { kind: 'steps', stops: [
      { color: '#f7fbff', label: '$0' },
      { color: '#c6dbef', label: '$25k' },
      { color: '#6baed6', label: '$50k' },
      { color: '#2171b5', label: '$75k' },
      { color: '#08306b', label: '$125k+' },
    ]},
    'inter-canopy-width': {
      kind: 'bivariate',
      xLabel: 'canopy', xLo: '<10%', xHi: '≥10%',
      yLabel: 'width',  yLo: '<35ft', yHi: '≥35ft',
      cells: ['#fc8d59', '#1a9850', '#d9d9d9', '#91cf60'],
    },
    'inter-grade-speed': {
      kind: 'bivariate',
      xLabel: 'speed', xLo: '<35',  xHi: '≥35',
      yLabel: 'grade', yLo: 'flat', yHi: 'steep',
      cells: ['#fee08b', '#d73027', '#d9d9d9', '#fc8d59'],
    },
  };

  function renderLegend(container: HTMLElement, layerId: string | null) {
    if (!layerId || !LEGENDS[layerId]) {
      container.innerHTML = '';
      container.classList.remove('visible');
      return;
    }
    const legend = LEGENDS[layerId];
    let body = '';
    if (legend.kind === 'steps') {
      body = `
        <div class="legend-steps">
          ${legend.stops.map(s => `<div style="background:${s.color}"></div>`).join('')}
        </div>
        <div class="legend-labels">
          ${legend.stops.map(s => `<span>${s.label}</span>`).join('')}
        </div>`;
    } else {
      const [tl, tr, bl, br] = legend.cells;
      body = `
        <div class="biv-legend">
          <span class="biv-y-hi">${legend.yHi}</span>
          <div class="biv-row">
            <div style="background:${tl}"></div><div style="background:${tr}"></div>
          </div>
          <span class="biv-y-lo">${legend.yLo}</span>
          <div class="biv-row">
            <div style="background:${bl}"></div><div style="background:${br}"></div>
          </div>
          <span class="biv-y-axis">${legend.yLabel}</span>
          <div class="biv-x-axis">
            <span>${legend.xLo}</span>
            <span class="biv-x-name">${legend.xLabel}</span>
            <span>${legend.xHi}</span>
          </div>
        </div>`;
    }
    const extras = layerId === 'grade' ? `
      <label class="outlier-check">
        <input type="checkbox" id="toggle-grade-outliers">
        <span>Highlight outliers &gt;15%</span>
      </label>` : '';
    container.innerHTML = body + extras;
    container.classList.add('visible');
  }

  type LayerGroup = { toggleId: string; layerId: string; legendId: string }[];

  function setupGroup(group: LayerGroup, onDeactivate?: Partial<Record<string, () => void>>) {
    const setVisible = (layerId: string, visible: boolean) =>
      map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');

    group.forEach(({ toggleId, layerId, legendId }) => {
      const el = document.getElementById(toggleId) as HTMLInputElement | null;
      const legendEl = document.getElementById(legendId)!;
      if (el && !el.checked) {
        setVisible(layerId, false);
      } else if (el?.checked) {
        renderLegend(legendEl, layerId);
      }
    });

    group.forEach(({ toggleId, layerId, legendId }) => {
      const legendEl = document.getElementById(legendId)!;
      document.getElementById(toggleId)?.addEventListener('change', (e) => {
        const checked = (e.target as HTMLInputElement).checked;
        if (checked) {
          group.forEach(item => {
            if (item.toggleId !== toggleId) {
              setVisible(item.layerId, false);
              onDeactivate?.[item.layerId]?.();
              const other = document.getElementById(item.toggleId) as HTMLInputElement | null;
              if (other) other.checked = false;
              renderLegend(document.getElementById(item.legendId)!, null);
            }
          });
          setVisible(layerId, true);
          renderLegend(legendEl, layerId);
        } else {
          setVisible(layerId, false);
          onDeactivate?.[layerId]?.();
          renderLegend(legendEl, null);
        }
      });
    });
  }

  const clearGradeOutliers = () => {
    map.setLayoutProperty('grade-outliers', 'visibility', 'none');
    map.setLayoutProperty('grade-outlier-markers', 'visibility', 'none');
    map.setFilter('grade-outliers',        ['>', ['get', 'grade_range_smooth'], 0.15]);
    map.setFilter('grade-outlier-markers', ['>', ['get', 'grade_range_smooth'], 0.15]);
  };

  setupGroup(
    [
      { toggleId: 'toggle-crashes', layerId: 'segments-line', legendId: 'legend-crashes' },
      { toggleId: 'toggle-canopy',  layerId: 'canopy-pct',    legendId: 'legend-canopy' },
      { toggleId: 'toggle-grade',   layerId: 'grade',         legendId: 'legend-grade' },
    ],
    { 'grade': clearGradeOutliers },
  );

  document.getElementById('legend-grade')!.addEventListener('change', (e) => {
    const target = e.target as HTMLInputElement;
    if (target.id === 'toggle-grade-outliers') {
      const v = target.checked ? 'visible' : 'none';
      map.setLayoutProperty('grade-outliers', 'visibility', v);
      map.setLayoutProperty('grade-outlier-markers', 'visibility', v);
    }
  });

  setupGroup(
    [
      { toggleId: 'toggle-canopy-width', layerId: 'inter-canopy-width', legendId: 'legend-canopy-width' },
      { toggleId: 'toggle-grade-speed',  layerId: 'inter-grade-speed',  legendId: 'legend-grade-speed' },
    ],
  );

  setupGroup(
    [
      { toggleId: 'toggle-population', layerId: 'population',    legendId: 'legend-population' },
      { toggleId: 'toggle-income',     layerId: 'median-income', legendId: 'legend-income' },
    ],
  );

  // ── Sidebar state ────────────────────────────────────────────────────────

  let activeChipId: string | null = null;

  function setSidebarMode(mode: 'idle' | 'pinned' | 'story', payload?: any) {
    const sidebar = document.getElementById('sidebar')!;
    const hasChip = mode === 'story' ? true : !!activeChipId;
    sidebar.className = `mode-${mode}${hasChip ? ' has-active-chip' : ''}`;
    if (mode === 'story' && payload) {
      activeChipId = payload.id;
      sidebar.className = 'mode-story has-active-chip';
      renderStoryContent(payload);
    }
  }

  function unpin() {
    if (pinnedSegId !== null) {
      map.setFeatureState({ source: 'segments', id: pinnedSegId }, { pinned: false });
      pinnedSegId = null;
    }
    if (activeChipId) {
      setSidebarMode('story', CHIPS.find(c => c.id === activeChipId));
    } else {
      setSidebarMode('idle');
    }
  }

  document.getElementById('sidebar-back-story')!.addEventListener('click', unpin);

  document.getElementById('sidebar-back-idle')!.addEventListener('click', () => {
    activeChipId = null;
    document.querySelectorAll('.chip').forEach(el => el.classList.remove('active'));
    setSidebarMode('idle');
  });

  window.addEventListener('keydown', (e) => { if (e.key === 'Escape') unpin(); });

  map.on('click', (e) => {
    const hit = map.queryRenderedFeatures(e.point, { layers: ['segments-hit'] });
    if (!hit.length && pinnedSegId !== null) unpin();
  });

  map.on('click', 'segments-hit', (e) => {
    if (!e.features?.length) return;
    const id = e.features[0].id as number | string;
    const props = e.features[0].properties as any;
    if (pinnedSegId !== null && pinnedSegId !== id) {
      map.setFeatureState({ source: 'segments', id: pinnedSegId }, { pinned: false });
    }
    pinnedSegId = id;
    map.setFeatureState({ source: 'segments', id }, { pinned: true });
    setSidebarMode('pinned');
    renderPinnedStats(props);
    runPeerQuery(props);
  });

  // ── Pinned inspector ─────────────────────────────────────────────────────

  function renderPinnedStats(p: any) {
    const content = document.getElementById('pinned-content')!;
    const streetName = [p.st_name, p.st_type].filter(Boolean).join(' ') || 'Unknown segment';
    const fmt = (v: any, suffix: string, dec = 0) =>
      v != null && !isNaN(+v) ? `${(+v).toFixed(dec)}${suffix}` : '—';

    const delta = (p.cartway_width_ft != null && p.state_total_width_ft != null)
      ? +p.cartway_width_ft - +p.state_total_width_ft : null;
    const deltaStr = delta != null
      ? `${delta >= 0 ? '+' : ''}${delta.toFixed(1)} ft vs state` : null;
    const deltaCls = delta != null && Math.abs(delta) > 3 ? (delta > 0 ? ' warn' : ' good') : '';

    const rows: [string, string, string][] = [
      ['Crashes',       fmt(p.crash_count, ''),                       ''],
      ['Canopy',        fmt(p.canopy_pct != null ? p.canopy_pct * 100 : null, '%'),         ''],
      ['Grade',         fmt(p.grade_range_smooth != null ? p.grade_range_smooth * 100 : null, '%', 1), ''],
      ['Speed',         fmt(p.maxspeed_final, ' mph'),                ''],
      ['Width (calc.)', fmt(p.cartway_width_ft, ' ft'),               ''],
    ];
    if (deltaStr) rows.push(['Width (state)',
      `${fmt(p.state_total_width_ft, ' ft')} <small style="color:#666">${deltaStr}</small>`, deltaCls]);
    if (p.state_lane_cnt != null) rows.push(['State lanes', String(p.state_lane_cnt), '']);
    if (p.state_divisor_type && p.state_divisor_type !== 'null')
      rows.push(['Divider', p.state_divisor_type, '']);

    content.innerHTML = `
      <div class="pinned-street">
        <div class="pinned-street-name">${streetName}</div>
      </div>
      ${rows.map(([label, val, cls]) =>
        `<div class="stat-row${cls}"><span>${label}</span><strong>${val}</strong></div>`
      ).join('')}
      <div class="peer-comparison" id="peer-comparison">
        <h4>Loading block-group context…</h4>
      </div>`;
  }

  async function runPeerQuery(p: any) {
    const peerEl = document.getElementById('peer-comparison');
    if (!peerEl) return;

    const geoid: string | null = p.GEOID && p.GEOID !== 'null' ? String(p.GEOID) : null;
    if (!geoid) { peerEl.innerHTML = '<h4>No block group data for this segment.</h4>'; return; }

    const sql =
`SELECT
  COUNT(*) AS peer_n,
  MEDIAN(crash_count) AS bg_median_crash,
  MEDIAN(canopy_pct)  AS bg_median_canopy,
  SUM(CASE WHEN crash_count <= ${p.crash_count} THEN 1 ELSE 0 END) * 1.0
    / COUNT(*) AS crash_pctile
FROM segments
WHERE GEOID = '${geoid}'`;

    try {
      const result = await query(sql);
      const row = result.toArray()[0] as any;
      const n        = Number(row.peer_n);
      const pctile   = row.crash_pctile != null ? Math.round(+row.crash_pctile * 100) : null;
      const medCrash = row.bg_median_crash != null ? (+row.bg_median_crash).toFixed(0) : '—';
      const medCanopy = row.bg_median_canopy != null
        ? `${(+row.bg_median_canopy * 100).toFixed(0)}%` : '—';

      peerEl.innerHTML = `
        <h4>Block group (${n} segments)</h4>
        <div class="stat-row">
          <span>Crashes — block-group median</span>
          <strong>${medCrash}${pctile != null ? ` <small style="color:#666">(this: ${pctile}th pctile)</small>` : ''}</strong>
        </div>
        <div class="stat-row">
          <span>Canopy — block-group median</span>
          <strong>${medCanopy}</strong>
        </div>
        <details class="sql-details">
          <summary>View DuckDB query</summary>
          <pre>${sql}</pre>
        </details>`;
    } catch (err) {
      peerEl.innerHTML = '<h4>Query failed.</h4>';
      console.error(err);
    }
  }

  // ── Story chips ──────────────────────────────────────────────────────────

  type StoryChip = {
    id: string;
    title: string;
    hook: string;
    toggleIds: string[];
    camera: maplibregl.FlyToOptions;
    stat: string;
    writeup: string;
    extras?: 'grade-outlier-slider';
  };

  const CHIPS: StoryChip[] = [
    {
      id: 'canopy-width',
      title: 'Canopy on Narrow Streets',
      hook: 'Tree cover reduces crashes — but mostly on narrow residential roads.',
      toggleIds: ['toggle-canopy-width'],
      camera: { center: [-75.198, 39.957], zoom: 14.5 },
      stat: 'Narrow residential streets with moderate canopy show ~15–25% fewer crashes than equivalent streets with no canopy.',
      writeup: 'Wide arterial roads are built for speed, and nothing about tree cover changes that calculus. But on the narrow residential streets where most of Philadelphia\'s pedestrian life happens, canopy coverage is a meaningful predictor of safety. Streets that are wide <em>and</em> treeless — the orange segments — show the highest crash concentrations.',
    },
    {
      id: 'grade-speed',
      title: 'Grade × Speed Paradox',
      hook: 'Steep hills mean fewer crashes — until they don\'t.',
      toggleIds: ['toggle-grade-speed'],
      camera: { center: [-75.221, 40.025], zoom: 14, pitch: 30, bearing: -20 },
      stat: 'On 25 mph streets, 10% grade is associated with ~65% fewer crashes. On 45+ mph arterials, the relationship reverses — grade becomes a hazard.',
      writeup: 'On slow residential streets, hills are self-calming: drivers naturally brake on steep grades. But on faster arterials, grade amplifies risk. Stopping distances increase, reaction time is compressed, and the consequences of a mistake are more severe. The same slope that makes a Manayunk side street relatively safe makes a fast connector road more dangerous.',
    },
    {
      id: 'method-check',
      title: 'Where My Method Probably Failed',
      hook: 'The grade calculation breaks on bridges, ramps, and very short segments.',
      toggleIds: ['toggle-grade'],
      camera: { center: [-75.178, 40.008], zoom: 13.5 },
      stat: 'Some segments show grades above 15% — physically implausible for a drivable city road. Most are measurement artifacts.',
      writeup: 'I calculated grade from LiDAR elevation data, smoothed with a 20m rolling average. That smoothing helps on real hills but fails on infrastructure transitions: bridges create abrupt elevation spikes, ramps join roads at grade mid-span, and very short segments don\'t have enough length for the smoothing to behave. Use the slider to explore the threshold and see where the calculation goes wrong.',
      extras: 'grade-outlier-slider',
    },
  ];

  function activateChip(chip: StoryChip) {
    document.querySelectorAll<HTMLInputElement>('#layer-panel input[type=checkbox]').forEach(input => {
      const should = chip.toggleIds.includes(input.id);
      if (input.checked !== should) {
        input.checked = should;
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
    map.flyTo({ ...chip.camera, essential: true });
    setSidebarMode('story', chip);
    document.querySelectorAll('.chip').forEach(el =>
      el.classList.toggle('active', el.getAttribute('data-chip-id') === chip.id));
  }

  function renderStoryContent(chip: StoryChip) {
    const el = document.getElementById('story-content')!;
    const sliderHtml = chip.extras === 'grade-outlier-slider' ? `
      <div class="outlier-slider-wrap">
        <div class="outlier-slider-label">
          <span>Outlier threshold</span>
          <strong id="slider-val">15%</strong>
        </div>
        <input type="range" class="outlier-slider" id="outlier-threshold-slider"
               min="5" max="30" value="15" step="1">
        <div class="outlier-count" id="outlier-count">Counting…</div>
      </div>` : '';
    el.innerHTML = `
      <div class="story-label">Finding</div>
      <div class="story-title">${chip.title}</div>
      <div class="story-stat">${chip.stat}</div>
      <div class="story-writeup">${chip.writeup}</div>
      ${sliderHtml}`;

    if (chip.extras === 'grade-outlier-slider') {
      const checkbox = document.getElementById('toggle-grade-outliers') as HTMLInputElement | null;
      if (checkbox && !checkbox.checked) {
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
      }
      setupOutlierSlider();
    }
  }

  function setupOutlierSlider() {
    const slider = document.getElementById('outlier-threshold-slider') as HTMLInputElement | null;
    const valLabel = document.getElementById('slider-val') as HTMLElement;
    const countEl  = document.getElementById('outlier-count') as HTMLElement;
    if (!slider || !valLabel || !countEl) return;

    let timer: ReturnType<typeof setTimeout>;
    async function apply(threshold: number) {
      valLabel.textContent = `${threshold}%`;
      const t = threshold / 100;
      map.setFilter('grade-outliers',        ['>', ['get', 'grade_range_smooth'], t]);
      map.setFilter('grade-outlier-markers', ['>', ['get', 'grade_range_smooth'], t]);
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const res = await query(`SELECT COUNT(*) AS n FROM segments WHERE grade_range_smooth > ${t}`);
          const n = Number((res.toArray()[0] as any).n);
          countEl.textContent = `${n.toLocaleString()} segments flagged at ≥${threshold}% grade`;
        } catch { countEl.textContent = ''; }
      }, 150);
    }
    slider.addEventListener('input', () => apply(Number(slider.value)));
    apply(15);
  }

  function renderChipList() {
    const listEl = document.getElementById('chip-list')!;
    listEl.innerHTML = CHIPS.map(c => `
      <button class="chip" data-chip-id="${c.id}">
        <div class="chip-title">${c.title}</div>
        <div class="chip-hook">${c.hook}</div>
      </button>`).join('');
    listEl.querySelectorAll<HTMLButtonElement>('.chip').forEach(btn => {
      btn.addEventListener('click', () => {
        activateChip(CHIPS.find(c => c.id === btn.dataset.chipId)!);
      });
    });
  }

  renderChipList();

  return map;
}