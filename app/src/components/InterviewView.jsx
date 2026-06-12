import { useEffect, useRef, useState } from 'react'
import { nextQuestion, recordAnswer } from '../api.js'
import { rankListings } from '../mock/interview.js'
import RerankPanel from './RerankPanel.jsx'
import { SPECS } from '../mock/data.js'

// 02 · Getting to Know You (design 08 §2) — short adaptive interview, one
// question at a time, never a form. Chips + free text; questions branch on
// answers; candidate homes visibly re-rank below as each answer lands.
// Skippable (never gates the experience) and finite ("2 of 5").
export default function InterviewView({ profileId, answers, onAnswer, onDone }) {
  const [question, setQuestion] = useState(null)
  const [draft, setDraft] = useState('')
  const [ranked, setRanked] = useState(() => rankListings(answers))
  const prevOrder = useRef(ranked.map((r) => r.listing_id))
  const spec = SPECS[profileId]

  useEffect(() => {
    let alive = true
    nextQuestion(profileId, answers).then((q) => {
      if (!alive) return
      if (q) setQuestion(q)
      else onDone('finished')
    })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers.length])

  const submit = async (answer) => {
    if (!answer.trim() || !question) return
    setDraft('')
    prevOrder.current = ranked.map((r) => r.listing_id)
    const res = await recordAnswer(profileId, answers, question.id, answer.trim())
    setRanked(res.ranked)
    onAnswer(question.id, answer.trim(), res.new_facts) // parent stores answer + facts → rail animates
  }

  if (!question) return null

  return (
    <div className="interview">
      <div className="interview-inner">
        <div className="interview-head">
          <span className="progress">{question.asked} of {question.total}</span>
          <button className="skip" onClick={() => onDone('skipped')}>
            Skip for now →
          </button>
        </div>

        <h1 key={question.id} className="question-prompt">{question.prompt}</h1>
        {question.optional && <p className="optional-note">Optional — skip if nothing comes to mind.</p>}

        <div className="answer-chips">
          {question.chips.map((c) => (
            <button key={c} className="answer-chip" onClick={() => submit(c)}>{c}</button>
          ))}
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); submit(draft) }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="…or say it in your own words"
          />
          <button className="cta" type="submit">Answer</button>
        </form>

        <RerankPanel ranked={ranked} prevOrder={prevOrder.current} />
        <p className="rerank-caption">
          {spec.name}, these re-order as I learn — nothing is locked in yet.
        </p>
      </div>
    </div>
  )
}
