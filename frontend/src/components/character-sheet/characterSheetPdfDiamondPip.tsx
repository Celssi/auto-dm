import type { PdfModule } from './characterSheetPdfTypes';

export function createDiamondPip(pdf: PdfModule) {
  const { View } = pdf;

  return function DiamondPip({ filled, size = 6 }: { filled: boolean; size?: number }) {
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
  };
}
