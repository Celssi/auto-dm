import { createContext, use, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api } from '../api/client';
import { lookupGlossary, glossaryKey, type GlossaryEntry } from '../lib/glossary';

interface GlossaryContextValue {
  ready: boolean;
  getEntry: (name: string, classId?: string) => GlossaryEntry | null;
  fetchEntry: (name: string, classId?: string) => Promise<GlossaryEntry | null>;
}

const GlossaryContext = createContext<GlossaryContextValue | null>(null);

function getCache<K, V>(ref: { current: Map<K, V> | null }): Map<K, V> {
  if (!ref.current) ref.current = new Map();
  return ref.current;
}

export function GlossaryProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<Record<string, GlossaryEntry>>({});
  const [ready, setReady] = useState(false);
  const cacheRef = useRef<Map<string, GlossaryEntry> | null>(null);
  const inflightRef = useRef<Map<string, Promise<GlossaryEntry | null>> | null>(null);

  useEffect(() => {
    api
      .getGlossary()
      .then((res) => {
        setEntries(res.entries as Record<string, GlossaryEntry>);
        setReady(true);
      })
      .catch((err: unknown) => {
        console.warn('Failed to load glossary', err);
        setReady(true);
      });
  }, []);

  const getEntry = useCallback(
    (name: string, classId?: string) => {
      const cacheKey = classId ? `${classId}:${glossaryKey(name)}` : glossaryKey(name);
      const cached = getCache(cacheRef).get(cacheKey);
      if (cached) return cached;
      return lookupGlossary(name, entries, classId);
    },
    [entries],
  );

  const fetchEntry = useCallback(
    async (name: string, classId?: string) => {
      const cacheKey = classId ? `${classId}:${glossaryKey(name)}` : glossaryKey(name);
      const cached = getCache(cacheRef).get(cacheKey);
      if (cached) return cached;

      const staticHit = lookupGlossary(name, entries, classId);
      if (staticHit?.summary && staticHit.kind !== 'unknown') {
        getCache(cacheRef).set(cacheKey, staticHit);
        return staticHit;
      }

      const pending = getCache(inflightRef).get(cacheKey);
      if (pending) return pending;

      const promise = api
        .lookupGlossary([name], true)
        .then((res) => {
          const entry = res.entries[name] as GlossaryEntry | undefined;
          if (entry) getCache(cacheRef).set(cacheKey, entry);
          return entry ?? null;
        })
        .finally(() => {
          getCache(inflightRef).delete(cacheKey);
        });

      getCache(inflightRef).set(cacheKey, promise);
      return promise;
    },
    [entries],
  );

  const value = useMemo(() => ({ ready, getEntry, fetchEntry }), [ready, getEntry, fetchEntry]);

  return <GlossaryContext.Provider value={value}>{children}</GlossaryContext.Provider>;
}

export function useGlossary() {
  const ctx = use(GlossaryContext);
  if (!ctx) {
    return {
      ready: true,
      getEntry: () => null,
      fetchEntry: async () => null,
    };
  }
  return ctx;
}
