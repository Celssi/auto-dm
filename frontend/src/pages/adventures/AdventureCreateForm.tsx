import { m } from '../../lib/framer';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';
import ChoiceGroup from '../../components/ui/forms/ChoiceGroup';
import Toggle from '../../components/ui/forms/Toggle';
import type { AdventuresState } from './adventuresState';

interface Props {
  form: AdventuresState['form'];
  characters: AdventuresState['characters'];
  campaigns: AdventuresState['campaigns'];
  onPatchForm: (patch: Partial<AdventuresState['form']>) => void;
  onCreate: () => void;
  onCancel: () => void;
}

export default function AdventureCreateForm({
  form,
  characters,
  campaigns,
  onPatchForm,
  onCreate,
  onCancel,
}: Props) {
  return (
    <m.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="panel-glow p-5 space-y-4 overflow-hidden"
    >
      <h2 className="section-heading">Generate adventure</h2>
      <Field label="Adventure name">
        <TextInput
          placeholder="Adventure name"
          value={form.name}
          onChange={(e) => onPatchForm({ name: e.target.value })}
        />
      </Field>
      <Field label="Mode">
        <ChoiceGroup
          value={form.mode}
          onChange={(mode) => onPatchForm({ mode })}
          options={[
            { value: 'freeform', label: 'Freeform (AI generates)' },
            { value: 'module', label: 'Module (Faerûn books)' },
            { value: 'hybrid', label: 'Hybrid' },
          ]}
          columns={2}
        />
      </Field>
      <Field label="Theme or hook">
        <TextArea
          placeholder="Theme or hook"
          value={form.theme}
          onChange={(e) => onPatchForm({ theme: e.target.value })}
        />
      </Field>
      <Field label="Campaign (optional)">
        <ChoiceGroup
          value={form.campaign_id}
          onChange={(campaign_id) => onPatchForm({ campaign_id })}
          options={campaigns.map((c) => ({ value: c.id, label: c.name }))}
          allowEmpty
          emptyLabel="Standalone adventure"
          columns={2}
        />
      </Field>
      <Field label="Character (optional)">
        <ChoiceGroup
          value={form.character_id}
          onChange={(character_id) => onPatchForm({ character_id })}
          options={characters.map((c) => ({ value: c.id, label: c.name }))}
          allowEmpty
          emptyLabel="None"
          columns={2}
        />
      </Field>
      <Toggle
        checked={form.include_faerun}
        onChange={(include_faerun) => onPatchForm({ include_faerun })}
        label="Include Faerûn supplements in outline generation"
      />
      <div className="flex gap-2">
        <button type="button" className="btn-primary" onClick={onCreate}>
          Generate & save
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </m.div>
  );
}
