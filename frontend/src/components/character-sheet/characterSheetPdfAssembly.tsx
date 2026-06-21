import type { Character } from '../../types';
import type { PdfModule } from './characterSheetPdfTypes';
import { buildSheetPage1 } from './characterSheetPdfPage1';
import { buildSheetPage2 } from './characterSheetPdfPage2';

export type PdfUnlockedFeatures = {
  class_features?: Record<string, string[]>;
  subclass_features?: Record<string, string[]>;
  species_traits?: Array<{ id: string; label: string; detail?: string; display: string }>;
  resolved_choices?: Array<{ id: string; label: string; value_label: string }>;
};

export function buildSheetDocument(pdf: PdfModule, c: Character, unlockedFeatures?: PdfUnlockedFeatures) {
  const { Document } = pdf;
  return (
    <Document title={`${c.name || 'Character'} - D&D Character Sheet`}>
      {buildSheetPage1(pdf, c, unlockedFeatures)}
      {buildSheetPage2(pdf, c)}
    </Document>
  );
}
