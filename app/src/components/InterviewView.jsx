import { useCallback, useEffect, useRef, useState } from 'react'
import { getHealth, nextQuestion, recordAnswer, transcribe } from '../api.js'

// 02 · Getting to Know You — design 08b. One screen, five phases:
// intro → speaking → ask → (listening → transcribing, voice) → thinking → done.
// Voice = answers by held mic (MediaRecorder → /api/voice/transcribe); VISTA's
// questions stay on screen as text (design 09 scope: voice-to-voice is later).
// Facts that fit no target section land in "Also worth knowing" — the profile
// flexes to what people actually say (never forced, never dropped).
// Motion rule (08b §11): entrances are transform-only, resting opacity 1.

const BEATS = {
  // 08b §9 — the rhythm; live latency replaces the fixed windows but never undercuts the beat
  speak: { voice: 1400, text: 900 },
  commit: 700,
  think: { voice: 1500, text: 1100 },
  done: 1200,
}

const TARGET_GROUPS = ['Life', 'Taste', 'Materials', 'Must-haves']
const OTHER_GROUP = 'Also worth knowing'

function groupOf(fact) {
  const t = fact.text.toLowerCase()
  if (t.startsWith('must-have') || t.startsWith('deal-breaker')) return 'Must-haves'
  if (fact.category === 'materials') return 'Materials'
  if (fact.category === 'taste' || fact.category === 'mood_board') return 'Taste'
  if (fact.category === 'life_situation') return 'Life'
  return OTHER_GROUP // open lane: anything off-taxonomy still lands visibly
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

export default function InterviewView({ profileId, answers, onAnswer, onDone }) {
  const [mode, setMode] = useState(null) // null until intro choice; 'voice' | 'text'
  const [phase, setPhase] = useState('intro')
  const [question, setQuestion] = useState(null)
  const [thread, setThread] = useState([]) // text-mode bubbles [{role, text}]
  const [draft, setDraft] = useState('')
  const [caption, setCaption] = useState(null) // voice: transcribed answer
  const [facts, setFacts] = useState([]) // panel facts (with group)
  const [palette, setPalette] = useState([])
  const [aesthetic, setAesthetic] = useState(null)
  const [micNote, setMicNote] = useState(null)
  const [brain, setBrain] = useState(null) // 'live' | 'scripted' | 'offline' — which brain answers
  const recorder = useRef(null)
  const chunks = useRef([])
  const alive = useRef(true)

  // StrictMode double-mounts in dev: re-arm on every mount, not just the first.
  useEffect(() => {
    alive.current = true
    return () => { alive.current = false }
  }, [])

  // Surface WHICH brain is answering — a stale/mock backend must never be able
  // to masquerade as the live agent (lesson learned the hard way).
  useEffect(() => {
    getHealth().then((h) => {
      if (alive.current) setBrain(h === null ? 'offline' : h.llm === 'live' ? 'live' : 'scripted')
    })
  }, [])

  const askQuestion = useCallback(async (q, chosenMode) => {
    setQuestion(q)
    setPhase('speaking')
    setThread((prev) =>
      prev.some((b) => b.text === q.prompt) ? prev : [...prev, { role: 'agent', text: q.prompt }],
    )
    await wait(BEATS.speak[chosenMode])
    if (alive.current) setPhase('ask')
  }, [])

  const finish = useCallback(async () => {
    await wait(BEATS.done)
    if (alive.current) setPhase('done')
  }, [])

  const begin = useCallback(async (chosenMode) => {
    setMode(chosenMode)
    setPhase('thinking')
    const q = await nextQuestion(profileId, answers)
    if (!alive.current) return
    if (q) askQuestion(q, chosenMode)
    else finish()
  }, [profileId, answers, askQuestion, finish])

  const submit = useCallback(async (answer) => {
    const text = answer.trim()
    if (!text || !question || phase === 'thinking') return
    setDraft('')
    setCaption(null)
    setThread((prev) => [...prev, { role: 'user', text }])
    setPhase('thinking')

    const minBeat = wait(BEATS.think[mode])
    const res = await recordAnswer(profileId, answers, question.id, text)
    if (!alive.current) return

    setFacts((prev) => [
      ...prev,
      ...res.new_facts
        .filter((f) => !prev.some((p) => p.text === f.text))
        .map((f) => ({ ...f, group: groupOf(f) })),
    ])
    const delta = res.profile_delta ?? {}
    if (delta.palette_add?.length) {
      setPalette((prev) => [...new Set([...prev, ...delta.palette_add])].slice(0, 6))
    }
    if (delta.aesthetic) setAesthetic(delta.aesthetic)

    onAnswer(question.id, text, res.new_facts) // parent: rail + global rerank
    await minBeat
    if (!alive.current) return
    if (res.next) askQuestion(res.next, mode)
    else finish()
  }, [question, phase, mode, profileId, answers, onAnswer, askQuestion, finish])

  // ---- voice: hold-to-speak (MediaRecorder → /api/voice/transcribe) --------

  const startListening = useCallback(async () => {
    if (phase !== 'ask') return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunks.current = []
      const rec = new MediaRecorder(stream)
      rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data)
      rec.start()
      recorder.current = rec
      setPhase('listening')
    } catch {
      setMicNote("Couldn't reach the mic — let's type instead.")
      setMode('text')
    }
  }, [phase])

  const stopListening = useCallback(async () => {
    const rec = recorder.current
    if (!rec || phase !== 'listening') return
    setPhase('transcribing')
    const blob = await new Promise((resolve) => {
      rec.onstop = () => resolve(new Blob(chunks.current, { type: rec.mimeType }))
      rec.stop()
      rec.stream.getTracks().forEach((t) => t.stop())
    })
    recorder.current = null
    const text = await transcribe(blob)
    if (!alive.current) return
    if (!text) {
      setMicNote("I couldn't catch that — try again, or type it below.")
      setPhase('ask')
      return
    }
    setCaption(text)
    setPhase('ask')
    await wait(BEATS.commit) // 08b: transcript visible, then commits
    if (alive.current) submit(text)
  }, [phase, submit])

  const switchMode = useCallback((m) => {
    if (m === mode || phase === 'intro' || phase === 'done') return
    setMicNote(null)
    setMode(m)
  }, [mode, phase])

  // Spacebar = push-to-talk (hold to speak, release when done). Ignores key
  // repeat and anything typed into an input, so text mode is unaffected.
  useEffect(() => {
    if (mode !== 'voice') return
    const isTyping = (e) => ['INPUT', 'TEXTAREA'].includes(e.target.tagName)
    const down = (e) => {
      if (e.code !== 'Space' || e.repeat || isTyping(e)) return
      e.preventDefault()
      startListening()
    }
    const up = (e) => {
      if (e.code !== 'Space' || isTyping(e)) return
      e.preventDefault()
      stopListening()
    }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
    }
  }, [mode, startListening, stopListening])

  // ---- render ---------------------------------------------------------------

  const groups = [...TARGET_GROUPS, ...(facts.some((f) => f.group === OTHER_GROUP) ? [OTHER_GROUP] : [])]

  return (
    <div className="iv">
      <div className="iv-topbar">
        <span className="iv-title">Getting to know you</span>
        {brain && brain !== 'live' && (
          <span className="iv-brain" title="The adaptive agent isn't connected — answers follow the rehearsed script.">
            {brain === 'offline' ? 'offline · local mock' : 'scripted fallback'}
          </span>
        )}
        {brain === 'live' && <span className="iv-brain live">live</span>}
        <span className="iv-progress">
          {question && Array.from({ length: question.total }, (_, i) => (
            <i key={i} className={i < question.asked ? 'on' : ''} />
          ))}
        </span>
        <div className="iv-right">
          {mode && phase !== 'done' && (
            <div className="iv-mode">
              <button className={mode === 'voice' ? 'active' : ''} onClick={() => switchMode('voice')}>Voice</button>
              <button className={mode === 'text' ? 'active' : ''} onClick={() => switchMode('text')}>Text</button>
            </div>
          )}
          <button className="iv-skip" onClick={() => onDone('skipped')}>Skip for now →</button>
        </div>
      </div>

      <div className="iv-body">
        <div className="iv-stage">
          {phase === 'intro' && (
            <div className="iv-intro">
              <h1>Before we look at a single home, I'd love to understand you.</h1>
              <p>A few minutes of conversation — talk or type, switch anytime.</p>
              <div className="iv-mode-cards">
                <button className="iv-mode-card" onClick={() => begin('voice')}>
                  <span className="orb orb-mini" />
                  <strong>Talk it through</strong>
                  <span>Hold the mic and just speak</span>
                </button>
                <button className="iv-mode-card" onClick={() => begin('text')}>
                  <span className="iv-type-glyph serif">Aa</span>
                  <strong>Type instead</strong>
                  <span>Chips and free text</span>
                </button>
              </div>
            </div>
          )}

          {mode === 'voice' && phase !== 'intro' && phase !== 'done' && (
            <div className="iv-voice">
              <div className={`orb ${phase === 'speaking' ? 'breathe' : ''} ${phase === 'listening' ? 'ripple' : ''}`}>
                {phase === 'listening' && <><i className="ring" /><i className="ring r2" /><i className="ring r3" /></>}
              </div>
              {phase === 'speaking' && <div className="iv-status">VISTA is asking…</div>}
              {question && <h1 className="iv-question serif">{question.prompt}</h1>}
              {caption && <p className="iv-caption">“{caption}”</p>}
              {phase === 'listening' && (
                <div className="iv-wave">{Array.from({ length: 9 }, (_, i) => <i key={i} style={{ animationDelay: `${i * 70}ms` }} />)}</div>
              )}
              <button
                className={`iv-mic ${phase === 'listening' ? 'live' : ''}`}
                disabled={phase === 'thinking' || phase === 'transcribing' || phase === 'speaking'}
                onPointerDown={(e) => {
                  try { e.currentTarget.setPointerCapture(e.pointerId) } catch { /* capture is best-effort */ }
                  startListening()
                }}
                onPointerUp={stopListening}
                onPointerCancel={stopListening}
              >
                {phase === 'listening' ? 'Listening… release when done'
                  : phase === 'transcribing' || phase === 'thinking' ? 'VISTA is thinking…'
                  : 'Hold to speak'}
              </button>
              {micNote && <p className="iv-note">{micNote}</p>}
              <p className="iv-hint">Hold the <kbd>space</kbd> bar to talk — or switch to Text up top.</p>
            </div>
          )}

          {mode === 'text' && phase !== 'intro' && phase !== 'done' && (
            <div className="iv-text">
              <div className="iv-thread">
                {thread.map((b, i) => (
                  <div key={i} className={`iv-bubble ${b.role}`}>{b.text}</div>
                ))}
                {(phase === 'speaking' || phase === 'thinking') && (
                  <div className="iv-bubble agent iv-dots"><i /><i /><i /></div>
                )}
              </div>
              {phase === 'ask' && question && (
                <div className="iv-chips">
                  {question.chips?.map((c) => (
                    <button key={c} className="iv-chip" onClick={() => submit(c)}>{c}</button>
                  ))}
                </div>
              )}
              <form onSubmit={(e) => { e.preventDefault(); submit(draft) }}>
                <input
                  value={draft}
                  disabled={phase !== 'ask'}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={phase === 'ask' ? '…or say it in your own words' : 'VISTA is thinking…'}
                />
                <button className="cta" type="submit" disabled={phase !== 'ask'}>Answer</button>
              </form>
              {micNote && <p className="iv-note">{micNote}</p>}
            </div>
          )}

          {phase === 'done' && (
            <div className="iv-done">
              <span className="iv-check">✓</span>
              <h1>That's everything I need.</h1>
              <p>Your taste profile is ready — built from your own words.</p>
            </div>
          )}
        </div>

        <aside className="iv-panel">
          <h2>Your taste, taking shape</h2>
          <div className="iv-aesthetic">
            <span className="label">Aesthetic</span>
            <span className="serif value">{aesthetic ?? '——'}</span>
          </div>
          <div className="iv-palette">
            {palette.length
              ? palette.map((hex) => <i key={hex} style={{ background: hex }} title={hex} />)
              : <span className="iv-quiet">Colors arrive as we talk…</span>}
          </div>
          {groups.map((g) => {
            const list = facts.filter((f) => f.group === g)
            return (
              <div className="iv-group" key={g}>
                <h3>{g}</h3>
                {list.length
                  ? list.map((f) => (
                    <div className="iv-fact" key={f.text}>
                      <span className="tick">✓</span>
                      <span>{f.text}</span>
                      {f.provenance === 'inferred' && <em title="VISTA read between the lines">inferred</em>}
                    </div>
                  ))
                  : <p className="iv-quiet">VISTA is still listening…</p>}
              </div>
            )
          })}
          {phase === 'done' && (
            <button className="iv-ready cta" onClick={() => onDone('finished')}>
              Profile ready → See your taste profile
            </button>
          )}
        </aside>
      </div>
    </div>
  )
}
