import type maplibregl from 'maplibre-gl';
import type { BlockGroupFeature, SegmentFeature } from './mapQueries';

export const GRADE_OUTLIER_THRESHOLD = 0.15;

export type LegendStop = { color: string; label: string };
export type Legend =
  | { kind: 'steps'; stops: LegendStop[] }
  | {
      kind: 'bivariate';
      xLabel: string;
      xLo: string;
      xHi: string;
      yLabel: string;
      yLo: string;
      yHi: string;
      // cells in order: yHi+xLo, yHi+xHi, yLo+xLo, yLo+xHi (top-left, top-right, bottom-left, bottom-right)
      cells: [string, string, string, string];
    };

export type LayerGroup = { toggleId: string; layerId: string; legendId: string }[];

export const SEGMENT_LAYER_GROUP: LayerGroup = [
  { toggleId: 'toggle-crashes', layerId: 'segments-line', legendId: 'legend-crashes' },
  { toggleId: 'toggle-canopy', layerId: 'canopy-pct', legendId: 'legend-canopy' },
  { toggleId: 'toggle-grade', layerId: 'grade', legendId: 'legend-grade' },
];

export const INTERACTION_LAYER_GROUP: LayerGroup = [
  { toggleId: 'toggle-canopy-width', layerId: 'inter-canopy-width', legendId: 'legend-canopy-width' },
  { toggleId: 'toggle-grade-speed', layerId: 'inter-grade-speed', legendId: 'legend-grade-speed' },
];

export const BLOCK_GROUP_LAYER_GROUP: LayerGroup = [
  { toggleId: 'toggle-population', layerId: 'population', legendId: 'legend-population' },
  { toggleId: 'toggle-income', layerId: 'median-income', legendId: 'legend-income' },
];

export const LEGENDS: Record<string, Legend> = {
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
    xLabel: 'canopy',
    xLo: '<10%',
    xHi: '≥10%',
    yLabel: 'width',
    yLo: '<35ft',
    yHi: '≥35ft',
    cells: ['#fc8d59', '#1a9850', '#d9d9d9', '#91cf60'],
  },
  'inter-grade-speed': {
    kind: 'bivariate',
    xLabel: 'speed',
    xLo: '<35',
    xHi: '≥35',
    yLabel: 'grade',
    yLo: 'flat',
    yHi: 'steep',
    cells: ['#fee08b', '#d73027', '#d9d9d9', '#fc8d59'],
  },
};

export function addMapSourcesAndLayers(
  map: maplibregl.Map,
  segmentFeatures: SegmentFeature[],
  blockGroupFeatures: BlockGroupFeature[],
) {
  map.addSource('segments', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: segmentFeatures } as any,
    promoteId: 'seg_id',
  });

  map.addLayer({
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
    id: 'canopy-pct',
    type: 'line',
    source: 'segments',
    paint: {
      'line-color': [
        'step', ['get', 'canopy_pct'],
        '#fff',
        0.05, '#e5f5e0',
        0.1, '#a1d99b',
        0.5, '#31a354',
      ],
      'line-width': [
        'step', ['get', 'cartway_width_ft'],
        1,
        5, 2,
        10, 3,
        50, 5,
        100, 8,
      ],
    },
  });

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
    filter: ['>', ['get', 'grade_range_smooth'], GRADE_OUTLIER_THRESHOLD],
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
    filter: ['>', ['get', 'grade_range_smooth'], GRADE_OUTLIER_THRESHOLD],
    layout: {
      visibility: 'none',
      'symbol-placement': 'line-center',
      'icon-image': 'grade-outlier-dot',
      'icon-size': 1,
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
    },
  });

  map.addLayer({
    id: 'inter-canopy-width',
    type: 'line',
    source: 'segments',
    layout: { visibility: 'none' },
    paint: {
      'line-color': [
        'case',
        ['all', ['<', ['get', 'cartway_width_ft'], 35], ['<', ['get', 'canopy_pct'], 0.1]], '#d9d9d9',
        ['all', ['<', ['get', 'cartway_width_ft'], 35], ['>=', ['get', 'canopy_pct'], 0.1]], '#91cf60',
        ['all', ['>=', ['get', 'cartway_width_ft'], 35], ['<', ['get', 'canopy_pct'], 0.1]], '#fc8d59',
        ['all', ['>=', ['get', 'cartway_width_ft'], 35], ['>=', ['get', 'canopy_pct'], 0.1]], '#1a9850',
        '#d9d9d9',
      ],
      'line-width': [
        'step', ['get', 'cartway_width_ft'],
        1, 5, 1.5, 10, 2, 50, 4, 100, 6,
      ],
    },
  });

  map.addLayer({
    id: 'inter-grade-speed',
    type: 'line',
    source: 'segments',
    layout: { visibility: 'none' },
    paint: {
      'line-color': [
        'case',
        ['all', ['<', ['get', 'grade_range_smooth'], 0.02], ['<', ['get', 'maxspeed_final'], 35]], '#d9d9d9',
        ['all', ['>=', ['get', 'grade_range_smooth'], 0.02], ['<', ['get', 'maxspeed_final'], 35]], '#fee08b',
        ['all', ['<', ['get', 'grade_range_smooth'], 0.02], ['>=', ['get', 'maxspeed_final'], 35]], '#fc8d59',
        ['all', ['>=', ['get', 'grade_range_smooth'], 0.02], ['>=', ['get', 'maxspeed_final'], 35]], '#d73027',
        '#d9d9d9',
      ],
      'line-width': [
        'step', ['get', 'cartway_width_ft'],
        1, 5, 1.5, 10, 2, 50, 4, 100, 6,
      ],
    },
  });

  map.addSource('block-groups', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: blockGroupFeatures } as any,
  });

  map.addLayer({
    id: 'population',
    type: 'fill',
    source: 'block-groups',
    paint: {
      'fill-color': [
        'step', ['get', 'population'],
        '#fff7ec',
        500, '#fdd49e',
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
        ],
      ],
      'fill-opacity': 0.55,
    },
  });

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

  map.addLayer({
    id: 'segments-hit',
    type: 'line',
    source: 'segments',
    paint: { 'line-color': 'transparent', 'line-width': 10, 'line-opacity': 0 },
  });
}

export function setGradeOutlierVisibility(map: maplibregl.Map, visible: boolean) {
  const visibility = visible ? 'visible' : 'none';
  map.setLayoutProperty('grade-outliers', 'visibility', visibility);
  map.setLayoutProperty('grade-outlier-markers', 'visibility', visibility);
}

export function setGradeOutlierThreshold(map: maplibregl.Map, threshold: number) {
  map.setFilter('grade-outliers', ['>', ['get', 'grade_range_smooth'], threshold]);
  map.setFilter('grade-outlier-markers', ['>', ['get', 'grade_range_smooth'], threshold]);
}

export function clearGradeOutliers(map: maplibregl.Map) {
  setGradeOutlierVisibility(map, false);
  setGradeOutlierThreshold(map, GRADE_OUTLIER_THRESHOLD);
}
