export function visibleLonelogLines(lonelog: string[]): string[] {
  const lines: string[] = [];
  for (const line of lonelog.slice(-24)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (/^#+\s/.test(trimmed)) continue;
    if (/^_.*_$/.test(trimmed)) continue;
    lines.push(line);
  }
  return lines;
}
