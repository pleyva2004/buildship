import { SPECS } from '../mock/data.js'

// 04 · Taste Profile (design 08 §2) — promote the locked style_spec to a
// designed "taste passport": aesthetic name, palette, materials, furniture
// vocabulary, lighting mood. Nudge controls let the user co-author the spec
// BEFORE homes are found; provenance line keeps the memory story honest.

const NUDGES = [
  { key: 'warmth', low: 'Cooler', high: 'Warmer' },
  { key: 'ornate', low: 'Simpler', high: 'More ornate' },
  { key: 'light', low: 'Darker', high: 'Lighter' },
]

// pure hex adjustments so nudges visibly move the palette
function clamp(v) { return Math.max(0, Math.min(255, Math.round(v))) }
function adjustHex(hex, { warmth = 0, light = 0 }) {
  const n = parseInt(hex.slice(1), 16)
  let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255
  r = clamp(r + warmth * 14 + light * 12)
  g = clamp(g + warmth * 4 + light * 12)
  b = clamp(b - warmth * 14 + light * 12)
  return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')
}

const ORNATE_VOCAB = {
  jake_v1: ['fluted oak paneling', 'sculptural pendant'],
  pablo_v1: ['carved walnut detail', 'patterned kilim layers'],
}

export function applyNudges(spec, nudges) {
  const palette_hex = spec.palette_hex.map((h) => adjustHex(h, nudges))
  const furniture_vocabulary =
    nudges.ornate > 0
      ? [...spec.furniture_vocabulary, ...(ORNATE_VOCAB[spec.profile_id] ?? []).slice(0, nudges.ornate)]
      : nudges.ornate < 0
        ? spec.furniture_vocabulary.slice(0, Math.max(1, spec.furniture_vocabulary.length + nudges.ornate))
        : spec.furniture_vocabulary
  return { ...spec, palette_hex, furniture_vocabulary }
}

export default function TasteProfileView({ profileId, nudges, onNudge, onContinue, onBack }) {
  const base = SPECS[profileId]
  const spec = applyNudges(base, nudges)
  const nudged = nudges.warmth !== 0 || nudges.ornate !== 0 || nudges.light !== 0

  return (
    <div className="taste-view">
      <div className="passport">
        <button className="back" onClick={onBack}>← Back</button>
        <div className="passport-label">Taste passport</div>
        <h1>{spec.aesthetic_name}</h1>
        <p className="provenance">
          Built from your conversation + {base.provenance.mood_boards} mood boards
          {nudged && ' · nudged by you'}
        </p>

        <div className="passport-swatches">
          {spec.palette_hex.map((hex, i) => (
            <div key={i} className="passport-swatch" style={{ background: hex }} title={hex} />
          ))}
        </div>

        <div className="passport-section">
          <h3>Materials</h3>
          <div className="vocab">{spec.materials.map((m) => <span key={m} className="chip">{m}</span>)}</div>
        </div>

        <div className="passport-section">
          <h3>Furniture vocabulary</h3>
          <div className="vocab">{spec.furniture_vocabulary.map((f) => <span key={f} className="chip">{f}</span>)}</div>
        </div>

        <div className="passport-section">
          <h3>Light</h3>
          <p className="lighting serif">{spec.lighting_mood}</p>
        </div>

        <div className="passport-section">
          <h3>Nudge it</h3>
          <div className="nudges">
            {NUDGES.map(({ key, low, high }) => (
              <div className="nudge" key={key}>
                <button
                  className={nudges[key] < 0 ? 'active' : ''}
                  onClick={() => onNudge(key, nudges[key] < 0 ? 0 : -1)}
                >
                  {low}
                </button>
                <span className="nudge-dot" data-state={nudges[key]} />
                <button
                  className={nudges[key] > 0 ? 'active' : ''}
                  onClick={() => onNudge(key, nudges[key] > 0 ? 0 : 1)}
                >
                  {high}
                </button>
              </div>
            ))}
          </div>
        </div>

        <button className="cta wide" onClick={onContinue}>
          Find homes that fit
        </button>
      </div>
    </div>
  )
}
