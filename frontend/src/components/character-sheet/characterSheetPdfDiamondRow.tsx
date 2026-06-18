import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';

export function createDiamondRow(pdf: PdfModule) {
  const { Text, View } = pdf;

  return function DiamondRow({ count, filled }: { count: number; filled: number }) {
    return (
      <View style={[s.row, { gap: 2, marginTop: 2 }]}>
        {Array.from({ length: count }).map((_, i) => (
          <Text key={`diamond-${i}`} style={{ fontSize: 12, color: i < filled ? '#000' : '#bbb' }}>
            {i < filled ? '◆' : '◇'}
          </Text>
        ))}
      </View>
    );
  };
}
