import { useEffect, useMemo, useRef, useState } from 'react'
import CuratedSet from './CuratedSet.jsx'
import { REFINES } from '../mock/discovery.js'
import { LISTINGS } from '../mock/data.js'

// Narrated loading (design 08 voice): say what VISTA is doing, never a bare
// "…" — and keep it MOVING: the label advances through a contextual sequence
// so a long turn reads as progress, not a hang.
function thinkingSequence(messages) {
  const last = [...messages].reverse().find((m) => m.role === 'user')?.text?.toLowerCase() ?? ''
  const hood = LISTINGS.map((l) => l.neighborhood).find((h) => h && last.includes(h.toLowerCase()))
  if (hood) return [
    `Researching ${hood}…`,
    'Reading what locals say…',
    'Cross-checking your must-haves…',
    'Pulling it together…',
  ]
  if (/show me|my version|my style/.test(last)) return [
    'Composing your tour…',
    'Restyling each room to your taste…',
    'Setting the light…',
    'Almost there…',
  ]
  if (/find|recommend|home|house/.test(last)) return [
    'Matching against what I know about you…',
    'Weighing light, walkability, the yard…',
    'Ranking what fits best…',
    'Pulling it together…',
  ]
  return [
    'Thinking it through…',
    'Checking it against your profile…',
    'Pulling it together…',
  ]
}

function ThinkingBubble({ messages }) {
  const [seq] = useState(() => thinkingSequence(messages)) // freeze on mount
  const [step, setStep] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, seq.length - 1)), 2400)
    return () => clearInterval(t)
  }, [seq])
  return (
    <div className="bubble agent thinking">
      <span key={step} className="think-label">{seq[step]}</span>
      <span className="thinkdots"><span /><span /><span /></span>
    </div>
  )
}

// Act 2 — the conversation column, now the discovery surface (design 10):
// curated sets render inline as VISTA's responses; reactions and refine chips
// re-rank live, ALWAYS narrated (sparkle bubbles). Only the latest set is live;
// earlier ones collapse to "updated below" (prototype behavior).
export default function ChatView({
  messages, profileId, thinking, discovery, onSend,
  onRefine, onDismiss, onSaveListing, onMoreListings, onOpenListing, onGenerate,
}) {
  const [draft, setDraft] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const lastSetIdx = messages.reduce((acc, m, i) => (m.set ? i : acc), -1)
  const hasSet = lastSetIdx !== -1

  return (
    <div className="chat-col">
      <div className="thread">
        {messages.map((m, i) => (
          <div key={i}>
            {m.role === 'narrate' ? (
              <div className="bubble narrate">{m.researchDone ? '✓' : '✦'} <span dangerouslySetInnerHTML={{
                __html: m.text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'),
              }} /></div>
            ) : (
              m.text && <div className={`bubble ${m.role}`}>{m.text}</div>
            )}
            {m.trace?.length > 0 && (
              <div className="turn-trace">✦ {m.trace.join(' · ')}</div>
            )}
            {m.newFacts?.length > 0 && (
              <div className="saved-facts">
                {m.newFacts.map((f) => (
                  <span className="saved-fact" key={f.text}>✓ Saved to memory — {f.text}</span>
                ))}
              </div>
            )}
            {m.set && (i === lastSetIdx ? (
              <CuratedSet
                set={discovery.set}
                saved={discovery.saved}
                onSave={onSaveListing}
                onDismiss={onDismiss}
                onMore={onMoreListings}
                onOpen={onOpenListing}
                onGenerate={onGenerate}
              />
            ) : (
              <p className="setintro stale">↑ updated below</p>
            ))}
          </div>
        ))}
        {thinking && <ThinkingBubble messages={messages} />}
        <div ref={endRef} />
      </div>

      {hasSet && (
        <div className="refchips">
          {REFINES.map((r) => (
            <button key={r.id} onClick={() => onRefine(r)}>{r.label}</button>
          ))}
        </div>
      )}
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault()
          if (!draft.trim()) return
          onSend(draft.trim())
          setDraft('')
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={hasSet ? '“somewhere quieter, closer to a park” — or react to a home above' : 'Reply to VISTA…'}
        />
        <button className="cta" type="submit">Send</button>
      </form>
    </div>
  )
}
