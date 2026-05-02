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
    CAST(seg_id AS INTEGER)      AS seg_id,
    CAST(crash_count AS INTEGER) AS crash_count,
    CAST(cartway_width_ft AS FLOAT) AS  cartway_width_ft,
    CAST(canopy_pct AS FLOAT) AS              canopy_pct,
    CAST(grade_range_smooth AS FLOAT) AS      grade_range_smooth,
    CAST(maxspeed_final AS FLOAT) AS          maxspeed_final,
    ST_AsGeoJSON(geometry)       AS geojson
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
        'case', ['==', ['get', 'median_income'], null], '#e8e8e8',
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

  // Invisible wide layer on top for reliable hit detection
  map.addLayer({
    id: 'segments-hit',
    type: 'line',
    source: 'segments',
    paint: { 'line-color': 'transparent', 'line-width': 10, 'line-opacity': 0 },
  });

  let hoveredId: number | string | null = null;
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });

  map.on('mousemove', 'segments-hit', (e) => {
    if (!e.features?.length) return;
    map.getCanvas().style.cursor = 'crosshair';

    const id = e.features[0].id as number | string;
    if (hoveredId !== null && hoveredId !== id) {
      map.setFeatureState({ source: 'segments', id: hoveredId }, { hover: false });
    }
    hoveredId = id;
    map.setFeatureState({ source: 'segments', id }, { hover: true });

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

  return map;
}