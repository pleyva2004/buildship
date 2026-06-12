import { useCallback, useEffect, useRef, useState } from 'react'
import Welcome from './components/Welcome.jsx'
import InterviewView from './components/InterviewView.jsx'
import ChatView from './components/ChatView.jsx'
import MemoryRail from './components/MemoryRail.jsx'
import TasteProfileView from './components/TasteProfileView.jsx'
import ListingDetailView from './components/ListingDetailView.jsx'
import GeneratingOverlay from './components/GeneratingOverlay.jsx'
import TourView from './components/TourView.jsx'
import { chat, getContext, updateMemory, deleteMemory, finishInterview, resetSession } from './api.js'
import { rankListings } from './mock/interview.js'
import * as discovery from './mock/discovery.js'
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
  const [nudges, setNudges] = useState({ jake_v1: NO_NUDGES, pablo_v1: NO_NUDGES, guest_v1: NO_NUDGES })
  // Specs distilled from THIS session's interview (step 4) — override the
  // seeded SPECS so the passport reflects the actual conversation.
  const [dynamicSpecs, setDynamicSpecs] = useState({})
  // Discovery state per profile (design 10): weights/dismissed/saved + the
  // current RankedSet. Local model for now; live endpoints follow (10b PARKED).
  const [disc, setDisc] = useState({})
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

  const freshDisc = useCallback((pid) => {
    // logistics facts (Area/Budget band) become HARD filters, never weights
    const state = discovery.initialState(pid, discovery.filtersFromMemories(memories))
    return { state, set: discovery.discover(pid, state).set }
  }, [memories])
  const discCur = disc[profileId] ?? freshDisc(profileId)
  const commitDisc = useCallback((next) => {
    setDisc((prev) => ({ ...prev, [profileId]: next }))
  }, [profileId])

  const sendMessage = useCallback(async (text) => {
    setMessages((prev) => [...prev, { role: 'user', text }])
    setThinking(true)
    try {
      const turn = await chat(profileId, text)
      const isSet = turn.action?.type === 'recommend'
      if (isSet) setDisc((prev) => ({ ...prev, [profileId]: prev[profileId] ?? freshDisc(profileId) }))
      setMessages((prev) => [
        ...prev,
        { role: 'agent', text: turn.reply, set: isSet, newFacts: turn.new_facts ?? [] },
      ])
      setRecalledIds((turn.recalled ?? []).map((m) => m.id))
      addFacts(turn.new_facts)
      if (turn.action?.type === 'generate_tour') setGenerating(true)
    } finally {
      setThinking(false)
    }
  }, [profileId, addFacts, freshDisc])

  // ---- discovery reactions (design 10 §6) — always narrated -----------------
  const onRefine = useCallback((r) => {
    const { state, narration, set } = discovery.refine(discCur.state, r.bump, r.say)
    commitDisc({ state, set })
    setMessages((prev) => [...prev,
      { role: 'user', text: r.label },
      { role: 'narrate', text: narration },
      { role: 'agent', set: true },
    ])
  }, [discCur, commitDisc])

  const onDismiss = useCallback((id) => {
    const { state, narration, set } = discovery.dismiss(discCur.state, id)
    commitDisc({ state, set })
    setMessages((prev) => [...prev, { role: 'narrate', text: narration }])
  }, [discCur, commitDisc])

  const onSaveListing = useCallback((id) => {
    commitDisc({ ...discCur, state: discovery.toggleSave(discCur.state, id) })
  }, [discCur, commitDisc])

  const onMoreListings = useCallback(() => {
    const { state, set } = discovery.showMore(discCur.state)
    commitDisc({ state, set })
  }, [discCur, commitDisc])

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

  const onInterviewDone = useCallback(async (reason) => {
    if (reason === 'finished') {
      // distill THIS conversation into the spec the passport shows
      const spec = await finishInterview(profileId, answers)
      setDynamicSpecs((prev) => ({
        ...prev,
        [profileId]: { ...SPECS[profileId], ...spec, profile_id: profileId },
      }))
      setTasteReturn('chat')
      setView('taste') // payoff: "here's your taste passport"
    } else {
      keepGoing()
    }
  }, [keepGoing, profileId, answers])

  // "Things changed — let's catch up" starts a FRESH interview: clear session
  // answers (and the agent's accumulated interview state); memories persist.
  const startInterview = useCallback(() => {
    setAnswers([])
    resetSession(profileId)
    setView('interview')
  }, [profileId])

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
      spec={dynamicSpecs[profileId]}
      weights={view === 'chat' && disc[profileId] ? discCur.set.weights : null}
      savedIds={disc[profileId] ? discCur.state.saved : []}
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
          onThingsChanged={startInterview}
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
            discovery={{ set: discCur.set, saved: discCur.state.saved }}
            onSend={sendMessage}
            onRefine={onRefine}
            onDismiss={onDismiss}
            onSaveListing={onSaveListing}
            onMoreListings={onMoreListings}
            onOpenListing={(id) => { setDetailId(id); setView('detail') }}
            onGenerate={() => setGenerating(true)}
          />
          {rail}
        </div>
      )}

      {view === 'taste' && (
        <TasteProfileView
          profileId={profileId}
          spec={dynamicSpecs[profileId]}
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
