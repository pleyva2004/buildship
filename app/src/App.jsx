import { useCallback, useEffect, useState } from 'react'
import Welcome from './components/Welcome.jsx'
import ChatView from './components/ChatView.jsx'
import MemoryRail from './components/MemoryRail.jsx'
import GeneratingOverlay from './components/GeneratingOverlay.jsx'
import TourView from './components/TourView.jsx'
import { chat, getContext } from './api.js'
import { SPECS } from './mock/data.js'

// The spine: WELCOME ─► CHAT ─► [GENERATING ~8s] ─► TOUR. One page, view
// states, no router. Backend: FastAPI bridge via api.js, mock fallback baked in.
export default function App() {
  const [view, setView] = useState('welcome') // welcome | chat | tour
  const [generating, setGenerating] = useState(false)
  const [profileId, setProfileId] = useState('jake_v1')
  const [messages, setMessages] = useState([])
  const [memories, setMemories] = useState([])
  const [recalledIds, setRecalledIds] = useState([])
  const [thinking, setThinking] = useState(false)

  // Memory rail loads from the live agent (mock fallback inside api.js).
  useEffect(() => {
    getContext(profileId).then(setMemories)
  }, [profileId])

  const sendMessage = useCallback(async (text) => {
    setMessages((prev) => [...prev, { role: 'user', text }])
    setThinking(true)
    try {
      const turn = await chat(profileId, text)
      setMessages((prev) => [
        ...prev,
        {
          role: 'agent',
          text: turn.reply,
          action: turn.action?.type === 'recommend' ? turn.action : null,
        },
      ])
      setRecalledIds((turn.recalled ?? []).map((m) => m.id))
      if (turn.action?.type === 'generate_tour') setGenerating(true)
    } finally {
      setThinking(false)
    }
  }, [profileId])

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
            thinking={thinking}
            onSend={sendMessage}
            onGenerate={() => setGenerating(true)}
          />
          <MemoryRail profileId={profileId} memories={memories} recalledIds={recalledIds} />
        </div>
      )}

      {view === 'tour' && (
        <div className="main">
          <TourView profileId={profileId} onBack={() => setView('chat')} />
          <MemoryRail profileId={profileId} memories={memories} recalledIds={[]} />
        </div>
      )}

      {generating && <GeneratingOverlay profileId={profileId} onDone={onTourReady} />}
    </div>
  )
}
