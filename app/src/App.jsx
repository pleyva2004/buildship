import { useCallback, useEffect, useRef, useState } from 'react'
import Welcome from './components/Welcome.jsx'
import InterviewView from './components/InterviewView.jsx'
import ChatView from './components/ChatView.jsx'
import MemoryRail from './components/MemoryRail.jsx'
import TasteProfileView from './components/TasteProfileView.jsx'
import ListingDetailView from './components/ListingDetailView.jsx'
import GeneratingOverlay from './components/GeneratingOverlay.jsx'
import TourView from './components/TourView.jsx'
import { chat, getContext, updateMemory, deleteMemory } from './api.js'
import { rankListings } from './mock/interview.js'
import { SPECS } from './mock/data.js'

// The spine (design 08): WELCOME ─► [GETTING TO KNOW YOU] ─► CHAT+RAIL ─►
// [TASTE PROFILE] ─► RECOMMENDATIONS (inline) ─► [LISTING DETAIL] ─►
// [GENERATING ~8s] ─► TOUR. One page, view states, no router. Backend:
// FastAPI bridge via api.js, mock fallback baked in.
const NO_NUDGES = { warmth: 0, ornate: 0, light: 0 }

// "Key: value" facts are singular — a new one supersedes the old value for
// that key (e.g. interview's "Household: partner + a dog" replaces the
// seeded household) — EXCEPT keys where many can coexist. Local-rail only;
// mem0 deletion stays a deliberate user action (✕).
const ACCUMULATIVE_KEYS = new Set(['must-have', 'deal-breaker', 'mood board'])
const factKey = (text) => {
  const i = text.indexOf(':')
  if (i <= 0) return null
  const key = text.slice(0, i).trim().toLowerCase()
  return ACCUMULATIVE_KEYS.has(key) ? null : key
}

export default function App() {
  const [view, setView] = useState('welcome') // welcome | interview | chat | taste | detail | tour
  const [generating, setGenerating] = useState(false)
  const [profileId, setProfileId] = useState('jake_v1')
  const [messages, setMessages] = useState([])
  const [memories, setMemories] = useState([])
  const [recalledIds, setRecalledIds] = useState([])
  const [thinking, setThinking] = useState(false)
  const [answers, setAnswers] = useState([]) // interview session state: [{questionId, answer}]
  const [rankOrder, setRankOrder] = useState(() => rankListings([]).map((r) => r.listing_id))
  const [nudges, setNudges] = useState({ jake_v1: NO_NUDGES, pablo_v1: NO_NUDGES })
  const [detailId, setDetailId] = useState(null)
  const [tasteReturn, setTasteReturn] = useState('chat')
  const factSeq = useRef(0)

  // Memory rail loads from the live agent (mock fallback inside api.js).
  useEffect(() => {
    getContext(profileId).then(setMemories)
  }, [profileId])

  const spec = SPECS[profileId]

  // Learned facts (interview answers, chat extractions) animate into the rail.
  const addFacts = useCallback((facts) => {
    if (!facts?.length) return
    setMemories((prev) => {
      const known = new Set(prev.map((m) => m.text))
      const fresh = facts
        .filter((f) => !known.has(f.text))
        .map((f) => ({ ...f, id: `f${++factSeq.current}`, fresh: true }))
      if (!fresh.length) return prev
      const superseded = new Set(fresh.map((f) => factKey(f.text)).filter(Boolean))
      const kept = prev.filter((m) => !superseded.has(factKey(m.text)))
      return [...kept, ...fresh]
    })
  }, [])

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
          newFacts: turn.new_facts ?? [],
        },
      ])
      setRecalledIds((turn.recalled ?? []).map((m) => m.id))
      addFacts(turn.new_facts)
      if (turn.action?.type === 'generate_tour') setGenerating(true)
    } finally {
      setThinking(false)
    }
  }, [profileId, addFacts])

  const start = useCallback((text) => {
    setView('chat')
    sendMessage(text)
  }, [sendMessage])

  // Returning-user "keep going" — the agent opens, no interview (design 08, 01).
  const keepGoing = useCallback(() => {
    setView('chat')
    setMessages((prev) =>
      prev.length
        ? prev
        : [{
            role: 'agent',
            text: `Welcome back, ${spec.name} — shall we pick up the Austin search where we left off? Say the word and I'll pull what's new.`,
          }],
    )
  }, [spec.name])

  // Interview wiring (design 08 §1): each answer writes facts to the rail and
  // re-ranks the candidate pool; the panel inside the view animates the move.
  const onInterviewAnswer = useCallback((questionId, answer, newFacts) => {
    setAnswers((prev) => [...prev, { questionId, answer }])
    addFacts(newFacts)
    setRankOrder(rankListings([...answers, { questionId, answer }]).map((r) => r.listing_id))
  }, [answers, addFacts])

  const onInterviewDone = useCallback((reason) => {
    if (reason === 'finished') {
      setTasteReturn('chat')
      setView('taste') // payoff: "here's your taste passport"
    } else {
      keepGoing()
    }
  }, [keepGoing])

  const openTaste = useCallback(() => {
    setTasteReturn(view)
    setView('taste')
  }, [view])

  const onTasteContinue = useCallback(() => {
    setView('chat')
    sendMessage('Find me homes that fit what you know about me.')
  }, [sendMessage])

  // Memory hygiene — optimistic local state; best-effort sync to the agent.
  const confirmMemory = useCallback((id) => {
    setMemories((prev) => prev.map((m) => (m.id === id ? { ...m, confirmed: true } : m)))
  }, [])
  const editMemory = useCallback((id, text) => {
    if (!text.trim()) return
    setMemories((prev) => prev.map((m) => (m.id === id ? { ...m, text: text.trim(), confirmed: true } : m)))
    updateMemory(profileId, id, text.trim())
  }, [profileId])
  const removeMemory = useCallback((id) => {
    setMemories((prev) => prev.filter((m) => m.id !== id))
    deleteMemory(profileId, id)
  }, [profileId])

  const onTourReady = useCallback(() => {
    setGenerating(false)
    setView('tour')
  }, [])

  const rail = (
    <MemoryRail
      profileId={profileId}
      memories={memories}
      recalledIds={view === 'chat' ? recalledIds : []}
      nudges={nudges[profileId]}
      onConfirm={confirmMemory}
      onEdit={editMemory}
      onRemove={removeMemory}
      onOpenTaste={openTaste}
    />
  )

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

      {view === 'welcome' && (
        <Welcome
          profileId={profileId}
          onStart={start}
          onKeepGoing={keepGoing}
          onThingsChanged={() => setView('interview')}
        />
      )}

      {view === 'interview' && (
        /* 08b owns its own right panel ("your taste, taking shape") — no rail */
        <InterviewView
          profileId={profileId}
          answers={answers}
          onAnswer={onInterviewAnswer}
          onDone={onInterviewDone}
        />
      )}

      {view === 'chat' && (
        <div className="main">
          <ChatView
            messages={messages}
            profileId={profileId}
            thinking={thinking}
            rankOrder={rankOrder}
            onSend={sendMessage}
            onOpenListing={(id) => { setDetailId(id); setView('detail') }}
            onGenerate={() => setGenerating(true)}
          />
          {rail}
        </div>
      )}

      {view === 'taste' && (
        <TasteProfileView
          profileId={profileId}
          nudges={nudges[profileId]}
          onNudge={(key, value) =>
            setNudges((prev) => ({
              ...prev,
              [profileId]: { ...prev[profileId], [key]: value },
            }))
          }
          onContinue={onTasteContinue}
          onBack={() => setView(tasteReturn === 'welcome' ? 'welcome' : tasteReturn)}
        />
      )}

      {view === 'detail' && (
        <div className="main">
          <ListingDetailView
            listingId={detailId}
            profileId={profileId}
            onGenerate={() => setGenerating(true)}
            onBack={() => setView('chat')}
          />
          {rail}
        </div>
      )}

      {view === 'tour' && (
        <div className="main">
          <TourView profileId={profileId} onBack={() => setView('chat')} />
          {rail}
        </div>
      )}

      {generating && <GeneratingOverlay profileId={profileId} onDone={onTourReady} />}
    </div>
  )
}
