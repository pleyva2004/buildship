import { useEffect, useState } from 'react'
import { SPECS } from '../mock/data.js'
import { rawPhoto } from '../assets.js'

// Act 5 opener — the ~8s cinematic loading moment. Pure theater by design
// (CLAUDE.md §2.1). Design 08 (07) refinements: stages narrate with the
// user's ACTUAL spec words, and the real room blooms from dim original to
// warm/bright as stages progress — loading becomes a preview of the payoff.
const TOTAL_MS = 8000

const stagesFor = (spec) => [
  'Reading the architecture…',
  `Bringing in ${spec.materials[0]} and ${spec.materials[2]}…`,
  `Tuning the light: ${spec.lighting_mood}…`,
  `Composing your ${spec.aesthetic_name} tour…`,
]

export default function GeneratingOverlay({ profileId, onDone }) {
  const [stageIdx, setStageIdx] = useState(0)
  const [photoFailed, setPhotoFailed] = useState(false)
  const spec = SPECS[profileId]
  const stages = stagesFor(spec)

  useEffect(() => {
    const per = TOTAL_MS / stages.length
    const tick = setInterval(() => setStageIdx((i) => Math.min(i + 1, stages.length - 1)), per)
    const done = setTimeout(onDone, TOTAL_MS)
    return () => { clearInterval(tick); clearTimeout(done) }
  }, [onDone, stages.length])

  const progress = stageIdx / (stages.length - 1) // 0 → 1 across the stages

  return (
    <div className="generating">
      {!photoFailed && (
        <div className="bloom-wrap">
          <img
            src={rawPhoto('living')}
            alt=""
            aria-hidden
            onError={() => setPhotoFailed(true)}
            style={{
              filter: `brightness(${0.45 + progress * 0.55}) saturate(${0.5 + progress * 0.5})`,
            }}
          />
          <div
            className="bloom-tint"
            style={{ background: spec.palette_hex[0], opacity: progress * 0.22 }}
          />
        </div>
      )}
      <div className="dots">
        {spec.palette_hex.map((hex) => (
          <div key={hex} className="dot" style={{ background: hex }} />
        ))}
      </div>
      <div className="stage-line">{stages[stageIdx]}</div>
    </div>
  )
}
