import * as duckdb from '@duckdb/duckdb-wasm';
import duckdb_wasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvp_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import duckdb_wasm_eh from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import eh_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

const PARQUET_URL = "https://pub-3569c09037ec4a099ca0c7b5324372f6.r2.dev/data/philly_segments.parquet";
const BG_PARQUET_URL = "https://pub-3569c09037ec4a099ca0c7b5324372f6.r2.dev/data/philly_block_groups.parquet";
const FILE_NAME = 'philly_segments.parquet';
const BG_FILE_NAME = 'philly_block_groups.parquet';
const BUNDLES: duckdb.DuckDBBundles = {
  mvp: { mainModule: duckdb_wasm, mainWorker: mvp_worker },
  eh: { mainModule: duckdb_wasm_eh, mainWorker: eh_worker },
};

let _db: duckdb.AsyncDuckDB | null = null;
let _parquetRegistered: boolean = false

export async function initDB(): Promise<duckdb.AsyncDuckDB> {
  if (_db) return _db;

  const bundle = await duckdb.selectBundle(BUNDLES);
  const worker = new Worker(bundle.mainWorker!);
  const logger = new duckdb.ConsoleLogger();
  const db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

  // OPFS requires the path to end in .db; Chrome/Edge only — others fall back to in-memory
  try {
      // await db.open({ path: ':memory:' })
    await db.open({
      path: 'opfs://phlcrsh.db',
      accessMode: duckdb.DuckDBAccessMode.READ_WRITE,
    });
   
    console.log('[db] opened with OPFS backing');
  } catch (e) {
    console.warn('[db] OPFS unavailable, falling back to in-memory:', e);
    await db.open({ path: ':memory:' });
  }

  const conn = await db.connect();
  const [segHandle, bgHandle] = await Promise.all([getOrFetch(FILE_NAME, PARQUET_URL), getOrFetch(BG_FILE_NAME, BG_PARQUET_URL)]);

  await db.registerFileHandle(FILE_NAME, segHandle, duckdb.DuckDBDataProtocol.BROWSER_FSACCESS, true);
  await db.registerFileHandle(BG_FILE_NAME, bgHandle, duckdb.DuckDBDataProtocol.BROWSER_FSACCESS, true);

  await conn.query('INSTALL spatial; LOAD spatial;');
  await conn.query(`CREATE OR REPLACE VIEW segments AS SELECT * FROM read_parquet('${PARQUET_URL}')`);
  await conn.query(`CREATE OR REPLACE VIEW block_groups AS SELECT * FROM read_parquet('${BG_PARQUET_URL}')`);
  await conn.close();
  
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

async function getOrFetch(fileName: string, url: string): Promise<FileSystemFileHandle> {
  const root = await navigator.storage.getDirectory();
  try {
    return await root.getFileHandle(fileName);
  } catch {
    const handle = await root.getFileHandle(fileName, { create: true });
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    const writable = await handle.createWritable();
    await res.body!.pipeTo(writable);
    return handle;
  }
}