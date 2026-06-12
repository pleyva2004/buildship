import { useState } from 'react'
import CompareSlider from './CompareSlider.jsx'
import { LISTINGS, ROOM_LABELS, ROOM_CUES, SPECS } from '../mock/data.js'
import { rawPhoto, restyledPhoto, tourVideo, PLACEHOLDER } from '../assets.js'

// Act 5 — the hero, rebuilt slider-first (design 08 §2 (08)): the draggable
// before/after leads each room (the credibility proof); the video is offered
// as "play the full tour." Per-room taste chips tie the magic to the rail;
// compare-aesthetics is a deliberate split-screen, not a topbar toggle.
const OTHER = { jake_v1: 'pablo_v1', pablo_v1: 'jake_v1' }

export default function TourView({ profileId, onBack }) {
  const hero = LISTINGS.find((l) => l.hero)
  const [room, setRoom] = useState(hero.rooms[0])
  const [showVideo, setShowVideo] = useState(false)
  const [videoFailed, setVideoFailed] = useState(false)
  const [compareProfiles, setCompareProfiles] = useState(false)
  const [shared, setShared] = useState(false)
  const spec = SPECS[profileId]
  const otherSpec = SPECS[OTHER[profileId]]
  const cues = ROOM_CUES[profileId]?.[room] ?? []

  const share = async () => {
    try {
      await navigator.clipboard.writeText(`${location.origin}/tour/${hero.listing_id}/${profileId}`)
      setShared(true)
      setTimeout(() => setShared(false), 2000)
    } catch {
      /* clipboard unavailable — button stays quiet */
    }
  }

  return (
    <div className="tour">
      <button className="back" onClick={onBack}>← Back to conversation</button>
      <div className="head">
        <h1>{hero.title}, in {spec.name}'s style</h1>
        <div className="sub serif">{spec.aesthetic_name} · {spec.lighting_mood}</div>
      </div>

      <div className="proof-line serif">Same windows. Same walls. Your decor.</div>

      <div className="room-tabs">
        {hero.rooms.map((r) => (
          <button key={r} className={r === room ? 'active' : ''} onClick={() => setRoom(r)}>
            {ROOM_LABELS[r] ?? r}
          </button>
        ))}
      </div>

      {compareProfiles ? (
        <div className="profile-compare">
          {[spec, otherSpec].map((s) => (
            <figure key={s.profile_id}>
              <img
                src={restyledPhoto(room, s.profile_id)}
                alt={`${ROOM_LABELS[room] ?? room} — ${s.name}'s style`}
                onError={(e) => { e.currentTarget.src = PLACEHOLDER(`${s.name}'s restyle landing soon`) }}
              />
              <figcaption>
                <strong>{s.name}</strong> · {s.aesthetic_name}
              </figcaption>
            </figure>
          ))}
          <div className="compare-caption serif">One house, two souls — same rooms, same walls.</div>
        </div>
      ) : (
        <CompareSlider
          key={`${room}-${profileId}`} /* reset wipe position per room/profile */
          original={rawPhoto(room)}
          restyled={restyledPhoto(room, profileId)}
        />
      )}

      {cues.length > 0 && (
        <div className="room-cues">
          <span className="cues-label">Shaped by your cues:</span>
          {cues.map((c) => <span className="chip" key={c}>{c}</span>)}
        </div>
      )}

      <div className="tour-actions">
        <button className="cta" onClick={() => setShowVideo((v) => !v)}>
          {showVideo ? 'Hide the full tour' : '▶ Play the full tour'}
        </button>
        <button className="ghost" onClick={() => setCompareProfiles((v) => !v)}>
          {compareProfiles ? 'Back to before / after' : `Compare aesthetics: ${spec.name} ⇄ ${otherSpec.name}`}
        </button>
        <a className="ghost" href={tourVideo(profileId)} download={`vista-tour-${profileId}.mp4`}>
          Save tour
        </a>
        <button className="ghost" onClick={share}>{shared ? '✓ Link copied' : 'Share'}</button>
      </div>

      {showVideo && (
        <div className="player-wrap">
          {videoFailed ? (
            <div className="player-fallback">tour video landing soon — stills above are live</div>
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
      )}
    </div>
  )
}
