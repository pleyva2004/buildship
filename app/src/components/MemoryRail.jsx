import { SPECS } from '../mock/data.js'

// The "knows you" proof — sacred (design 05). Renders whatever memories the
// API (or mock fallback) provides; facts recalled THIS turn pulse. The taste
// card renders the locked style spec as a designed object, not JSON.

const GROUPS = [
  { label: 'Life', match: (m) => m.category === 'life_situation' && !m.text.startsWith('Must-have') },
  { label: 'Taste', match: (m) => m.category === 'taste' },
  { label: 'Inspiration', match: (m) => m.category === 'mood_board' },
  { label: 'Must-haves', match: (m) => m.category === 'life_situation' && m.text.startsWith('Must-have') },
  // 'constraint' is intentionally not rendered — render rules, not user context
]

export default function MemoryRail({ profileId, memories, recalledIds }) {
  const spec = SPECS[profileId]
  return (
    <aside className="rail">
      <h2>What VISTA knows about {spec.name}</h2>

      <div className="taste-card">
        <div className="name serif">{spec.aesthetic_name}</div>
        <div className="swatches">
          {spec.palette_hex.map((hex) => (
            <div key={hex} className="swatch" style={{ background: hex }} title={hex} />
          ))}
        </div>
        <div className="materials">{spec.materials.join(' · ')}</div>
      </div>

      {GROUPS.map(({ label, match }) => {
        const items = memories.filter(match)
        if (!items.length) return null
        return (
          <div className="cat" key={label}>
            <h3>{label}</h3>
            {items.map((m) => (
              <div key={m.id} className={'mem' + (recalledIds.includes(m.id) ? ' recalled' : '')}>
                {m.text.replace(/^Must-have:\s*/, '')}
              </div>
            ))}
          </div>
        )
      })}
    </aside>
  )
}
