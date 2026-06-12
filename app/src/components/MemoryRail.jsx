import { MEMORIES, MEMORY_CATEGORIES, SPECS } from '../mock/data.js'

// The "knows you" proof — present from Act 2 onward, sacred (design 05).
// Facts recalled THIS turn pulse. The taste card renders the locked style spec
// as a designed object, not JSON (Act 3 lives here).
export default function MemoryRail({ profileId, recalledIds }) {
  const memories = MEMORIES[profileId] ?? []
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

      {MEMORY_CATEGORIES.map((cat) => {
        const items = memories.filter((m) => m.category === cat)
        if (!items.length) return null
        return (
          <div className="cat" key={cat}>
            <h3>{cat}</h3>
            {items.map((m) => (
              <div key={m.id} className={'mem' + (recalledIds.includes(m.id) ? ' recalled' : '')}>
                {m.text}
              </div>
            ))}
          </div>
        )
      })}
    </aside>
  )
}
