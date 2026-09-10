import { useEffect, useRef, useState } from "react";

// CONTRACT.md Section 13: polling is the ONLY frontend/backend transport.
// ~2s interval, no faster, no WebSocket, no SSE.

export function usePolling<T>(
  fetcher: () => Promise<T | null>,
  intervalMs = 2000,
  enabled = true,
): T | null {
  const [data, setData] = useState<T | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      const result = await fetcherRef.current();
      if (!cancelled && result !== null) setData(result);
      if (!cancelled) timer = setTimeout(tick, intervalMs);
    };
    tick();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [intervalMs, enabled]);

  return data;
}
