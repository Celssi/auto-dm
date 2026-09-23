import type { ComponentType } from 'react';
import type { Character } from '../types';
import CharacterWizard from './dnd5e/character-sheet/CharacterWizard';
import CharacterSetupPanel from './brambletrek/CharacterSetupPanel';

type WizardProps = {
  initial?: Character;
  onSave: (c: Character) => void | Promise<void>;
  onCancel: () => void;
};

type SetupProps = {
  characterId: string | null;
  entity: Record<string, unknown>;
  onChange: (entity: Record<string, unknown>) => void;
  onSaved: (entity: Record<string, unknown>) => void | Promise<void>;
};

const CHARACTER_WIZARDS: Partial<Record<string, ComponentType<WizardProps>>> = {
  dnd5e: CharacterWizard,
};

const CHARACTER_SETUP: Partial<Record<string, ComponentType<SetupProps>>> = {
  brambletrek: CharacterSetupPanel,
};

export function GameCharacterWizard({ gameId, ...props }: WizardProps & { gameId: string }) {
  const Wizard = CHARACTER_WIZARDS[gameId];
  if (!Wizard) return null;
  return <Wizard {...props} />;
}

export function GameCharacterSetup({ gameId, ...props }: SetupProps & { gameId: string }) {
  const Setup = CHARACTER_SETUP[gameId];
  if (!Setup) return null;
  return <Setup {...props} />;
}
