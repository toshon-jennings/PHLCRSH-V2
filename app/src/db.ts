import * as duckdb from '@duckdb/duckdb-wasm';
import duckdb_wasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvp_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import duckdb_wasm_eh from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import eh_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

const PARQUET_URL = "/PHLCRSH-V2/data/philly_segments.parquet";
const BG_PARQUET_URL = "/PHLCRSH-V2/data/philly_block_groups.parquet";
const FILE_NAME = 'philly_segments.parquet';
const BG_FILE_NAME = 'philly_block_groups.parquet';
const BUNDLES: duckdb.DuckDBBundles = {
  mvp: { mainModule: duckdb_wasm, mainWorker: mvp_worker },
  eh: { mainModule: duckdb_wasm_eh, mainWorker: eh_worker },
};

let _db: duckdb.AsyncDuckDB | null = null;

type StorageMode = 'chromium-opfs' | 'memory';

export async function initDB(): Promise<duckdb.AsyncDuckDB> {
  if (_db) return _db;

  const DB_VERSION = 'v2_combinations';
  const versionKey = 'db_version';
  const currentVersion = localStorage.getItem(versionKey);
  if (currentVersion !== DB_VERSION) {
    if (supportsChromiumOPFS()) {
      try {
        const root = await navigator.storage.getDirectory();
        await root.removeEntry(FILE_NAME).catch(() => null);
        await root.removeEntry(BG_FILE_NAME).catch(() => null);
        localStorage.removeItem(`etag:${FILE_NAME}`);
        localStorage.removeItem(`etag:${BG_FILE_NAME}`);
        console.log('[db] Old OPFS cache cleared for version:', DB_VERSION);
      } catch (e) {
        console.warn('Failed to clear old OPFS files:', e);
      }
    }
    localStorage.setItem(versionKey, DB_VERSION);
  }

  const bundle = await duckdb.selectBundle(BUNDLES);
  const worker = new Worker(bundle.mainWorker!);
  const logger = new duckdb.ConsoleLogger();
  const db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

  let storageMode: StorageMode = 'memory';
  if (supportsChromiumOPFS()) {
    storageMode = 'chromium-opfs';
  }
  await db.open({ path: ':memory:' });
  console.log('[db] opened with in-memory backing. OPFS cache mode:', storageMode);

  await registerParquetFiles(db, storageMode);

  const conn = await db.connect();
  try {
    await conn.query('INSTALL spatial; LOAD spatial;');
    await conn.query(`CREATE OR REPLACE VIEW segments AS SELECT * FROM read_parquet('${FILE_NAME}')`);
    await conn.query(`CREATE OR REPLACE VIEW block_groups AS SELECT * FROM read_parquet('${BG_FILE_NAME}')`);
  } finally {
    await conn.close();
  }
  
  _db = db;
  return db;
}

export async function query(sql: string, db?: duckdb.AsyncDuckDB) {
  const instance = db ?? (await initDB());
  const conn = await instance.connect();
  try {
    return await conn.query(sql);
  } finally {
    await conn.close();
  }
}

async function registerParquetFiles(db: duckdb.AsyncDuckDB, storageMode: StorageMode) {
  if (storageMode === 'chromium-opfs') {
    try {
      const [segHandle, bgHandle] = await Promise.all([
        getOrFetchHandle(FILE_NAME, PARQUET_URL),
        getOrFetchHandle(BG_FILE_NAME, BG_PARQUET_URL),
      ]);
      await db.registerFileHandle(FILE_NAME, segHandle, duckdb.DuckDBDataProtocol.BROWSER_FSACCESS, true);
      await db.registerFileHandle(BG_FILE_NAME, bgHandle, duckdb.DuckDBDataProtocol.BROWSER_FSACCESS, true);
      console.log('[db] parquet files registered from OPFS handles');
      return;
    } catch (e) {
      console.warn('[db] OPFS parquet registration failed, using in-memory parquet buffers:', e);
      await db.dropFiles([FILE_NAME, BG_FILE_NAME]).catch(() => null);
    }
  }

  const [segmentBytes, blockGroupBytes] = await Promise.all([
    fetchParquetBytes(PARQUET_URL),
    fetchParquetBytes(BG_PARQUET_URL),
  ]);
  await db.registerFileBuffer(FILE_NAME, segmentBytes);
  await db.registerFileBuffer(BG_FILE_NAME, blockGroupBytes);
  console.log('[db] parquet files registered from fetched buffers');
}

async function fetchParquetBytes(url: string): Promise<Uint8Array> {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  return new Uint8Array(await res.arrayBuffer());
}

function supportsChromiumOPFS(): boolean {
  if (!window.isSecureContext || !navigator.storage?.getDirectory) return false;

  const nav = navigator as Navigator & {
    userAgentData?: { brands?: Array<{ brand: string }> };
  };
  const brands = nav.userAgentData?.brands?.map((brand) => brand.brand).join(' ') || '';
  if (/\b(Chromium|Google Chrome|Microsoft Edge|Opera)\b/.test(brands)) return true;

  if (/\b(Firefox|FxiOS)\//.test(navigator.userAgent)) return false;
  return /\b(Chrome|Chromium|Edg|OPR)\//.test(navigator.userAgent);
}

async function getOrFetchHandle(fileName: string, url: string): Promise<FileSystemFileHandle> {
  const root = await navigator.storage.getDirectory();
  const etagKey = `etag:${fileName}`;

  let remoteEtag: string | null = null;
  try {
    const headRes = await fetch(url, { method: 'HEAD', cache: 'no-cache' });
    remoteEtag = headRes.ok ? headRes.headers.get('ETag') : null;
  } catch (e) {
    console.warn(`[db] could not read parquet ETag for ${fileName}; refreshing cache`, e);
  }
  const storedEtag = localStorage.getItem(etagKey);

  let handle: FileSystemFileHandle;
  let needsFetch = true;

  try {
    handle = await root.getFileHandle(fileName);
    needsFetch = !remoteEtag || remoteEtag !== storedEtag;
  } catch {
    handle = await root.getFileHandle(fileName, { create: true });
    needsFetch = true;
  }

  if (needsFetch) {
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    const writable = await handle.createWritable();
    if (res.body) {
      await res.body.pipeTo(writable);
    } else {
      await writable.write(await res.arrayBuffer());
      await writable.close();
    }
    if (remoteEtag) localStorage.setItem(etagKey, remoteEtag);
  }

  return handle;
}
