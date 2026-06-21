import type { PdfModule } from './characterSheetPdfTypes';
import { createCirclePip } from './characterSheetPdfCirclePip';
import { createDiamondPip } from './characterSheetPdfDiamondPip';
import { createPipRow } from './characterSheetPdfPipRow';

export function createPdfShapes(pdf: PdfModule) {
  return {
    CirclePip: createCirclePip(pdf),
    DiamondPip: createDiamondPip(pdf),
    PipRow: createPipRow(pdf),
  };
}

/** Stack long header labels on two lines to avoid awkward hyphenation. */
export function stackLabel(label: string): string {
  if (label.length <= 14) return label;
  if (label.includes(' & ')) {
    return label.replace(' & ', '\n& ');
  }
  const words = label.split(' ');
  if (words.length === 2) return words.join('\n');
  if (words.length > 2) {
    const mid = Math.ceil(words.length / 2);
    return `${words.slice(0, mid).join(' ')}\n${words.slice(mid).join(' ')}`;
  }
  return label;
}

/** Format hit dice without line breaks (e.g. 3d8). */
export function formatHitDice(count: number, die: number): string {
  return `${count}d${die}`;
}
