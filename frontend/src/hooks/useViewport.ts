import { useEffect, useState } from 'react';

export type Viewport = 'phone' | 'tablet' | 'desktop';

function viewportFromWidth(width: number): Viewport {
  if (width < 768) return 'phone';
  if (width < 1280) return 'tablet';
  return 'desktop';
}

export function useViewport(): Viewport {
  const [viewport, setViewport] = useState<Viewport>(() =>
    typeof window === 'undefined' ? 'desktop' : viewportFromWidth(window.innerWidth),
  );

  useEffect(() => {
    const onResize = () => setViewport(viewportFromWidth(window.innerWidth));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return viewport;
}
