export default function PageSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-live="polite" aria-label="Loading">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="panel p-4 space-y-2">
          <div className="h-4 w-1/3 max-w-[12rem] rounded bg-border/80 animate-pulse" />
          <div className="h-3 w-2/3 max-w-[20rem] rounded bg-border/50 animate-pulse" />
          <div className="h-3 w-1/2 max-w-[16rem] rounded bg-border/40 animate-pulse" />
        </div>
      ))}
    </div>
  );
}
