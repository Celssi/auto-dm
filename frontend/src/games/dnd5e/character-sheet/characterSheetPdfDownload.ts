import type { Character } from '../../../types';
import type { PdfUnlockedFeatures } from './characterSheetPdfAssembly';

export async function downloadCharacterPdf(
  character: Character,
  filename?: string,
  unlockedFeatures?: PdfUnlockedFeatures,
) {
  const pdf = await import('@react-pdf/renderer');
  pdf.Font.registerHyphenationCallback((word) => [word]);
  const { buildSheetDocument } = await import('./characterSheetPdfAssembly');
  const blob = await pdf.pdf(buildSheetDocument(pdf, character, unlockedFeatures)).toBlob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || `${character.name || 'character'}-sheet.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}
