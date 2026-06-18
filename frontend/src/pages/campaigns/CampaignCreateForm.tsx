import { m } from '../../lib/framer';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';
import ChoiceGroup from '../../components/ui/forms/ChoiceGroup';
import SegmentedControl from '../../components/ui/forms/SegmentedControl';
import Toggle from '../../components/ui/forms/Toggle';
import type { CampaignsState } from './campaignsState';

interface Props {
  createMode: 'manual' | 'ai';
  form: CampaignsState['form'];
  generateForm: CampaignsState['generateForm'];
  characters: { id: string; name: string }[];
  generating: boolean;
  onCreateModeChange: (mode: 'manual' | 'ai') => void;
  onPatchForm: (patch: Partial<CampaignsState['form']>) => void;
  onPatchGenerateForm: (patch: Partial<CampaignsState['generateForm']>) => void;
  onCreateManual: () => void;
  onGenerate: () => void;
  onCancel: () => void;
}

export default function CampaignCreateForm({
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
  onCancel,
}: Props) {
  const canGenerate = generateForm.character_id && generateForm.theme.trim();

  return (
    <m.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="panel-glow p-5 space-y-4 overflow-hidden"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="section-heading">Create campaign</h2>
        <SegmentedControl
          value={createMode}
          onChange={(mode) => onCreateModeChange(mode as 'manual' | 'ai')}
          options={[
            { value: 'ai', label: 'AI generate' },
            { value: 'manual', label: 'Manual' },
          ]}
        />
      </div>

      {createMode === 'manual' ? (
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
      ) : (
        <>
          <p className="text-sm text-muted leading-relaxed">
            Generate a story arc and a sequence of adventures. Use module mode to base the campaign on a published
            adventure book from your indexed PDFs.
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

          <Field label={generateForm.mode === 'module' ? 'Book or adventure name' : 'Theme / hook'}>
            <TextArea
              placeholder={
                generateForm.mode === 'module'
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
                onChange={(e) =>
                  onPatchGenerateForm({
                    adventure_count: Math.max(1, Math.min(8, Number(e.target.value) || 3)),
                  })
                }
              />
            </Field>
          </div>

          <Toggle
            checked={generateForm.include_faerun}
            onChange={(include_faerun) => onPatchGenerateForm({ include_faerun })}
            label="Use Faerûn supplements in rules search"
          />

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
      )}
    </m.div>
  );
}
