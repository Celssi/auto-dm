import type { PdfModule } from './characterSheetPdfTypes';
import { createBox } from './characterSheetPdfBox';
import { createDiamondRow } from './characterSheetPdfDiamondRow';
import { createHeaderField } from './characterSheetPdfHeaderField';
import { createAbilityBlock } from './characterSheetPdfAbilityBlock';
import { ABILITIES } from './sheetConstants';

export function createPdfParts(pdf: PdfModule) {
  return {
    Box: createBox(pdf),
    DiamondRow: createDiamondRow(pdf),
    HeaderField: createHeaderField(pdf),
    AbilityBlock: createAbilityBlock(pdf),
    ABILITIES,
  };
}
