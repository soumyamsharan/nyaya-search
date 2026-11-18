/**
 * A small in-memory cache for read-only API responses. It lives for the browser session, so going Back to a
 * page you already loaded is instant. Only successful responses are kept; failures are retried on the next call.
 */

const MAX_ENTRIES = 200;
const store = new Map<string, { value: Promise<unknown>; expires: number }>();

export const MINUTE = 60_000;
export const HOUR = 60 * MINUTE;

export function cached<T>(key: string, ttlMs: number, load: () => Promise<T>): Promise<T> {
  const now = Date.now();
  const hit = store.get(key);
  if (hit && hit.expires > now) return hit.value as Promise<T>;

  const value = load().catch((error: unknown) => {
    store.delete(key);
    throw error;
  });
  store.delete(key); // re-insert at the end so the oldest entry is evicted first
  store.set(key, { value, expires: now + ttlMs });
  if (store.size > MAX_ENTRIES) store.delete(store.keys().next().value as string);
  return value;
}

/** Start loading something the user is likely to open next. Errors are ignored; the page loads it again. */
export function prefetch(key: string, ttlMs: number, load: () => Promise<unknown>): void {
  cached(key, ttlMs, load).catch(() => undefined);
}
