import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api } from '../api/client';
import { fuzzyGlossaryLookup, glossaryKey, type GlossaryEntry } from '../lib/glossary';

interface GlossaryContextValue {
  ready: boolean;
  getEntry: (name: string) => GlossaryEntry | null;
  fetchEntry: (name: string) => Promise<GlossaryEntry | null>;
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
      .catch(() => setReady(true));
  }, []);

  const getEntry = useCallback(
    (name: string) => {
      const cached = getCache(cacheRef).get(glossaryKey(name));
      if (cached) return cached;
      return fuzzyGlossaryLookup(name, entries);
    },
    [entries],
  );

  const fetchEntry = useCallback(
    async (name: string) => {
      const key = glossaryKey(name);
      const cached = getCache(cacheRef).get(key);
      if (cached) return cached;

      const staticHit = fuzzyGlossaryLookup(name, entries);
      if (staticHit?.summary && staticHit.kind !== 'unknown') {
        getCache(cacheRef).set(key, staticHit);
        return staticHit;
      }

      const pending = getCache(inflightRef).get(key);
      if (pending) return pending;

      const promise = api
        .lookupGlossary([name], true)
        .then((res) => {
          const entry = res.entries[name] as GlossaryEntry | undefined;
          if (entry) getCache(cacheRef).set(key, entry);
          return entry ?? null;
        })
        .finally(() => {
          getCache(inflightRef).delete(key);
        });

      getCache(inflightRef).set(key, promise);
      return promise;
    },
    [entries],
  );

  const value = useMemo(() => ({ ready, getEntry, fetchEntry }), [ready, getEntry, fetchEntry]);

  return <GlossaryContext.Provider value={value}>{children}</GlossaryContext.Provider>;
}

export function useGlossary() {
  const ctx = useContext(GlossaryContext);
  if (!ctx) {
    return {
      ready: true,
      getEntry: () => null,
      fetchEntry: async () => null,
    };
  }
  return ctx;
}
