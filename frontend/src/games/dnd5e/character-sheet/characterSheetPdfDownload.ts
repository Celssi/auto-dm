import type { Character } from '../../../types';
import type { PdfUnlockedFeatures } from './characterSheetPdfAssembly';

export function characterPdfFilename(name?: string): string {
  const cleaned = (name || 'character')
    .replace(/[<>:"/\\|?*\u0000-\u001f]+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80);
  return `${cleaned || 'character'}-sheet.pdf`;
}

export async function renderCharacterPdfBlob(
  character: Character,
  unlockedFeatures?: PdfUnlockedFeatures,
): Promise<Blob> {
  const pdf = await import('@react-pdf/renderer');
  pdf.Font.registerHyphenationCallback((word) => [word]);
  const { buildSheetDocument } = await import('./characterSheetPdfAssembly');
  return pdf.pdf(buildSheetDocument(pdf, character, unlockedFeatures)).toBlob();
}

export function triggerBlobDownload(blob: Blob, filename: string) {
  if (typeof document === 'undefined') {
    throw new Error('PDF download needs a browser window.');
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.rel = 'noopener';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export async function downloadCharacterPdf(
  character: Character,
  filename?: string,
  unlockedFeatures?: PdfUnlockedFeatures,
) {
  const blob = await renderCharacterPdfBlob(character, unlockedFeatures);
  if (!blob || blob.size < 8) {
    throw new Error('The character sheet PDF was empty.');
  }
  triggerBlobDownload(blob, filename || characterPdfFilename(character.name));
}
