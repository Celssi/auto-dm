import { useLocation } from 'react-router-dom';

/** Prevents React StrictMode from replaying the same route enter animation. */
const seenRouteKeys = new Set<string>();

export function useStaggerInitial(): false | 'initial' {
  const { key } = useLocation();
  if (seenRouteKeys.has(key)) return false;
  seenRouteKeys.add(key);
  return 'initial';
}
