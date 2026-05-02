import { initDB, query } from './db';
import { initMap, } from './map';

async function main() {
  const statusEl = document.getElementById('status')!;

  console.log('[phlcrsh] Initializing DuckDB…');
  await initDB();
  console.log('[phlcrsh] DuckDB ready. Loading map…');

  initMap('map');

}

main().catch((err) => {
  console.error(err);
  const statusEl = document.getElementById('status');
  if (statusEl) { statusEl.classList.add('error'); statusEl.textContent = `Error: ${err.message}`; }
});
