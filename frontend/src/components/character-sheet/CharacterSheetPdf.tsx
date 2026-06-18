import type { Character } from '../../types';

export async function downloadCharacterPdf(character: Character, filename?: string) {
  const { downloadCharacterPdf: render } = await import('./characterSheetPdfDownload');
  return render(character, filename);
}
