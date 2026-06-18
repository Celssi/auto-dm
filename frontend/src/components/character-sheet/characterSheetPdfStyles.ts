import { SKILLS } from './sheetConstants';

export const ABILITY_NAMES: Record<string, string> = {
  str: 'Strength',
  dex: 'Dexterity',
  con: 'Constitution',
  int: 'Intelligence',
  wis: 'Wisdom',
  cha: 'Charisma',
};

export const SKILLS_BY_ABILITY = SKILLS.reduce<Record<string, typeof SKILLS>>((acc, sk) => {
  (acc[sk.ability] ||= []).push(sk);
  return acc;
}, {});

export const pdfStyles = {
  page: {
    backgroundColor: '#e8e8e8',
    padding: 10,
    fontFamily: 'Helvetica',
    fontSize: 12,
    color: '#111',
  },
  box: {
    border: '1pt solid #000',
    backgroundColor: '#fff',
  },
  label: {
    fontSize: 12,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.4,
    color: '#222',
    fontFamily: 'Helvetica-Bold',
  },
  labelSm: {
    fontSize: 12,
    textTransform: 'uppercase' as const,
    color: '#333',
  },
  value: {
    fontSize: 12,
    marginTop: 1,
  },
  valueLg: {
    fontSize: 12,
    fontFamily: 'Helvetica-Bold',
  },
  gridBg: {
    backgroundColor: '#f4f4f4',
  },
  row: { flexDirection: 'row' as const },
  col: { flexDirection: 'column' as const },
  center: { alignItems: 'center' as const, justifyContent: 'center' as const },
  dot: { fontSize: 12, width: 8, textAlign: 'center' as const },
  modCircle: {
    width: 26,
    height: 26,
    borderRadius: 13,
    border: '1.5pt solid #000',
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    marginVertical: 2,
  },
  modText: { fontSize: 12, fontFamily: 'Helvetica-Bold' },
  scoreBox: {
    border: '1pt solid #000',
    width: 22,
    paddingVertical: 1,
    alignItems: 'center' as const,
  },
  shield: {
    border: '1.5pt solid #000',
    width: 34,
    height: 38,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    paddingTop: 4,
  },
  tableHeader: {
    flexDirection: 'row' as const,
    borderBottom: '1pt solid #000',
    backgroundColor: '#f0f0f0',
    paddingVertical: 2,
    paddingHorizontal: 3,
  },
  tableRow: {
    flexDirection: 'row' as const,
    borderBottom: '0.5pt solid #ccc',
    paddingVertical: 2,
    paddingHorizontal: 3,
    minHeight: 12,
  },
  footer: {
    position: 'absolute' as const,
    bottom: 8,
    right: 12,
    fontSize: 12,
    color: '#666',
  },
};
