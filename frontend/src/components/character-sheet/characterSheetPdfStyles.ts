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

/** Official 2024 sheet uses compact type on a light gray page. */
export const pdfStyles = {
  page: {
    backgroundColor: '#d4d4d4',
    paddingTop: 8,
    paddingBottom: 18,
    paddingHorizontal: 10,
    fontFamily: 'Helvetica',
    fontSize: 8,
    color: '#111',
  },
  box: {
    border: '1pt solid #000',
    backgroundColor: '#fff',
  },
  label: {
    fontSize: 6,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.35,
    color: '#222',
    fontFamily: 'Helvetica-Bold',
    lineHeight: 1.15,
  },
  labelSm: {
    fontSize: 6,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.25,
    color: '#333',
    lineHeight: 1.15,
  },
  value: {
    fontSize: 9,
    marginTop: 2,
    lineHeight: 1.2,
  },
  valueLg: {
    fontSize: 11,
    fontFamily: 'Helvetica-Bold',
    lineHeight: 1.1,
  },
  gridBg: {
    backgroundColor: '#ececec',
  },
  row: { flexDirection: 'row' as const },
  col: { flexDirection: 'column' as const },
  center: { alignItems: 'center' as const, justifyContent: 'center' as const },
  skillRow: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    marginTop: 0.5,
    paddingLeft: 1,
    gap: 3,
  },
  skillText: { fontSize: 7, flex: 1, lineHeight: 1.15 },
  skillMod: { fontSize: 7, fontFamily: 'Helvetica-Bold', width: 14, textAlign: 'right' as const },
  modCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    border: '1.25pt solid #000',
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    marginVertical: 1,
  },
  modText: { fontSize: 10, fontFamily: 'Helvetica-Bold' },
  scoreBox: {
    border: '1pt solid #000',
    width: 20,
    paddingVertical: 1,
    alignItems: 'center' as const,
  },
  shield: {
    border: '1.5pt solid #000',
    width: 30,
    height: 34,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    paddingTop: 2,
  },
  tableHeader: {
    flexDirection: 'row' as const,
    borderBottom: '1pt solid #000',
    backgroundColor: '#ececec',
    paddingVertical: 2,
    paddingHorizontal: 3,
  },
  tableRow: {
    flexDirection: 'row' as const,
    borderBottom: '0.5pt solid #ccc',
    paddingVertical: 1.5,
    paddingHorizontal: 3,
    minHeight: 10,
  },
  tableCell: { fontSize: 7.5, lineHeight: 1.15 },
  footer: {
    position: 'absolute' as const,
    bottom: 6,
    right: 10,
    fontSize: 6,
    color: '#555',
  },
};
