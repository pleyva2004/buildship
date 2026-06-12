import { useCallback, useState } from 'react'
import Welcome from './components/Welcome.jsx'
import ChatView from './components/ChatView.jsx'
import MemoryRail from './components/MemoryRail.jsx'
import GeneratingOverlay from './components/GeneratingOverlay.jsx'
import TourView from './components/TourView.jsx'
import { respond } from './mock/brain.js'
import { SPECS } from './mock/data.js'

// The spine (design 05, reconciled with the five-act flow):
//   WELCOME ─► CHAT (thread + memory rail + inline cards + taste card)
//                 └─ generate ─► [GENERATING overlay ~8s] ─► TOUR
// One page, view states, no router. Swap point for the live backend: replace
// respond() with POST /api/chat — the shape is identical (design 04 §5).
export default function App() {
  const [view, setView] = useState('welcome') // welcome | chat | tour
  const [generating, setGenerating] = useState(false)
  const [profileId, setProfileId] = useState('jake_v1')
  const [messages, setMessages] = useState([])
  const [recalledIds, setRecalledIds] = useState([])

  const sendMessage = useCallback((text) => {
    const turn = respond(text)
    setMessages((prev) => [
      ...prev,
      { role: 'user', text },
      { role: 'agent', text: turn.reply, action: turn.action?.type === 'recommend' ? turn.action : null },
    ])
    setRecalledIds(turn.recalled)
    if (turn.action?.type === 'generate_tour') setGenerating(true)
  }, [])

  const start = useCallback((text) => {
    setView('chat')
    sendMessage(text)
  }, [sendMessage])

  const onTourReady = useCallback(() => {
    setGenerating(false)
    setView('tour')
  }, [])

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">VISTA</span>
        <div className="profile-switch">
          {Object.values(SPECS).map((s) => (
            <button
              key={s.profile_id}
              className={s.profile_id === profileId ? 'active' : ''}
              onClick={() => setProfileId(s.profile_id)}
            >
              {s.name}
            </button>
          ))}
        </div>
      </header>

      {view === 'welcome' && <Welcome onStart={start} />}

      {view === 'chat' && (
        <div className="main">
          <ChatView
            messages={messages}
            profileId={profileId}
            onSend={sendMessage}
            onGenerate={() => setGenerating(true)}
          />
          <MemoryRail profileId={profileId} recalledIds={recalledIds} />
        </div>
      )}

      {view === 'tour' && (
        <div className="main">
          <TourView profileId={profileId} onBack={() => setView('chat')} />
          <MemoryRail profileId={profileId} recalledIds={[]} />
        </div>
      )}

      {generating && <GeneratingOverlay profileId={profileId} onDone={onTourReady} />}
    </div>
  )
}
