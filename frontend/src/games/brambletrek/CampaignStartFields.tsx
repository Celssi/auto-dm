import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';
import ChoiceGroup from '../../components/ui/forms/ChoiceGroup';
import { gameShortLabel } from '../registry';

interface CharacterOption {
  id: string;
  name: string;
  game_id?: string;
}

interface Props {
  characters: CharacterOption[];
  characterId: string;
  onCharacterIdChange: (id: string) => void;
  activeAdventure: string;
  onActiveAdventureChange: (id: string) => void;
  campaignName: string;
  onCampaignNameChange: (name: string) => void;
  flavorNotes: string;
  onFlavorNotesChange: (notes: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  submitLabel?: string;
  cancelLabel?: string;
  onCancel?: () => void;
  showActions?: boolean;
}

export default function BrambletrekCampaignStartFields({
  characters,
  characterId,
  onCharacterIdChange,
  activeAdventure,
  onActiveAdventureChange,
  campaignName,
  onCampaignNameChange,
  flavorNotes,
  onFlavorNotesChange,
  onSubmit,
  submitting,
  submitLabel = 'Start adventure',
  cancelLabel = 'Cancel',
  onCancel,
  showActions = true,
}: Props) {
  const btCharacters = characters.filter((c) => (c.game_id || 'dnd5e') === 'brambletrek');
  const syncedCharacterRef = useRef('');
  const onActiveAdventureChangeRef = useRef(onActiveAdventureChange);
  onActiveAdventureChangeRef.current = onActiveAdventureChange;

  const { data: characterAdventure } = useQuery({
    queryKey: ['brambletrek-character-adventure', characterId],
    queryFn: async () => {
      const { character } = await api.getCharacter(characterId);
      return String((character as Record<string, unknown>).active_adventure || '');
    },
    enabled: Boolean(characterId),
  });

  useEffect(() => {
    if (!characterId || characterAdventure === undefined) return;
    if (syncedCharacterRef.current === characterId) return;
    syncedCharacterRef.current = characterId;
    onActiveAdventureChangeRef.current(characterAdventure);
  }, [characterId, characterAdventure]);

  const { data: adventureOptions = [] } = useQuery({
    queryKey: ['brambletrek-adventure-modules'],
    queryFn: async () => {
      const res = await api.getCharacterOptions(false, 'brambletrek');
      const adventures = (res as { adventures?: { id: string; label: string }[] }).adventures || [];
      return adventures.filter((a) => a.id);
    },
  });

  const selectedModule = adventureOptions.find((a) => a.id === activeAdventure);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted leading-relaxed">
        Brambletrek adventures come from the rulebook and modules — not AI-generated story arcs. Pick your Gnawborn
        and adventure module, then journal by drawing cards and describing what happens.
      </p>

      <Field label="Character">
        {btCharacters.length === 0 ? (
          <p className="text-sm text-muted">
            <Link to="/characters" className="text-accent hover:underline">
              Create a Gnawborn
            </Link>{' '}
            first.
          </p>
        ) : (
          <ChoiceGroup
            value={characterId}
            onChange={onCharacterIdChange}
            options={btCharacters.map((c) => ({
              value: c.id,
              label: `${c.name} (${gameShortLabel(c.game_id)})`,
            }))}
            allowEmpty
            emptyLabel="Select character"
            columns={2}
          />
        )}
      </Field>

      {characterId && (
        <Field label="Adventure module" hint="Set on the character sheet; change here if you want a different book adventure.">
          <select
            className="select w-full"
            value={activeAdventure}
            onChange={(e) => onActiveAdventureChange(e.target.value)}
            aria-label="Adventure module"
          >
            <option value="">Hyhill solo (core rules)</option>
            {adventureOptions.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
          {selectedModule && (
            <p className="text-xs text-muted mt-2">
              Play uses curated tables from <span className="text-gray-300">{selectedModule.label}</span>. Draw journey
              cards each in-game day and narrate the results.
            </p>
          )}
          {!activeAdventure && (
            <p className="text-xs text-muted mt-2">
              Open Hyhill exploration with core journey and encounter tables from the Complete Digital Edition.
            </p>
          )}
        </Field>
      )}

      <Field label="Campaign name (optional)">
        <TextInput
          placeholder="e.g. Tuke's autumn journal"
          value={campaignName}
          onChange={(e) => onCampaignNameChange(e.target.value)}
        />
      </Field>

      <Field label="Personal hook (optional)" hint="Flavor for the opening scene — the book tables drive play.">
        <TextArea
          placeholder="e.g. Returning to Hyhill after a long journey north"
          value={flavorNotes}
          onChange={(e) => onFlavorNotesChange(e.target.value)}
          className="min-h-[72px]"
        />
      </Field>

      {showActions && (
        <div className="flex gap-2">
          <button
            type="button"
            className="btn-primary"
            disabled={!characterId || submitting || btCharacters.length === 0}
            onClick={onSubmit}
          >
            {submitting ? 'Starting…' : submitLabel}
          </button>
          {onCancel && (
            <button type="button" className="btn-ghost" onClick={onCancel}>
              {cancelLabel}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
