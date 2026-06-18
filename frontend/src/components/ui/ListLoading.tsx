export default function ListLoading({ className = '' }: { className?: string }) {
  return <p className={`text-sm text-muted ${className}`.trim()}>Loading…</p>;
}
