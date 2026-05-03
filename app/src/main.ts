import './styles.css';
import { initAboutPage } from './aboutPage';
import { initDB } from './db';
import { initMap } from './map';

const loadingEl = document.getElementById('loading-screen');
const loadingMessageEl = document.getElementById('loading-message');

function setLoadingMessage(message: string) {
  if (loadingMessageEl) loadingMessageEl.textContent = message;
}

function finishLoading() {
  if (!loadingEl) return;
  loadingEl.classList.add('is-loaded');
  loadingEl.setAttribute('aria-hidden', 'true');
}

function showLoadingError(message: string) {
  if (!loadingEl) return;
  loadingEl.classList.add('is-error');
  loadingEl.removeAttribute('aria-hidden');
  setLoadingMessage(message);
}

async function main() {
  initAboutPage();

  setLoadingMessage('Preparing DuckDB and local data cache…');
  console.log('[phlcrsh] Initializing DuckDB…');
  await initDB();
  console.log('[phlcrsh] DuckDB ready. Loading map…');

  setLoadingMessage('Drawing Philadelphia streets and block groups…');
  await initMap('map');
  finishLoading();
}

main().catch((err) => {
  console.error(err);
  const statusEl = document.getElementById('status');
  if (statusEl) { statusEl.classList.add('error'); statusEl.textContent = `Error: ${err.message}`; }
  showLoadingError(`Could not load app data: ${err.message}`);
});
