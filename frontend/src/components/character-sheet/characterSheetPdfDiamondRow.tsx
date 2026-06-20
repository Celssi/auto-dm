import type { PdfModule } from './characterSheetPdfTypes';
import { createPdfShapes } from './characterSheetPdfShapes';

export function createDiamondRow(pdf: PdfModule) {
  const { PipRow } = createPdfShapes(pdf);
  return function DiamondRow({ count, filled }: { count: number; filled: number }) {
    return <PipRow count={count} filled={filled} shape="diamond" gap={4} />;
  };
}
