import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';

export function createHeaderField(pdf: PdfModule) {
  const { Text, View } = pdf;

  return function HeaderField({ label, value, flex = 1 }: { label: string; value: string; flex?: number }) {
    return (
      <View style={{ flex, paddingHorizontal: 4, paddingVertical: 3, borderRight: '0.5pt solid #ccc' }}>
        <Text style={s.label}>{label}</Text>
        <Text style={s.value}>{value || ' '}</Text>
      </View>
    );
  };
}
