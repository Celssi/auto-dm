import type { PdfModule } from './characterSheetPdfTypes';

export function createPdfShapes(pdf: PdfModule) {
  const { View } = pdf;

  function CirclePip({ filled, size = 5 }: { filled: boolean; size?: number }) {
    return (
      <View
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          border: '0.75pt solid #000',
          backgroundColor: filled ? '#000' : '#fff',
        }}
      />
    );
  }

  function DiamondPip({ filled, size = 6 }: { filled: boolean; size?: number }) {
    return (
      <View
        style={{
          width: size,
          height: size,
          border: '0.75pt solid #000',
          backgroundColor: filled ? '#000' : '#fff',
        }}
      />
    );
  }

  function PipRow({
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
  }

  return { CirclePip, DiamondPip, PipRow };
}

/** Stack long header labels on two lines to avoid awkward hyphenation. */
export function stackLabel(label: string): string {
  if (label.includes(' & ')) {
    return label.replace(' & ', '\n& ');
  }
  const words = label.split(' ');
  if (words.length === 2) return words.join('\n');
  if (words.length > 2) {
    const mid = Math.ceil(words.length / 2);
    return `${words.slice(0, mid).join(' ')}\n${words.slice(mid).join(' ')}`;
  }
  return label;
}
