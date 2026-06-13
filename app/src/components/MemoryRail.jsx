import { useState } from 'react'
import { LISTINGS, SPECS } from '../mock/data.js'
import { FEATURES, START_WEIGHTS, WEIGHT_CAP } from '../mock/discovery.js'
import { applyNudges } from './TasteProfileView.jsx'
import Stamp, { CompassIcon, UserIcon } from './Stamp.jsx'
import { AREA_INTEL, liveAreaNotes } from '../mock/areas.js'

// The "knows you" proof — sacred (design 05). Renders whatever memories the
// API (or mock fallback) provides; facts recalled THIS turn pulse, facts
// learned THIS session animate in. Design 08 (03) refinements: stated/inferred
// provenance marks, confirm/edit/remove hygiene, and a readiness indicator so
// the chat has a finish line. Design 11: two tabs — what's about YOU vs what
// VISTA researched about the AREA — so city facts never wear Jake's framing.

const GROUPS = [
  { label: 'Life', match: (m) => m.category === 'life_situation' && !m.text.startsWith('Must-have') },
  { label: 'Taste', match: (m) => ['taste', 'materials'].includes(m.category) },
  { label: 'Inspiration', match: (m) => m.category === 'mood_board' },
  { label: 'Must-haves', match: (m) => m.category === 'life_situation' && m.text.startsWith('Must-have') },
  // open lane — anything off-taxonomy (category 'other' etc.) still shows
  { label: 'More', match: (m) => !['life_situation', 'taste', 'materials', 'mood_board', 'constraint', 'area_research'].includes(m.category) },
  // 'constraint' is intentionally not rendered — render rules, not user context
  // 'area_research' lives in The area tab — world facts, not Jake facts
]

// The area tab's notes: live research findings (area_research memories) take
// over per hood as they land; canned intel (mock twin of agent/mocks/areas.json)
// is the baseline "wider reading" so the tab is never empty on stage.
function buildAreaNotes(memories, inPlayHoods) {
  const live = liveAreaNotes(memories)
  // in-play hoods first (Set preserves insertion order), then the wider reading
  const hoods = [...new Set([...inPlayHoods, ...live.keys(), ...Object.keys(AREA_INTEL)])]
  return hoods
    .map((hood) => ({
      hood,
      notes: live.get(hood)?.notes ?? (AREA_INTEL[hood] ? [AREA_INTEL[hood]] : []),
      fresh: live.get(hood)?.fresh ?? false,
      inPlay: inPlayHoods.includes(hood),
    }))
    .filter((n) => n.notes.length)
}

const PROVENANCE_LABEL = { stated: 'you said', inferred: 'inferred', imported: 'imported', researched: 'researched' }
// live memories (mem0_client._norm) carry `source`; mocks carry `provenance`
const provOf = (m) => m.provenance ?? m.source ?? 'stated'

function RailTabs({ tab, setTab, count }) {
  return (
    <div className="railtabs">
      <button className={tab === 'you' ? 'on' : ''} onClick={() => setTab('you')}>
        <UserIcon />You
      </button>
      <button className={tab === 'area' ? 'on' : ''} onClick={() => setTab('area')}>
        <CompassIcon />The area<span className="cnt">{count}</span>
      </button>
    </div>
  )
}

// what VISTA still needs before matching feels honest (design 08 (03))
const READINESS = [
  { label: 'budget', has: (ms) => ms.some((m) => /budget|\d{3}k/i.test(m.text)) },
  { label: 'area', has: (ms) => ms.some((m) => /austin|neighborhood|walkable heart|relocating/i.test(m.text)) },
  { label: 'a must-have', has: (ms) => ms.some((m) => /^Must-have|^Deal-breaker/i.test(m.text)) },
  { label: 'a taste cue', has: (ms) => ms.some((m) => m.category === 'taste' || m.category === 'mood_board') },
]

export default function MemoryRail({ profileId, spec: specOverride, weights, savedIds = [], memories, recalledIds, nudges, inPlayHoods = [], onEdit, onRemove, onConfirm, onOpenTaste }) {
  const spec = applyNudges(specOverride ?? SPECS[profileId], nudges ?? { warmth: 0, ornate: 0, light: 0 })
  const [editingId, setEditingId] = useState(null)
  const [editText, setEditText] = useState('')
  const [tab, setTab] = useState('you')

  const missing = READINESS.filter((r) => !r.has(memories))
  const startW = START_WEIGHTS[profileId] ?? START_WEIGHTS.guest_v1
  const weightRows = weights
    ? Object.keys(weights).sort((a, b) => weights[b] - weights[a]).slice(0, 5)
    : []
  const areaNotes = buildAreaNotes(memories, inPlayHoods)

  if (tab === 'area') {
    return (
      <aside className="rail">
        <RailTabs tab={tab} setTab={setTab} count={areaNotes.length} />
        <div className="areapanel">
          <h2>What VISTA researched</h2>
          <p className="dsub">
            Neighborhood intel VISTA gathered out in the world.
          </p>
          {areaNotes.map((n) => (
            <div className={'anote' + (n.inPlay ? ' inset' : '') + (n.fresh ? ' fresh' : '')} key={n.hood}>
              <div className="ahood">
                <span className="hn">{n.hood}</span>
                <Stamp />
              </div>
              {n.inPlay && <div className="ins">In your current set</div>}
              {n.notes.map((t, i) => (
                <p className="at" key={i}>{t}</p>
              ))}
            </div>
          ))}
        </div>
      </aside>
    )
  }

  return (
    <aside className="rail">
      <RailTabs tab={tab} setTab={setTab} count={areaNotes.length} />
      {/* merged rail (design 10b §4): weights + saved sit ABOVE memories —
          a reaction moves a bar AND lands a memory chip, one story */}
      {weights && (
        <div className="rail-weights">
          <h2>What VISTA is weighting</h2>
          {weightRows.map((k) => (
            <div className="weight" key={k}>
              <div className="wtop">
                <span className="wname">
                  {FEATURES[k].label}
                  {weights[k] !== startW[k] && <em className="up"> ↑ raised</em>}
                </span>
                <span className="wval">{Math.round((weights[k] / WEIGHT_CAP) * 100)}%</span>
              </div>
              <div className="wbar"><i style={{ width: `${Math.round((weights[k] / WEIGHT_CAP) * 100)}%` }} /></div>
            </div>
          ))}
          {savedIds.length > 0 && (
            <div className="rail-saved">
              <h2>Saved</h2>
              {savedIds.map((id) => (
                <div className="saved-item" key={id}>♥ {LISTINGS.find((l) => l.listing_id === id)?.title}</div>
              ))}
            </div>
          )}
        </div>
      )}

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
                    <span className={`prov ${provOf(m)}`}>
                      {m.confirmed ? 'confirmed' : PROVENANCE_LABEL[provOf(m)] ?? 'you said'}
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
