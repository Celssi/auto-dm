import type { PdfModule } from './characterSheetPdfTypes';
import { pdfStyles as s } from './characterSheetPdfStyles';

type ViewStyle = NonNullable<React.ComponentProps<PdfModule['View']>['style']>;

export function createBox(pdf: PdfModule) {
  const { Text, View } = pdf;

  return function Box({
    children,
    style,
    title,
  }: {
    children: React.ReactNode;
    style?: ViewStyle;
    title?: string;
  }) {
    const boxStyle = (style ? [s.box, style] : [s.box]) as ViewStyle;
    return (
      <View style={boxStyle}>
        {title ? (
          <View style={{ borderBottom: '0.5pt solid #000', paddingHorizontal: 4, paddingVertical: 2 }}>
            <Text style={s.label}>{title}</Text>
          </View>
        ) : null}
        {children}
      </View>
    );
  };
}
