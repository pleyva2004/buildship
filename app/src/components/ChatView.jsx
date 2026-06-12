import { useEffect, useRef, useState } from 'react'
import CuratedSet from './CuratedSet.jsx'
import { REFINES } from '../mock/discovery.js'

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
              <div className="bubble narrate">✦ <span dangerouslySetInnerHTML={{
                __html: m.text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'),
              }} /></div>
            ) : (
              m.text && <div className={`bubble ${m.role}`}>{m.text}</div>
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
        {thinking && <div className="bubble agent thinking">…</div>}
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
