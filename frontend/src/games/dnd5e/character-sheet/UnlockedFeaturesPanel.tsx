import type { ReactNode } from 'react';
import { displayLabel } from '../../../lib/displayText';
import GlossaryTip from '../../../components/ui/GlossaryTip';

export type UnlockedFeatures = {
  class_features?: Record<string, string[]>;
  subclass_features?: Record<string, string[]>;
  species_traits?: Array<{
    id: string;
    label: string;
    detail?: string;
    display: string;
    automatic?: boolean;
  }>;
  origin_feat_effects?: Array<{ feat_id: string; feat: string; effect: string }>;
  resolved_choices?: Array<{ id: string; label: string; value_label: string }>;
};

function FeatureSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-1.5">
      <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted">{title}</h4>
      {children}
    </section>
  );
}

export default function UnlockedFeaturesPanel({ features }: { features: UnlockedFeatures }) {
  const speciesTraits = features.species_traits || [];
  const originFeatEffects = features.origin_feat_effects || [];
  const classFeatures = Object.entries(features.class_features || {});
  const subclassFeatures = Object.entries(features.subclass_features || {});
  const resolvedChoices = features.resolved_choices || [];

  const hasOriginColumn = speciesTraits.length > 0 || originFeatEffects.length > 0;
  const hasClassColumn = classFeatures.length > 0 || subclassFeatures.length > 0 || resolvedChoices.length > 0;

  if (!hasOriginColumn && !hasClassColumn) return null;

  return (
    <div className="panel p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-accent mb-4">Unlocked features</h3>
      <div
        className={`grid gap-x-8 gap-y-4 text-sm ${
          hasOriginColumn && hasClassColumn ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'
        }`}
      >
        {hasOriginColumn && (
          <div className="space-y-4">
            {speciesTraits.length > 0 && (
              <FeatureSection title="Species traits">
                <ul className="space-y-1">
                  {speciesTraits.map((row) => (
                    <li key={row.id} className="text-gray-200 leading-snug">
                      {row.display}
                    </li>
                  ))}
                </ul>
              </FeatureSection>
            )}
            {originFeatEffects.length > 0 && (
              <FeatureSection title="Origin feat effects">
                <ul className="space-y-1">
                  {originFeatEffects.map((row) => (
                    <li key={`${row.feat_id}-${row.effect}`} className="text-gray-200 leading-snug">
                      <GlossaryTip name={row.feat} variant="inline" />: {row.effect}
                    </li>
                  ))}
                </ul>
              </FeatureSection>
            )}
          </div>
        )}

        {hasClassColumn && (
          <div className="space-y-4">
            {classFeatures.map(([cid, feats]) => (
              <FeatureSection key={cid} title={displayLabel(cid)}>
                <div className="flex flex-wrap gap-1.5">
                  {(feats as string[]).map((f) => (
                    <GlossaryTip key={f} name={f} />
                  ))}
                </div>
              </FeatureSection>
            ))}
            {subclassFeatures.map(([key, feats]) => (
              <FeatureSection key={key} title={displayLabel(key)}>
                <div className="flex flex-wrap gap-1.5">
                  {(feats as string[]).map((f) => (
                    <GlossaryTip key={f} name={f} />
                  ))}
                </div>
              </FeatureSection>
            ))}
            {resolvedChoices.length > 0 && (
              <FeatureSection title="Class choices">
                <dl className="space-y-2">
                  {resolvedChoices.map((row) => (
                    <div key={row.id}>
                      <dt className="text-muted text-xs">{row.label}</dt>
                      <dd className="text-gray-200 mt-0.5">{row.value_label}</dd>
                    </div>
                  ))}
                </dl>
              </FeatureSection>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
