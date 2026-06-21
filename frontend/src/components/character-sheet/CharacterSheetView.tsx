import type { Character } from '../../types';
import CharacterSheetPage1 from './CharacterSheetPage1';
import CharacterSheetPage2 from './CharacterSheetPage2';

interface Props {
  character: Character;
  summary?: Record<string, unknown>;
  editable?: boolean;
  onChange?: (patch: Partial<Character>) => void;
  page?: 1 | 2;
  hideHeader?: boolean;
}

export default function CharacterSheetView({ character, summary, editable, onChange, page, hideHeader }: Props) {
  const shared = { character, summary, editable, onChange, hideHeader };

  if (page === 1) return <CharacterSheetPage1 {...shared} />;
  if (page === 2) return <CharacterSheetPage2 {...shared} />;

  return (
    <div className="sheet-root space-y-6">
      <CharacterSheetPage1 {...shared} />
      <CharacterSheetPage2 {...shared} />
    </div>
  );
}
