import type { Character } from '../../types';
import type { PdfModule } from './characterSheetPdfTypes';
import { buildSheetPage1 } from './characterSheetPdfPage1';
import { buildSheetPage2 } from './characterSheetPdfPage2';

export function buildSheetDocument(pdf: PdfModule, c: Character) {
  const { Document } = pdf;
  return (
    <Document>
      {buildSheetPage1(pdf, c)}
      {buildSheetPage2(pdf, c)}
    </Document>
  );
}
