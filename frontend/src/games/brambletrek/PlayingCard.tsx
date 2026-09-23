interface ParsedCard {
  rank: string;
  suitSymbol: string;
  isRed: boolean;
}

function parseCard(card: string): ParsedCard {
  const lower = card.toLowerCase();
  let suitSymbol = '●';
  let isRed = false;

  if (/heart|♥/.test(lower)) {
    suitSymbol = '♥';
    isRed = true;
  } else if (/diamond|♦/.test(lower)) {
    suitSymbol = '♦';
    isRed = true;
  } else if (/spade|♠/.test(lower)) {
    suitSymbol = '♠';
  } else if (/club|♣/.test(lower)) {
    suitSymbol = '♣';
  }

  const rankMap: Record<string, string> = {
    ace: 'A',
    a: 'A',
    king: 'K',
    k: 'K',
    queen: 'Q',
    q: 'Q',
    jack: 'J',
    j: 'J',
  };
  const rankMatch = lower.match(/^(\d+|ace|king|queen|jack|[akqj])\b/);
  const raw = rankMatch?.[1] || card.split(/\s+/)[0] || '?';
  const rank = rankMap[raw] || raw.toUpperCase();

  return { rank, suitSymbol, isRed };
}

interface PlayingCardProps {
  card: string;
  applied?: boolean;
  active?: boolean;
  size?: 'sm' | 'md';
}

function CornerPip({
  rank,
  suitSymbol,
  color,
  inverted,
}: {
  rank: string;
  suitSymbol: string;
  color: string;
  inverted?: boolean;
}) {
  return (
    <div
      className={`absolute flex flex-col items-center leading-none select-none ${inverted ? 'bottom-1.5 right-1.5 rotate-180' : 'top-1.5 left-1.5'}`}
    >
      <span
        className="font-serif font-bold tabular-nums"
        style={{ color, fontSize: rank.length > 1 ? '0.65rem' : '0.75rem' }}
      >
        {rank}
      </span>
      <span style={{ color, fontSize: '0.75rem', marginTop: '1px' }}>{suitSymbol}</span>
    </div>
  );
}

export default function PlayingCard({ card, applied = false, active = false, size = 'md' }: PlayingCardProps) {
  const { rank, suitSymbol, isRed } = parseCard(card);
  const pipColor = isRed ? '#b91c1c' : '#171717';
  const dims = size === 'sm' ? 'w-11 h-[3.75rem]' : 'w-[3.5rem] h-[4.75rem]';

  return (
    <div
      className={`relative shrink-0 ${dims} rounded-[0.45rem] transition-all duration-200 ${applied ? 'opacity-75 scale-[0.97]' : ''} ${active ? 'scale-105' : ''}`}
      style={{
        boxShadow: active
          ? '0 0 0 2px rgba(212, 162, 76, 0.55), 0 6px 16px rgba(0,0,0,0.35)'
          : '0 1px 2px rgba(0,0,0,0.2), 0 4px 12px rgba(0,0,0,0.25)',
      }}
    >
      <div
        className="absolute inset-0 rounded-[0.45rem] overflow-hidden"
        style={{
          background: 'linear-gradient(145deg, #faf6ee 0%, #f0e8da 48%, #e6dcc8 100%)',
          border: '1px solid rgba(0,0,0,0.12)',
        }}
      >
        <div
          className="absolute inset-[3px] rounded-[0.3rem] pointer-events-none"
          style={{ border: '1px solid rgba(0,0,0,0.06)' }}
        />
        <CornerPip rank={rank} suitSymbol={suitSymbol} color={pipColor} />
        <CornerPip rank={rank} suitSymbol={suitSymbol} color={pipColor} inverted />
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span
            className="font-serif select-none"
            style={{
              color: pipColor,
              fontSize: size === 'sm' ? '1.35rem' : '1.65rem',
              opacity: 0.92,
              textShadow: '0 1px 0 rgba(255,255,255,0.4)',
            }}
          >
            {suitSymbol}
          </span>
        </div>
        {applied && <div className="absolute inset-0 bg-success/10 rounded-[0.45rem] pointer-events-none" />}
      </div>
    </div>
  );
}
