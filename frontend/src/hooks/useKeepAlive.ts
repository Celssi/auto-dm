import { useEffect, useRef } from 'react';
import { api } from '../api/client';

const PING_MS = 15_000;

export function useKeepAlive(active: boolean) {
  const alive = useRef(false);
  alive.current = active;

  useEffect(() => {
    if (!active) return;

    const ping = () => {
      if (!alive.current) return;
      void api.keepalive().catch(() => {
        /* The open job request is the source of truth. */
      });
    };

    ping();
    const timer = window.setInterval(ping, PING_MS);
    return () => window.clearInterval(timer);
  }, [active]);
}
