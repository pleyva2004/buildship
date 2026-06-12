import { useRef, useState } from 'react'
import { PLACEHOLDER } from '../assets.js'

// The proof — original ⇄ restyled wipe. Sacred component (design 05): same
// windows, same walls, your decor. ~40 lines, no library, pointer events.
export default function CompareSlider({ original, restyled }) {
  const [pos, setPos] = useState(50)
  const ref = useRef(null)
  const dragging = useRef(false)

  const moveTo = (clientX) => {
    const rect = ref.current.getBoundingClientRect()
    setPos(Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100)))
  }

  return (
    <div
      className="compare"
      ref={ref}
      onPointerDown={(e) => {
        dragging.current = true
        e.currentTarget.setPointerCapture(e.pointerId)
        moveTo(e.clientX)
      }}
      onPointerMove={(e) => dragging.current && moveTo(e.clientX)}
      onPointerUp={() => { dragging.current = false }}
    >
      <img
        src={original}
        alt="Original room"
        onError={(e) => { e.currentTarget.src = PLACEHOLDER('original photo', 'left') }}
      />
      <img
        src={restyled}
        alt="Restyled room"
        style={{ clipPath: `inset(0 0 0 ${pos}%)` }}
        onError={(e) => { e.currentTarget.src = PLACEHOLDER('restyle landing soon', 'right') }}
      />
      <div className="divider" style={{ left: `${pos}%` }} />
      <div className="handle" style={{ left: `${pos}%` }}>⇆</div>
      <div className="tag left">Original</div>
      <div className="tag right">Your style</div>
    </div>
  )
}
