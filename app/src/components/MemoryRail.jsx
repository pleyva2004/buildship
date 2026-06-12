import { useState } from 'react'
import { SPECS } from '../mock/data.js'
import { applyNudges } from './TasteProfileView.jsx'

// The "knows you" proof — sacred (design 05). Renders whatever memories the
// API (or mock fallback) provides; facts recalled THIS turn pulse, facts
// learned THIS session animate in. Design 08 (03) refinements: stated/inferred
// provenance marks, confirm/edit/remove hygiene, and a readiness indicator so
// the chat has a finish line.

const GROUPS = [
  { label: 'Life', match: (m) => m.category === 'life_situation' && !m.text.startsWith('Must-have') },
  { label: 'Taste', match: (m) => m.category === 'taste' },
  { label: 'Inspiration', match: (m) => m.category === 'mood_board' },
  { label: 'Must-haves', match: (m) => m.category === 'life_situation' && m.text.startsWith('Must-have') },
  // 'constraint' is intentionally not rendered — render rules, not user context
]

const PROVENANCE_LABEL = { stated: 'you said', inferred: 'inferred', imported: 'imported' }

// what VISTA still needs before matching feels honest (design 08 (03))
const READINESS = [
  { label: 'budget', has: (ms) => ms.some((m) => /budget|\d{3}k/i.test(m.text)) },
  { label: 'area', has: (ms) => ms.some((m) => /austin|neighborhood|walkable heart|relocating/i.test(m.text)) },
  { label: 'a must-have', has: (ms) => ms.some((m) => /^Must-have|^Deal-breaker/i.test(m.text)) },
  { label: 'a taste cue', has: (ms) => ms.some((m) => m.category === 'taste' || m.category === 'mood_board') },
]

export default function MemoryRail({ profileId, memories, recalledIds, nudges, onEdit, onRemove, onConfirm, onOpenTaste }) {
  const spec = applyNudges(SPECS[profileId], nudges ?? { warmth: 0, ornate: 0, light: 0 })
  const [editingId, setEditingId] = useState(null)
  const [editText, setEditText] = useState('')

  const missing = READINESS.filter((r) => !r.has(memories))

  return (
    <aside className="rail">
      <h2>What VISTA knows about {spec.name}</h2>

      <button className="taste-card as-button" onClick={onOpenTaste}>
        <div className="name serif">{spec.aesthetic_name}</div>
        <div className="swatches">
          {spec.palette_hex.map((hex, i) => (
            <div key={i} className="swatch" style={{ background: hex }} title={hex} />
          ))}
        </div>
        <div className="materials">{spec.materials.join(' · ')}</div>
        <div className="open-passport">Open taste passport →</div>
      </button>

      <div className={'readiness' + (missing.length ? '' : ' ready')}>
        {missing.length
          ? <>Still need: {missing.map((m) => m.label).join(' · ')}</>
          : <>✓ Budget · area · must-haves · taste — ready to match</>}
      </div>

      {GROUPS.map(({ label, match }) => {
        const items = memories.filter(match)
        if (!items.length) return null
        return (
          <div className="cat" key={label}>
            <h3>{label}</h3>
            {items.map((m) => (
              <div
                key={m.id}
                className={
                  'mem' +
                  (recalledIds.includes(m.id) ? ' recalled' : '') +
                  (m.fresh ? ' fresh' : '') +
                  (m.confirmed ? ' confirmed' : '')
                }
              >
                {editingId === m.id ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault()
                      onEdit(m.id, editText)
                      setEditingId(null)
                    }}
                  >
                    <input
                      autoFocus
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onBlur={() => setEditingId(null)}
                    />
                  </form>
                ) : (
                  <>
                    <span className="mem-text">{m.text.replace(/^Must-have:\s*/, '')}</span>
                    <span className={`prov ${m.provenance ?? 'stated'}`}>
                      {m.confirmed ? 'confirmed' : PROVENANCE_LABEL[m.provenance] ?? 'you said'}
                    </span>
                    <span className="mem-actions">
                      {!m.confirmed && (
                        <button title="Confirm — yes, that's me" onClick={() => onConfirm(m.id)}>✓</button>
                      )}
                      <button
                        title="Edit"
                        onClick={() => { setEditingId(m.id); setEditText(m.text) }}
                      >
                        ✎
                      </button>
                      <button title="Remove — not true" onClick={() => onRemove(m.id)}>✕</button>
                    </span>
                  </>
                )}
              </div>
            ))}
          </div>
        )
      })}
    </aside>
  )
}
