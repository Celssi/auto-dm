import type { Character } from '../../../types';
import type { PdfUnlockedFeatures } from './characterSheetPdfAssembly';

export async function downloadCharacterPdf(
  character: Character,
  filename?: string,
  unlockedFeatures?: PdfUnlockedFeatures,
) {
  const { downloadCharacterPdf: render } = await import('./characterSheetPdfDownload');
  return render(character, filename, unlockedFeatures);
}
