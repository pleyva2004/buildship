import { useState } from 'react'
import { SPECS } from '../mock/data.js'
import { rawPhoto } from '../assets.js'

// Act 1 — an invitation, not a search bar. Submitting doesn't navigate to
// results; it BECOMES the first chat message (the search bar becomes the chat).
// Design 08 refinements: warm-start chips (kills blank-input anxiety),
// returning-user recognition (greet by name; "keep going" vs "things changed"),
// ambient golden-hour Ken Burns behind the headline.

const WARM_STARTS = ['Great morning light', 'A place to host', 'Walkable', 'Room for the dog']

export default function Welcome({ profileId, onStart, onKeepGoing, onThingsChanged }) {
  const [text, setText] = useState('')
  const [bgFailed, setBgFailed] = useState(false)
  const spec = SPECS[profileId]

  return (
    <div className="welcome">
      {!bgFailed && (
        <img
          className="welcome-ambient"
          src={rawPhoto('living')}
          alt=""
          aria-hidden
          onError={() => setBgFailed(true)}
        />
      )}
      <div className="welcome-content">
        <h1>Tell me about the home you're looking for.</h1>
        <p>VISTA already knows your taste. Start anywhere — a city, a feeling, a must-have.</p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (text.trim()) onStart(text.trim())
          }}
        >
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="We're finally ready to look in Austin…"
          />
          <button className="cta" type="submit">Let's talk</button>
        </form>

        <div className="warm-starts">
          {WARM_STARTS.map((w) => (
            <button key={w} className="answer-chip" onClick={() => setText((t) => (t ? `${t}, ${w.toLowerCase()}` : w))}>
              {w}
            </button>
          ))}
        </div>

        <div className="returning">
          <span>Welcome back, {spec.name}.</span>
          <button onClick={onKeepGoing}>Keep going where we left off</button>
          <span className="dot-sep">·</span>
          <button onClick={onThingsChanged}>Things changed — let's catch up</button>
        </div>
      </div>
    </div>
  )
}
