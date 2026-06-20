import type { PdfModule } from './characterSheetPdfTypes';
import { createCirclePip } from './characterSheetPdfCirclePip';
import { createDiamondPip } from './characterSheetPdfDiamondPip';

export function createPipRow(pdf: PdfModule) {
  const { View } = pdf;
  const CirclePip = createCirclePip(pdf);
  const DiamondPip = createDiamondPip(pdf);

  return function PipRow({
    count,
    filled,
    shape = 'circle',
    gap = 3,
  }: {
    count: number;
    filled: number;
    shape?: 'circle' | 'diamond';
    gap?: number;
  }) {
    const Pip = shape === 'diamond' ? DiamondPip : CirclePip;
    return (
      <View style={{ flexDirection: 'row', gap, marginTop: 2, alignItems: 'center' }}>
        {Array.from({ length: count }).map((_, i) => (
          <Pip key={i} filled={i < filled} />
        ))}
      </View>
    );
  };
}
