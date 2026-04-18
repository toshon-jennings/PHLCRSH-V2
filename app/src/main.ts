import { initDB } from './db';
import { ensureDatasets } from './opfs';
import { initMap, addTableLayer } from './map';

const DATASETS = [
  {
    table: 'crashes',
    url: '/data/crashes.parquet',
  },
  // Add more datasets here as the pipeline produces them:
  // { table: 'segments', url: '/data/segments.parquet', geometryColumn: 'geometry' },
];

async function main() {
  const statusEl = document.getElementById('status')!;

  statusEl.textContent = 'Initializing DuckDB…';
  await initDB();
  statusEl.textContent = 'DuckDB ready. Loading datasets…';

  await ensureDatasets(DATASETS);
  statusEl.textContent = 'Data loaded. Rendering map…';

  const map = initMap('map');

  map.on('load', async () => {
    await addTableLayer(map, 'crashes', 'crashes-layer', undefined, 'circle');
    statusEl.textContent = 'Ready.';
  });
}

main().catch((err) => {
  console.error(err);
  const statusEl = document.getElementById('status');
  if (statusEl) statusEl.textContent = `Error: ${err.message}`;
});
