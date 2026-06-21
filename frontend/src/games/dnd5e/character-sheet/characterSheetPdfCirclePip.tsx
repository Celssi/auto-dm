import type { PdfModule } from './characterSheetPdfTypes';

export function createCirclePip(pdf: PdfModule) {
  const { View } = pdf;

  return function CirclePip({ filled, size = 5 }: { filled: boolean; size?: number }) {
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
  };
}
