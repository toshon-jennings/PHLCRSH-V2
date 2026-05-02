import { initDB, query } from './db';
import { initMap, } from './map';

async function main() {
  const statusEl = document.getElementById('status')!;

  statusEl.textContent = 'Initializing DuckDB…';
  await initDB();
  statusEl.textContent = 'DuckDB ready. Loading datasets…';

  // await ensureDatasets(DATASETS);
  // statusEl.textContent = 'Data loaded. Rendering map…';

  initMap('map');

}

main().catch((err) => {
  console.error(err);
  const statusEl = document.getElementById('status');
  if (statusEl) statusEl.textContent = `Error: ${err.message}`;
});
