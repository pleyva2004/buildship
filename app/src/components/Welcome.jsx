import { useState } from 'react'

// Act 1 — an invitation, not a search bar. Submitting doesn't navigate to
// results; it BECOMES the first chat message (the search bar becomes the chat).
export default function Welcome({ onStart }) {
  const [text, setText] = useState('')
  return (
    <div className="welcome">
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
    </div>
  )
}
