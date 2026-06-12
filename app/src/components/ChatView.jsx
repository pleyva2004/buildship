import { useEffect, useRef, useState } from 'react'
import ListingCards from './ListingCards.jsx'

// Act 2 — the conversation column. Messages may carry an inline card payload
// (action.recommend) so discovery happens INSIDE the conversation.
export default function ChatView({ messages, profileId, thinking, onSend, onGenerate }) {
  const [draft, setDraft] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  return (
    <div className="chat-col">
      <div className="thread">
        {messages.map((m, i) => (
          <div key={i}>
            <div className={`bubble ${m.role}`}>{m.text}</div>
            {m.action?.type === 'recommend' && (
              <ListingCards
                listingIds={m.action.listing_ids}
                profileId={profileId}
                onGenerate={onGenerate}
              />
            )}
          </div>
        ))}
        {thinking && <div className="bubble agent thinking">…</div>}
        <div ref={endRef} />
      </div>
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
          placeholder="Reply to VISTA…"
        />
        <button className="cta" type="submit">Send</button>
      </form>
    </div>
  )
}
