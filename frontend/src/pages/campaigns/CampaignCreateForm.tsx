import { m } from '../../lib/framer';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';

interface Props {
  form: { name: string; story_arc: string };
  onPatch: (patch: Partial<{ name: string; story_arc: string }>) => void;
  onCreate: () => void;
  onCancel: () => void;
}

export default function CampaignCreateForm({ form, onPatch, onCreate, onCancel }: Props) {
  return (
    <m.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="panel-glow p-5 space-y-4 overflow-hidden"
    >
      <h2 className="section-heading">Create campaign</h2>
      <Field label="Campaign name">
        <TextInput placeholder="Campaign name" value={form.name} onChange={(e) => onPatch({ name: e.target.value })} />
      </Field>
      <Field label="Story arc / notes">
        <TextArea
          placeholder="Story arc / campaign notes"
          value={form.story_arc}
          onChange={(e) => onPatch({ story_arc: e.target.value })}
          className="min-h-[120px]"
        />
      </Field>
      <div className="flex gap-2">
        <button type="button" className="btn-primary" onClick={onCreate}>
          Create
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </m.div>
  );
}
