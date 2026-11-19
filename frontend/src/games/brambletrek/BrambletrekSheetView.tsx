import type { BrambletrekCharacter } from '../../types';
import { EMPTY_FIELD } from '../../lib/displayText';
import { LabelWithTip } from '../../components/ui/HelpTip';
import { STAT_COLORS, brambletrekSummaryLine, statPercent } from './sheetUtils';

interface Props {
  character: BrambletrekCharacter;
  summary?: Record<string, unknown>;
}

function ResourceBar({ id, label, value }: { id: string; label: string; value: number }) {
  const pct = statPercent(value);
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <LabelWithTip id={id} label={label} className="text-xs text-muted" />
        <span className="text-sm font-semibold tabular-nums">{value}/20</span>
      </div>
      <div className="h-2 rounded-full bg-bg overflow-hidden border border-border">
        <div
          className="h-full transition-[width]"
          style={{ width: `${pct}%`, backgroundColor: STAT_COLORS[label.toLowerCase() as keyof typeof STAT_COLORS] }}
        />
      </div>
    </div>
  );
}

export default function BrambletrekSheetView({ character: c, summary }: Props) {
  const reason = String(summary?.reason || c.reason_band || EMPTY_FIELD);
  const background = String(summary?.background || c.background_band || EMPTY_FIELD);
  const trinket = String(summary?.trinket || c.trinket_band || EMPTY_FIELD);
  const legacy = String(summary?.legacy || c.legacy || EMPTY_FIELD);
  const adventure = String(c.active_adventure || EMPTY_FIELD);

  return (
    <div className="space-y-4">
      <section className="sheet-section">
        <h3 className="sheet-heading">
          <LabelWithTip id="gnawborn" label="Gnawborn" className="sheet-heading" />
        </h3>
        <p className="text-sm text-muted">{brambletrekSummaryLine(c, summary)}</p>
        <div className="grid gap-3 mt-4">
          <ResourceBar id="bt-health" label="Health" value={Number(c.health ?? 0)} />
          <ResourceBar id="bt-morale" label="Morale" value={Number(c.morale ?? 0)} />
          <ResourceBar id="bt-supplies" label="Supplies" value={Number(c.supplies ?? 0)} />
        </div>
      </section>
      <section className="sheet-section space-y-3 text-sm">
        <div>
          <div className="sheet-label">Reason for adventure</div>
          <p className="text-gray-200 mt-0.5">{reason}</p>
        </div>
        <div>
          <div className="sheet-label">Background</div>
          <p className="text-gray-200 mt-0.5">{background}</p>
        </div>
        <div>
          <div className="sheet-label">Trinket</div>
          <p className="text-gray-200 mt-0.5">{trinket}</p>
        </div>
        <div>
          <LabelWithTip id="bt-legacy" label="Legacy" className="sheet-label" />
          <p className="text-gray-200 mt-0.5">{legacy}</p>
        </div>
        <div>
          <div className="sheet-label">Active adventure</div>
          <p className="text-gray-200 mt-0.5">{adventure}</p>
        </div>
        {c.oracle_relic ? <p className="text-xs text-accent">Oracle relic: yes</p> : null}
        {c.notes ? (
          <div>
            <div className="sheet-label">Journal notes</div>
            <p className="text-gray-300 mt-0.5 whitespace-pre-wrap">{String(c.notes)}</p>
          </div>
        ) : null}
      </section>
    </div>
  );
}
