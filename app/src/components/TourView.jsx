import { useState } from 'react'
import CompareSlider from './CompareSlider.jsx'
import { LISTINGS, ROOM_LABELS, SPECS } from '../mock/data.js'
import { rawPhoto, restyledPhoto, tourVideo } from '../assets.js'

// Act 5 — cinematic payoff: tour player, per-room slider proof, and the
// compare-aesthetics flex (profile switch lives in the top bar; this view
// re-renders entirely off profileId).
export default function TourView({ profileId, onBack }) {
  const hero = LISTINGS.find((l) => l.hero)
  const [room, setRoom] = useState(hero.rooms[0])
  const [videoFailed, setVideoFailed] = useState(false)
  const spec = SPECS[profileId]

  return (
    <div className="tour">
      <button className="back" onClick={onBack}>← Back to conversation</button>
      <div className="head">
        <h1>{hero.title}, in {spec.name}'s style</h1>
        <div className="sub serif">{spec.aesthetic_name} · {spec.lighting_mood}</div>
      </div>

      <div className="player-wrap">
        {videoFailed ? (
          <div className="player-fallback">tour video landing soon — stills below are live</div>
        ) : (
          <video
            key={profileId} /* force reload on profile switch */
            src={tourVideo(profileId)}
            controls
            autoPlay
            muted
            onError={() => setVideoFailed(true)}
          />
        )}
      </div>

      <div className="room-tabs">
        {hero.rooms.map((r) => (
          <button key={r} className={r === room ? 'active' : ''} onClick={() => setRoom(r)}>
            {ROOM_LABELS[r] ?? r}
          </button>
        ))}
      </div>

      <CompareSlider
        key={`${room}-${profileId}`} /* reset wipe position per room/profile */
        original={rawPhoto(room)}
        restyled={restyledPhoto(room, profileId)}
      />
    </div>
  )
}
