import type { Character } from '../../types';

export async function downloadCharacterPdf(character: Character, filename?: string) {
  const [pdf, { buildSheetDocument }] = await Promise.all([
    import('@react-pdf/renderer'),
    import('./characterSheetPdfAssembly'),
  ]);
  const blob = await pdf.pdf(buildSheetDocument(pdf, character)).toBlob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || `${character.name || 'character'}-sheet.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}
