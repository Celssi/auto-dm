import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';
import { stackLabel } from './characterSheetPdfShapes';

export function createHeaderField(pdf: PdfModule) {
  const { Text, View } = pdf;

  return function HeaderField({ label, value, flex = 1 }: { label: string; value: string; flex?: number }) {
    return (
      <View style={{ flex, paddingHorizontal: 3, paddingVertical: 2, borderRight: '0.5pt solid #999', minWidth: 0 }}>
        <Text style={s.label}>{stackLabel(label)}</Text>
        <Text style={[s.value, { fontFamily: value.length > 18 ? 'Helvetica' : 'Helvetica-Bold' }]}>{value || ' '}</Text>
      </View>
    );
  };
}
