import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { query } from './db';

export function initMap(container: string | HTMLElement): maplibregl.Map {
  const map = new maplibregl.Map({
    container,
    style: {
      version: 8,
      sources: {
        'osm-tiles': {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors',
        },
      },
      layers: [{ id: 'osm', type: 'raster', source: 'osm-tiles' }],
    },
    center: [-75.1652, 39.9526], // Philadelphia
    zoom: 12,
  });

  map.addControl(new maplibregl.NavigationControl());
  return map;
}

/**
 * Query a table for GeoJSON and add it as a MapLibre layer.
 * The geometry column must already be a spatial type (loaded via ST_GeomFromWKB).
 */
export async function addTableLayer(
  map: maplibregl.Map,
  table: string,
  layerId: string,
  paint?: maplibregl.LinePaint | maplibregl.CirclePaint | maplibregl.FillPaint,
  type: 'line' | 'circle' | 'fill' = 'circle'
): Promise<void> {
  const result = await query(
    `SELECT ST_AsGeoJSON(geometry) AS geojson FROM "${table}" LIMIT 50000`
  );

  const features = result.toArray().map((row: any) => JSON.parse(row.geojson));
  const geojson: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: features.map((geom: GeoJSON.Geometry) => ({
      type: 'Feature',
      geometry: geom,
      properties: {},
    })),
  };

  if (map.getSource(layerId)) {
    (map.getSource(layerId) as maplibregl.GeoJSONSource).setData(geojson);
    return;
  }

  map.addSource(layerId, { type: 'geojson', data: geojson });
  map.addLayer({
    id: layerId,
    type,
    source: layerId,
    paint: (paint as any) ?? defaultPaint(type),
  });
}

function defaultPaint(type: string): object {
  if (type === 'circle') return { 'circle-radius': 4, 'circle-color': '#e74c3c', 'circle-opacity': 0.7 };
  if (type === 'line') return { 'line-color': '#3498db', 'line-width': 1.5 };
  return { 'fill-color': '#2ecc71', 'fill-opacity': 0.4 };
}
