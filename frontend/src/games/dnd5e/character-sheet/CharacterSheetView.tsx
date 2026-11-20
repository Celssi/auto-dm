import type { Character } from '../../../types';
import CharacterSheetHeader from './CharacterSheetHeader';
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

  const cards = (
    <>
      {page !== 2 && <CharacterSheetPage1 {...shared} hideHeader />}
      {page !== 1 && <CharacterSheetPage2 {...shared} />}
    </>
  );

  return (
    <div className="sheet-root space-y-6">
      {!hideHeader && page !== 2 && (
        <CharacterSheetHeader character={character} editable={editable} onChange={onChange} />
      )}
      <div className="sheet-masonry">{cards}</div>
    </div>
  );
}
