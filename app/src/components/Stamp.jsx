// Provenance stamps (design 11 §design-language) — the one small reusable
// system the split rests on. Wherever a you-fact and a world-fact could be
// mistaken for each other (rail, card, narration), these two draw the line:
// "you" = warm sans, clay wash · "researched" = mono, hollow outline, compass.

export const CompassIcon = (props) => (
  <svg viewBox="0 0 24 24" {...props}>
    <path d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM16.2 7.8l-2 5.4-5.4 2 2-5.4 5.4-2z" />
  </svg>
)

export const UserIcon = (props) => (
  <svg viewBox="0 0 24 24" {...props}>
    <path d="M20 21a8 8 0 0 0-16 0M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
  </svg>
)

export default function Stamp({ kind }) {
  if (kind === 'you')
    return (
      <span className="stamp you"><UserIcon />from your interview</span>
    )
  return (
    <span className="stamp"><CompassIcon />VISTA researched</span>
  )
}
