import type { Character } from '../../../types';
import CreationChoicesForm from '../CreationChoicesForm';
import { validateChoices, choicesForDraft, type CreationChoiceCatalog } from '../../../lib/creationChoices';

interface Props {
  char: Character;
  options: Record<string, unknown>;
  patch: (p: Partial<Character>) => void;
}

export default function WizardFeaturesStep({ char, options, patch }: Props) {
  const catalog = (options.creation_choice_catalog || {}) as CreationChoiceCatalog;
  const missing = validateChoices(char, choicesForDraft(char, options, catalog));

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted leading-relaxed">
        Species traits, class features, and origin-feat options from the PHB. Required picks must be completed before
        finishing character creation.
      </p>
      <CreationChoicesForm char={char} options={options} patch={patch} />
      {missing.length > 0 && <p className="text-xs text-amber-400/90">Still needed: {missing.join('; ')}</p>}
    </div>
  );
}
