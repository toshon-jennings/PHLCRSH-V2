import { query } from './db';

export type SegmentProperties = {
  seg_id: number;
  crash_count: number | null;
  cartway_width_ft: number | null;
  canopy_pct: number | null;
  grade_range_smooth: number | null;
  maxspeed_final: number | null;
  state_total_width_ft: number | null;
  state_lane_cnt: number | null;
  GEOID: string | null;
  st_name: string | null;
  st_type: string | null;
  road_class: string | null;
  state_divisor_type: string | null;
};

export type SegmentFeature = {
  type: 'Feature';
  properties: SegmentProperties;
  geometry: any;
};

export type BlockGroupFeature = {
  type: 'Feature';
  properties: {
    GEOID: string | null;
    population: number | null;
    median_income: number | null;
  };
  geometry: any;
};

export type BoundaryFeatureCollection = {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    properties: Record<string, unknown>;
    geometry: any;
  }>;
};

export type PeerComparison = {
  sql: string;
  peerN: number;
  bgMedianCrash: number | null;
  bgMedianCanopy: number | null;
  crashPctile: number | null;
};

export async function loadSegmentFeatures(): Promise<SegmentFeature[]> {
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

  return result.toArray().map((r: any) => ({
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
}

export async function loadBlockGroupFeatures(): Promise<BlockGroupFeature[]> {
  const result = await query(`
    SELECT
      GEOID,
      CAST(population AS INTEGER) AS population,
      CASE WHEN median_income < 0 THEN NULL ELSE CAST(median_income AS INTEGER) END AS median_income,
      ST_AsGeoJSON(geometry) AS geojson
    FROM block_groups
  `);

  return result.toArray().map((r: any) => ({
    type: 'Feature' as const,
    properties: {
      GEOID: r.GEOID,
      population: r.population,
      median_income: r.median_income,
    },
    geometry: JSON.parse(r.geojson),
  }));
}

export async function loadPhiladelphiaBoundary(): Promise<BoundaryFeatureCollection> {
  const result = await query(`
    SELECT ST_AsGeoJSON(ST_Boundary(ST_CoverageUnion_Agg(geometry))) AS geojson
    FROM block_groups
  `);
  const row = result.toArray()[0] as any;

  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { name: 'Philadelphia' },
        geometry: JSON.parse(row.geojson),
      },
    ],
  };
}

export async function loadBlockGroupPeerComparison(p: SegmentProperties): Promise<PeerComparison | null> {
  const geoid = p.GEOID && p.GEOID !== 'null' ? String(p.GEOID) : null;
  if (!geoid) return null;

  const safeGeoid = geoid.replace(/'/g, "''");
  const crashCount = p.crash_count == null ? 'NULL' : String(Number(p.crash_count));
  const sql =
`SELECT
  COUNT(*) AS peer_n,
  MEDIAN(crash_count) AS bg_median_crash,
  MEDIAN(canopy_pct)  AS bg_median_canopy,
  SUM(CASE WHEN crash_count <= ${crashCount} THEN 1 ELSE 0 END) * 1.0
    / COUNT(*) AS crash_pctile
FROM segments
WHERE GEOID = '${safeGeoid}'`;

  const result = await query(sql);
  const row = result.toArray()[0] as any;

  return {
    sql,
    peerN: Number(row.peer_n),
    bgMedianCrash: row.bg_median_crash != null ? Number(row.bg_median_crash) : null,
    bgMedianCanopy: row.bg_median_canopy != null ? Number(row.bg_median_canopy) : null,
    crashPctile: row.crash_pctile != null ? Number(row.crash_pctile) : null,
  };
}

export async function countGradeOutliers(threshold: number): Promise<number> {
  const result = await query(`SELECT COUNT(*) AS n FROM segments WHERE grade_range_smooth > ${threshold}`);
  return Number((result.toArray()[0] as any).n);
}
