import { useEffect, useState } from 'react'
import { SPECS } from '../mock/data.js'

// Act 5 opener — the ~8s cinematic loading moment. Pure theater by design
// (CLAUDE.md §2.1): narrated stages + the profile's actual palette breathing.
const STAGES = [
  'Reading the architecture…',
  'Recalling your taste…',
  'Applying your palette…',
  'Composing your tour…',
]
const TOTAL_MS = 8000

export default function GeneratingOverlay({ profileId, onDone }) {
  const [stageIdx, setStageIdx] = useState(0)
  const spec = SPECS[profileId]

  useEffect(() => {
    const per = TOTAL_MS / STAGES.length
    const tick = setInterval(() => setStageIdx((i) => Math.min(i + 1, STAGES.length - 1)), per)
    const done = setTimeout(onDone, TOTAL_MS)
    return () => { clearInterval(tick); clearTimeout(done) }
  }, [onDone])

  return (
    <div className="generating">
      <div className="dots">
        {spec.palette_hex.map((hex) => (
          <div key={hex} className="dot" style={{ background: hex }} />
        ))}
      </div>
      <div className="stage-line">{STAGES[stageIdx]}</div>
    </div>
  )
}
