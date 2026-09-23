import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Shuffle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api, type ResourceDraft, type ResourceDraftResponse } from '../../api/client';
import { Field } from '../../components/ui/forms/Field';
import TextInput from '../../components/ui/forms/TextInput';
import TextArea from '../../components/ui/forms/TextArea';
import { applyLegacyStatSwap, applyLegacyToBases, hasResourceBases } from './legacyStats';
import { useToast } from '../../components/ui/toast';

interface TableOption {
  id: string;
  label: string;
}

interface LegacyOption {
  id: string;
  label: string;
  boost?: string;
  flaw?: string;
  health_delta?: number;
  morale_delta?: number;
  supplies_delta?: number;
  abilities?: { id: string; label: string; description: string; tags: string[] }[];
}

interface CharacterOptions {
  reasons: TableOption[];
  backgrounds: TableOption[];
  trinkets: TableOption[];
  card_bands: TableOption[];
  legacies: LegacyOption[];
  adventures: TableOption[];
}

interface Props {
  characterId: string | null;
  entity: Record<string, unknown>;
  onChange: (entity: Record<string, unknown>) => void;
  onSaved?: (entity: Record<string, unknown>) => void;
}

function CardDrawnDisplay({ bandId, card, cardBands }: { bandId: string; card?: string; cardBands: TableOption[] }) {
  if (card) {
    return (
      <div className="text-[11px] text-muted">
        Card drawn: <span className="text-gray-300">{card}</span>
      </div>
    );
  }
  if (!bandId) return null;
  const bandLabel = cardBands.find((b) => b.id === bandId)?.label;
  if (!bandLabel) return null;
  return (
    <div className="mt-1.5 text-[11px] text-muted">
      Card band: <span className="text-gray-300">{bandLabel}</span>
    </div>
  );
}

function TableDrawField({
  label,
  value,
  options,
  bandId,
  card,
  cardBands,
  preview,
  drawing,
  disabled,
  onChange,
  onDraw,
}: {
  label: string;
  value: string;
  options: TableOption[];
  bandId: string;
  card?: string;
  cardBands: TableOption[];
  preview?: string;
  drawing: boolean;
  disabled?: boolean;
  onChange: (id: string) => void;
  onDraw: () => void;
}) {
  return (
    <section className="rounded-lg border border-border p-4 space-y-3">
      <div className="flex items-start justify-between gap-4">
        <span className="label-text pt-0.5">{label}</span>
        <button
          type="button"
          className="btn-ghost text-[11px] px-2.5 py-1.5 border border-border rounded-md inline-flex items-center gap-1 text-muted hover:text-accent shrink-0"
          disabled={drawing || disabled}
          onClick={onDraw}
        >
          {drawing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Shuffle className="w-3 h-3" />}
          Draw
        </button>
      </div>
      <select className="select w-full" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
        {options.map((o) => (
          <option key={o.id || 'empty'} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
      <CardDrawnDisplay bandId={bandId} card={card} cardBands={cardBands} />
      {preview && (
        <div className="rounded-lg border border-border/70 bg-bg/40 p-3.5 chat-markdown text-xs text-gray-300 leading-relaxed [&_p]:mt-2 [&_p:first-child]:mt-0">
          <ReactMarkdown>{preview}</ReactMarkdown>
        </div>
      )}
    </section>
  );
}

function mapResourceDraft(res: ResourceDraftResponse): ResourceDraft {
  return {
    cards_by_stat: res.cards_by_stat || {},
    pending_bonus: res.pending_bonus || [],
    base_stats: res.base_stats || { health: 0, morale: 0, supplies: 0 },
    final_stats: res.final_stats,
    stats: res.stats || [],
    remaining: res.remaining,
    draft: res.draft,
  };
}

export default function CharacterSetupPanel({ characterId, entity, onChange, onSaved }: Props) {
  const toast = useToast();
  const [resourceDraft, setResourceDraft] = useState<ResourceDraft | null>(null);
  const [saving, setSaving] = useState(false);
  const [drawing, setDrawing] = useState<string | null>(null);
  const [resourceBusy, setResourceBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: options = null } = useQuery({
    queryKey: ['brambletrek-character-options', characterId],
    queryFn: async () => {
      const res = await api.getCharacterOptions(false, 'brambletrek');
      return res as unknown as CharacterOptions;
    },
  });

  const reasonBand = String(entity.reason_band || '');
  const backgroundBand = String(entity.background_band || '');
  const trinketBand = String(entity.trinket_band || '');
  const reasonCard = String(entity.reason_card || '');
  const backgroundCard = String(entity.background_card || '');
  const trinketCard = String(entity.trinket_card || '');

  const { data: reasonPreview = '' } = useQuery({
    queryKey: ['brambletrek-reason-ending', reasonBand],
    queryFn: async () => {
      const r = await api.brambletrekReasonEnding(reasonBand);
      return r.preview;
    },
    enabled: Boolean(reasonBand),
  });

  const { data: tablePreviews = { reason: '', background: '', trinket: '' } } = useQuery({
    queryKey: [
      'brambletrek-table-previews',
      reasonBand,
      backgroundBand,
      trinketBand,
      reasonCard,
      backgroundCard,
      trinketCard,
    ],
    queryFn: async () => {
      const specs = [
        ['reason', reasonBand, reasonCard],
        ['background', backgroundBand, backgroundCard],
        ['trinket', trinketBand, trinketCard],
      ] as const;
      const results = await Promise.all(
        specs.map(([table, band, card]) =>
          band ? api.brambletrekCharacterTablePreview(table, band, card) : Promise.resolve({ preview: '' }),
        ),
      );
      return {
        reason: results[0].preview,
        background: results[1].preview,
        trinket: results[2].preview,
      };
    },
  });

  const patch = (key: string, value: unknown) => onChange({ ...entity, [key]: value });

  const drawTable = async (table: 'reason' | 'background' | 'trinket') => {
    if (!characterId) {
      setError('Save the character first to draw from the deck.');
      return;
    }
    setDrawing(table);
    setError(null);
    try {
      const res = await api.brambletrekDrawTable(characterId, table);
      onChange(res.character);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Draw failed');
    } finally {
      setDrawing(null);
    }
  };

  const changeLegacy = (id: string) => {
    const oldLegacy = options?.legacies.find((l) => l.id === String(entity.legacy || ''));
    const newLegacy = options?.legacies.find((l) => l.id === id);
    let stats: { health: number; morale: number; supplies: number };
    if (hasResourceBases(entity)) {
      stats = applyLegacyToBases(
        {
          health: Number(entity.resource_base_health ?? 0),
          morale: Number(entity.resource_base_morale ?? 0),
          supplies: Number(entity.resource_base_supplies ?? 0),
        },
        newLegacy,
      );
    } else {
      stats = applyLegacyStatSwap(
        {
          health: Number(entity.health ?? 10),
          morale: Number(entity.morale ?? 10),
          supplies: Number(entity.supplies ?? 10),
        },
        oldLegacy,
        newLegacy,
      );
    }
    onChange({
      ...entity,
      legacy: id,
      ...stats,
      legacy_abilities_used: {},
    });
    if (resourceDraft?.base_stats) {
      setResourceDraft({
        ...resourceDraft,
        final_stats: applyLegacyToBases(resourceDraft.base_stats, newLegacy),
      });
    }
  };

  const rollLegacy = async () => {
    if (!characterId) {
      setError('Save the character first to roll legacy.');
      return;
    }
    setDrawing('legacy');
    setError(null);
    try {
      const res = await api.brambletrekRollLegacy(characterId);
      changeLegacy(res.legacy_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Legacy roll failed');
    } finally {
      setDrawing(null);
    }
  };

  const drawResources = async () => {
    if (!characterId) {
      setError('Save the character first to draw resources.');
      return;
    }
    setResourceBusy('draw');
    setError(null);
    try {
      const res = await api.brambletrekDrawResources(characterId);
      setResourceDraft(mapResourceDraft(res));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Resource draw failed');
    } finally {
      setResourceBusy(null);
    }
  };

  const drawResourceBonus = async (stat: 'health' | 'morale' | 'supplies') => {
    if (!characterId || !resourceDraft?.draft) return;
    setResourceBusy(stat);
    setError(null);
    try {
      const res = await api.brambletrekResourceBonus(characterId, stat, undefined, resourceDraft.draft);
      setResourceDraft(mapResourceDraft(res));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Bonus draw failed');
    } finally {
      setResourceBusy(null);
    }
  };

  const applyResources = async () => {
    if (!characterId || !resourceDraft?.draft) return;
    setResourceBusy('apply');
    setError(null);
    try {
      const res = await api.brambletrekApplyResources(characterId, undefined, resourceDraft.draft);
      setResourceDraft(null);
      onChange(res.character);
      toast.success('Resources applied');
      onSaved?.(res.character);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Apply resources failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setResourceBusy(null);
    }
  };

  const selectedLegacy = options?.legacies.find((l) => l.id === String(entity.legacy || ''));

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      if (characterId) {
        const res = await api.updateCharacter(characterId, entity);
        onChange(res.character);
        const name = String(res.character.name || entity.name || '').trim();
        toast.success(name ? `Saved ${name}` : 'Character saved');
        onSaved?.(res.character);
      } else {
        const res = await api.createCharacter({ ...entity, game_id: 'brambletrek' });
        onChange(res.character);
        const name = String(res.character.name || entity.name || '').trim();
        toast.success(name ? `Created ${name}` : 'Character created');
        onSaved?.(res.character);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Save failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  if (!options) {
    return <p className="text-muted text-sm">Loading character tables…</p>;
  }

  const adventureOptions = options.adventures?.length ? options.adventures : [{ id: '', label: '— Not set —' }];

  return (
    <div className="space-y-6 panel-glow p-5">
      <p className="text-muted text-xs leading-relaxed">
        Create your Gnawborn — name, creation bands, legacy, resources, and active adventure module. Use{' '}
        <strong>Draw</strong> to pull table cards from the virtual deck.
      </p>

      <Field label="Name" className="space-y-2">
        <TextInput value={String(entity.name || '')} onChange={(e) => patch('name', e.target.value)} />
      </Field>

      <div className="space-y-4">
        <TableDrawField
          label="Reason for adventure"
          value={reasonBand}
          bandId={reasonBand}
          card={String(entity.reason_card || '') || undefined}
          cardBands={options.card_bands || []}
          preview={tablePreviews.reason}
          options={options.reasons}
          drawing={drawing === 'reason'}
          disabled={!characterId}
          onChange={(id) => onChange({ ...entity, reason_band: id, reason_card: '' })}
          onDraw={() => drawTable('reason')}
        />

        <TableDrawField
          label="Background"
          value={backgroundBand}
          bandId={backgroundBand}
          card={String(entity.background_card || '') || undefined}
          cardBands={options.card_bands || []}
          preview={tablePreviews.background}
          options={options.backgrounds}
          drawing={drawing === 'background'}
          disabled={!characterId}
          onChange={(id) => onChange({ ...entity, background_band: id, background_card: '' })}
          onDraw={() => drawTable('background')}
        />

        <TableDrawField
          label="Trinket"
          value={trinketBand}
          bandId={trinketBand}
          card={String(entity.trinket_card || '') || undefined}
          cardBands={options.card_bands || []}
          preview={tablePreviews.trinket}
          options={options.trinkets}
          drawing={drawing === 'trinket'}
          disabled={!characterId}
          onChange={(id) => onChange({ ...entity, trinket_band: id, trinket_card: '' })}
          onDraw={() => drawTable('trinket')}
        />
        <label className="flex items-center gap-2 text-xs text-muted cursor-pointer">
          <input
            type="checkbox"
            className="rounded border-border"
            checked={Boolean(entity.oracle_relic)}
            onChange={(e) => onChange({ ...entity, oracle_relic: e.target.checked })}
          />
          Oracle relic (from Hyhill) — required for Dragonkeep door
        </label>
      </div>

      <section className="rounded-lg border border-border p-4 space-y-3">
        <div className="flex items-start justify-between gap-4">
          <span className="label-text pt-0.5">Legacy</span>
          <button
            type="button"
            className="btn-ghost text-[11px] px-2.5 py-1.5 border border-border rounded-md inline-flex items-center gap-1 text-muted hover:text-accent shrink-0"
            disabled={drawing === 'legacy' || !characterId}
            onClick={rollLegacy}
          >
            {drawing === 'legacy' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Shuffle className="w-3 h-3" />}
            Roll d6
          </button>
        </div>
        <select
          className="select w-full"
          value={String(entity.legacy || '')}
          onChange={(e) => changeLegacy(e.target.value)}
          aria-label="Legacy"
        >
          <option value="">— Not set —</option>
          {options.legacies.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
        <p className="text-[11px] text-muted leading-relaxed">
          Rulebook order: resources from cards, then legacy modifiers.
        </p>
        {selectedLegacy?.boost && (
          <p className="text-xs">
            <span className="text-success">{selectedLegacy.boost}</span>
            <span className="text-muted"> · </span>
            <span className="text-red-400">{selectedLegacy.flaw}</span>
          </p>
        )}
      </section>

      {selectedLegacy && (selectedLegacy.abilities?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-border p-4 space-y-3">
          <div className="label-text">Daily abilities</div>
          {selectedLegacy.abilities!.map((ab) => (
            <div key={ab.id} className="text-xs">
              <span className="font-medium">{ab.label}</span>
              {ab.tags?.map((tag) => (
                <span
                  key={tag}
                  className={`ml-1.5 text-[10px] px-1 rounded ${
                    tag === 'combat' ? 'bg-red-900/40 text-red-300' : 'bg-success/15 text-success'
                  }`}
                >
                  {tag}
                </span>
              ))}
              <div className="text-muted mt-0.5">{ab.description}</div>
            </div>
          ))}
        </div>
      )}

      <section className="rounded-lg border border-border p-4 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="label-text">Resources (max 20 each)</div>
            <p className="text-[11px] text-muted leading-relaxed">
              Draw six cards (1–2 Health, 3–4 Morale, 5–6 Supplies). Ace = 11, J/Q/K = 10. Pair total ≤ 6 may take one
              bonus card.
            </p>
          </div>
          <button
            type="button"
            className="btn-ghost text-[11px] px-2.5 py-1.5 border border-border rounded-md inline-flex items-center gap-1 text-muted hover:text-accent shrink-0"
            disabled={Boolean(resourceBusy) || !characterId}
            onClick={drawResources}
          >
            {resourceBusy === 'draw' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Shuffle className="w-3 h-3" />}
            Draw 6
          </button>
        </div>

        {resourceDraft && (
          <div className="space-y-2">
            {resourceDraft.stats.map((row) => (
              <div key={row.stat} className="text-xs rounded-md border border-border bg-bg/40 p-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="capitalize font-medium">{row.stat}</span>
                  <span className="text-muted">
                    base {row.base}
                    {resourceDraft.final_stats && (
                      <span className="text-gray-300"> → {resourceDraft.final_stats[row.stat]}</span>
                    )}
                  </span>
                </div>
                <div className="text-muted mt-1">
                  {row.cards.map((card, i) => (
                    <span key={`${card}-${i}`}>
                      {i > 0 ? ', ' : ''}
                      {card} ({row.card_values[i] ?? '?'})
                    </span>
                  ))}
                </div>
                {row.needs_bonus && (
                  <button
                    type="button"
                    className="mt-1.5 text-[11px] text-accent hover:underline"
                    disabled={resourceBusy === row.stat}
                    onClick={() => drawResourceBonus(row.stat)}
                  >
                    {resourceBusy === row.stat ? 'Drawing bonus…' : 'Low roll — draw bonus card'}
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              className="btn-primary text-xs w-full"
              disabled={Boolean(resourceBusy)}
              onClick={applyResources}
            >
              {resourceBusy === 'apply' ? 'Applying…' : 'Apply resources to character'}
            </button>
          </div>
        )}

        {hasResourceBases(entity) && !resourceDraft && (
          <div className="text-[11px] text-muted space-y-1">
            {(['health', 'morale', 'supplies'] as const).map((k) => {
              const cards = (entity.resource_cards as Record<string, string[]> | undefined)?.[k] || [];
              if (!cards.length) return null;
              return (
                <div key={k}>
                  <span className="capitalize">{k}</span>: {cards.join(', ')} (base{' '}
                  {Number(entity[`resource_base_${k}`] ?? 0)})
                </div>
              );
            })}
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          {(['health', 'morale', 'supplies'] as const).map((k) => (
            <div key={k}>
              <div className="text-xs text-muted capitalize mb-1">{k}</div>
              <input
                type="number"
                min={0}
                max={20}
                className="input"
                aria-label={k}
                value={Number(entity[k] ?? 10)}
                onChange={(e) => patch(k, Number(e.target.value))}
              />
            </div>
          ))}
        </div>
      </section>

      <Field label="Active adventure" className="space-y-2">
        <select
          className="select w-full"
          value={String(entity.active_adventure || '')}
          onChange={(e) => patch('active_adventure', e.target.value)}
          aria-label="Active adventure"
        >
          {adventureOptions.map((o) => (
            <option key={o.id || 'empty'} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      </Field>

      {reasonBand && reasonPreview && (
        <details className="rounded-lg border border-border p-3">
          <summary className="cursor-pointer text-xs text-muted">Reason ending preview (p. 36)</summary>
          <div className="chat-markdown mt-2 text-xs">
            <ReactMarkdown>{reasonPreview}</ReactMarkdown>
          </div>
        </details>
      )}

      <Field label="Journal notes">
        <TextArea
          className="min-h-[80px]"
          placeholder="Journal notes"
          value={String(entity.notes || '')}
          onChange={(e) => patch('notes', e.target.value)}
        />
      </Field>

      {error && <p className="text-red-400 text-xs">{error}</p>}

      <button type="button" className="btn-primary" disabled={saving} onClick={save}>
        {saving ? 'Saving…' : characterId ? 'Save character' : 'Create character'}
      </button>
    </div>
  );
}
