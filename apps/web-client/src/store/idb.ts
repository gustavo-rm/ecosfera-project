/** Tiny IndexedDB key-value wrapper for local state (PWA, RNF-021). No synchronization: see ADR 0006. */
const DB = "ecosfera", STORE = "kv";
function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(STORE);
    r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error);
  });
}
export async function idbGet<T>(key: string): Promise<T | undefined> {
  try { const db = await open(); return await new Promise((res, rej) => { const r = db.transaction(STORE).objectStore(STORE).get(key); r.onsuccess = () => res(r.result as T); r.onerror = () => rej(r.error); }); } catch { return undefined; }
}
export async function idbSet(key: string, value: unknown): Promise<void> {
  try { const db = await open(); await new Promise<void>((res, rej) => { const tx = db.transaction(STORE, "readwrite"); tx.objectStore(STORE).put(value, key); tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error); }); } catch { /* offline storage is best effort */ }
}
