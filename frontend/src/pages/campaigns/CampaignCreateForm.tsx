import { m } from '../../lib/framer';
import { revealPanel } from '../../components/ui/motion';
import { getGamePlayConfig } from '../../games/play/registry';
import type { GameId } from '../../games/registry';
import BrambletrekCampaignStartFields from '../../games/brambletrek/CampaignStartFields';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';
import ChoiceGroup from '../../components/ui/forms/ChoiceGroup';
import SegmentedControl from '../../components/ui/forms/SegmentedControl';
import Toggle from '../../components/ui/forms/Toggle';
import type { CampaignsState } from './campaignsState';
import LongJobOverlay from '../../components/LongJobOverlay';

interface Props {
  gameId: GameId;
  createMode: 'manual' | 'ai';
  form: CampaignsState['form'];
  generateForm: CampaignsState['generateForm'];
  characters: CampaignsState['characters'];
  generating: boolean;
  onCreateModeChange: (mode: 'manual' | 'ai') => void;
  onPatchForm: (patch: Partial<CampaignsState['form']>) => void;
  onPatchGenerateForm: (patch: Partial<CampaignsState['generateForm']>) => void;
  onCreateManual: () => void;
  onGenerate: () => void;
  onBootstrapBrambletrek: () => void;
  onCancel: () => void;
}

export default function CampaignCreateForm({
  gameId,
  createMode,
  form,
  generateForm,
  characters,
  generating,
  onCreateModeChange,
  onPatchForm,
  onPatchGenerateForm,
  onCreateManual,
  onGenerate,
  onBootstrapBrambletrek,
  onCancel,
}: Props) {
  const playConfig = getGamePlayConfig(gameId);
  const showBrambletrekFlow = !playConfig.usesAiCampaignGeneration;
  const canGenerate = generateForm.character_id && generateForm.theme.trim();

  return (
    <m.div {...revealPanel} className="panel-glow p-5 space-y-4 overflow-hidden">
      <LongJobOverlay
        active={generating}
        title="Generating campaign"
        message="Keep this tab open. Heartbeats keep Cloud Run from scaling to zero."
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="section-heading">{showBrambletrekFlow ? 'Start Brambletrek adventure' : 'Create campaign'}</h2>
        {!showBrambletrekFlow && (
          <SegmentedControl
            value={createMode}
            onChange={(mode) => onCreateModeChange(mode as 'manual' | 'ai')}
            options={[
              { value: 'ai', label: 'AI generate' },
              { value: 'manual', label: 'Manual' },
            ]}
          />
        )}
      </div>

      {showBrambletrekFlow ? (
        <BrambletrekCampaignStartFields
          characters={characters}
          characterId={generateForm.character_id}
          onCharacterIdChange={(character_id) => onPatchGenerateForm({ character_id })}
          activeAdventure={generateForm.active_adventure}
          onActiveAdventureChange={(active_adventure) => onPatchGenerateForm({ active_adventure })}
          campaignName={generateForm.campaign_name}
          onCampaignNameChange={(campaign_name) => onPatchGenerateForm({ campaign_name })}
          flavorNotes={generateForm.theme}
          onFlavorNotesChange={(theme) => onPatchGenerateForm({ theme })}
          onSubmit={onBootstrapBrambletrek}
          submitting={generating}
          submitLabel="Start adventure"
          onCancel={onCancel}
        />
      ) : createMode === 'manual' ? (
        <ManualCampaignFields
          form={form}
          onPatchForm={onPatchForm}
          onCreateManual={onCreateManual}
          onCancel={onCancel}
        />
      ) : (
        <AiCampaignFields
          characters={characters}
          generateForm={generateForm}
          generating={generating}
          canGenerate={Boolean(canGenerate)}
          showFaerun={playConfig.showFaerunToggle}
          onPatchGenerateForm={onPatchGenerateForm}
          onGenerate={onGenerate}
          onCancel={onCancel}
        />
      )}
    </m.div>
  );
}

function ManualCampaignFields({
  form,
  onPatchForm,
  onCreateManual,
  onCancel,
}: {
  form: CampaignsState['form'];
  onPatchForm: (patch: Partial<CampaignsState['form']>) => void;
  onCreateManual: () => void;
  onCancel: () => void;
}) {
  return (
    <>
      <Field label="Campaign name">
        <TextInput
          placeholder="Campaign name"
          value={form.name}
          onChange={(e) => onPatchForm({ name: e.target.value })}
        />
      </Field>
      <Field label="Story arc / notes">
        <TextArea
          placeholder="Story arc / campaign notes"
          value={form.story_arc}
          onChange={(e) => onPatchForm({ story_arc: e.target.value })}
          className="min-h-[120px]"
        />
      </Field>
      <div className="flex gap-2">
        <button type="button" className="btn-primary" onClick={onCreateManual} disabled={!form.name.trim()}>
          Create
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </>
  );
}

function AiCampaignFields({
  characters,
  generateForm,
  generating,
  canGenerate,
  showFaerun,
  onPatchGenerateForm,
  onGenerate,
  onCancel,
}: {
  characters: CampaignsState['characters'];
  generateForm: CampaignsState['generateForm'];
  generating: boolean;
  canGenerate: boolean;
  showFaerun: boolean;
  onPatchGenerateForm: (patch: Partial<CampaignsState['generateForm']>) => void;
  onGenerate: () => void;
  onCancel: () => void;
}) {
  const moduleMode = generateForm.mode === 'module';
  return (
    <>
      <p className="text-sm text-muted leading-relaxed">
        Generate a story arc and a sequence of adventures. Use module mode to base the campaign on a published adventure
        book from your indexed PDFs.
      </p>
      <Field label="Character">
        {characters.length === 0 ? (
          <p className="text-sm text-muted">Create a character first to generate a campaign.</p>
        ) : (
          <ChoiceGroup
            value={generateForm.character_id}
            onChange={(character_id) => onPatchGenerateForm({ character_id })}
            options={characters.map((c) => ({ value: c.id, label: c.name }))}
            columns={2}
          />
        )}
      </Field>
      <Field label="Source">
        <SegmentedControl
          value={generateForm.mode}
          onChange={(mode) => onPatchGenerateForm({ mode: mode as 'freeform' | 'module' })}
          options={[
            { value: 'freeform', label: 'Random / original' },
            { value: 'module', label: 'Adventure book' },
          ]}
        />
      </Field>
      <Field label={moduleMode ? 'Book or adventure name' : 'Theme / hook'}>
        <TextArea
          placeholder={
            moduleMode
              ? 'e.g. Lost Mine of Phandelver, Stormwreck Isle'
              : 'e.g. A cursed forest spreading toward the capital'
          }
          value={generateForm.theme}
          onChange={(e) => onPatchGenerateForm({ theme: e.target.value })}
          className="min-h-[80px]"
        />
      </Field>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Campaign name (optional)">
          <TextInput
            placeholder="Campaign name"
            value={generateForm.campaign_name}
            onChange={(e) => onPatchGenerateForm({ campaign_name: e.target.value })}
          />
        </Field>
        <Field label="Number of adventures">
          <TextInput
            type="number"
            min={1}
            max={8}
            value={String(generateForm.adventure_count)}
            onChange={(e) => {
              const parsed = e.currentTarget.valueAsNumber;
              if (!Number.isFinite(parsed)) return;
              onPatchGenerateForm({ adventure_count: Math.max(1, Math.min(8, parsed)) });
            }}
          />
        </Field>
      </div>
      {showFaerun && (
        <Toggle
          checked={generateForm.include_faerun}
          onChange={(include_faerun) => onPatchGenerateForm({ include_faerun })}
          label="Use Faerûn supplements in rules search"
        />
      )}
      <Toggle
        checked={generateForm.bootstrap_first}
        onChange={(bootstrap_first) => onPatchGenerateForm({ bootstrap_first })}
        label="Generate opening scene for first adventure and jump to play"
      />
      <div className="flex gap-2">
        <button type="button" className="btn-primary" disabled={!canGenerate || generating} onClick={onGenerate}>
          {generating ? 'Generating campaign… (45-90 s)' : 'Generate campaign'}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </>
  );
}
