import * as duckdb from '@duckdb/duckdb-wasm';
import duckdb_wasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvp_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import duckdb_wasm_eh from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import eh_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

const BUNDLES: duckdb.DuckDBBundles = {
  mvp: { mainModule: duckdb_wasm, mainWorker: mvp_worker },
  eh: { mainModule: duckdb_wasm_eh, mainWorker: eh_worker },
};

let _db: duckdb.AsyncDuckDB | null = null;

export async function initDB(): Promise<duckdb.AsyncDuckDB> {
  if (_db) return _db;

  const bundle = await duckdb.selectBundle(BUNDLES);
  const worker = new Worker(bundle.mainWorker!);
  const logger = new duckdb.ConsoleLogger();
  const db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

  // OPFS requires the path to end in .db; Chrome/Edge only — others fall back to in-memory
  try {
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
  await conn.query('INSTALL spatial; LOAD spatial;');
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
