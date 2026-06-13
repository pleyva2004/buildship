import { LISTINGS } from '../mock/data.js'
import { fitChips, tradeChip } from '../mock/discovery.js'
import { rawPhoto, PLACEHOLDER } from '../assets.js'
import Stamp, { CompassIcon } from './Stamp.jsx'
import { AREA_INTEL, areaShort, liveAreaNotes } from '../mock/areas.js'

// Design 10 §3 — the curated set: VISTA showing a few homes it chose and
// telling you why. Lead = large card; alternates = compact rows. Never a grid,
// never a score. Badges: top pick / moved up / new find.
// Design 11: each card carries an AREA NOTE — researched intel about the
// place, visually a separate channel from the moss why-you chips.

const photoBg = (hue) =>
  `linear-gradient(150deg, hsl(${hue} 42% 72%), hsl(${hue - 6} 38% 58%) 55%, hsl(${hue - 10} 34% 42%))`

const BADGE = {
  top: { cls: '', label: '★ Top pick for you' },
  moved: { cls: ' moved', label: '↑ Moved up' },
  fresh: { cls: ' fresh', label: '✦ New find' },
}

function DiscoveryCard({ id, weights, lead, badge, saved, liveIntel, onSave, onDismiss, onOpen, onGenerate }) {
  const l = LISTINGS.find((x) => x.listing_id === id)
  if (!l) return null
  const chips = fitChips(l, weights, lead ? 3 : 2)
  const trade = tradeChip(l, weights)
  // live research findings for this hood displace the canned intel
  const intel = liveIntel?.get(l.neighborhood)?.notes.join(' · ')
    ?? AREA_INTEL[l.neighborhood] ?? l.neighborhood_note
  const b = badge && BADGE[badge]
  return (
    <div className={`dcard ${lead ? 'lead' : 'alt'}`}>
      <div className="dphoto" style={{ background: photoBg(l.hue ?? 30) }}>
        {l.hero && (
          <img src={rawPhoto('exterior')} alt="" onError={(e) => { e.currentTarget.style.display = 'none' }} />
        )}
        {b && <span className={`dbadge${b.cls}`}>{b.label}</span>}
        <button className={`heart${saved ? ' on' : ''}`} onClick={() => onSave(id)} title="Save">♥</button>
        {lead && <span className="teaser">See it in your style</span>}
      </div>
      <div className="dbody">
        <div className="drow">
          <span className="dname serif">{l.title}</span>
          <span className="dprice serif">{l.price}</span>
        </div>
        <div className="dmeta">{l.neighborhood} · {l.beds}bd {l.baths}ba · {l.sqft.toLocaleString()} sqft</div>
        <div className="dwhy">
          {chips.map((c) => <span className="dchip fit" key={c}>✓ {c}</span>)}
          {trade && <span className="dchip trade">{trade}</span>}
        </div>
        {intel && (
          <div className="areanote">
            <span className="an-ic"><CompassIcon /></span>
            <div className="an-body">
              <div className="an-top">
                <span className="an-hood">{l.neighborhood}</span>
                <Stamp />
              </div>
              <div className="an-text">{lead ? intel : areaShort(intel)}</div>
            </div>
          </div>
        )}
        <div className="dactions">
          {lead && <button className="btn-primary" onClick={() => onGenerate(id)}>See it in your style</button>}
          <button className="btn-ghost" onClick={() => onOpen(id)}>View home</button>
          <button className="ddismiss" onClick={() => onDismiss(id)}>✕ Not for me</button>
        </div>
      </div>
    </div>
  )
}

export default function CuratedSet({ set, saved, memories, onSave, onDismiss, onMore, onOpen, onGenerate }) {
  const hoods = [...new Set(set.visible.map((id) => LISTINGS.find((l) => l.listing_id === id)?.neighborhood).filter(Boolean))]
  const liveIntel = liveAreaNotes(memories)
  return (
    <div className="curated">
      <p className="setintro">
        <b>{set.visible.length} homes</b> {set.intro}
      </p>
      {/* the narration seam (design 11 §4) — "VISTA went and looked" */}
      {hoods.length > 0 && (
        <div className="researched-line">
          <span className="rl-ic"><CompassIcon /></span>
          <span>
            These sit across <b>{hoods.length} {hoods.length === 1 ? 'neighborhood' : 'neighborhoods'}</b> — I read up on each.
            That intel lives under <b>The area</b> tab, kept separate from your preferences.
          </span>
        </div>
      )}
      <div className="cardset">
        {set.visible.map((id, idx) => (
          <DiscoveryCard
            key={id}
            id={id}
            weights={set.weights}
            lead={idx === 0}
            badge={idx === 0 ? (set.badges[id] || 'top') : set.badges[id]}
            saved={saved.includes(id)}
            liveIntel={liveIntel}
            onSave={onSave}
            onDismiss={onDismiss}
            onOpen={onOpen}
            onGenerate={onGenerate}
          />
        ))}
        {set.hasMore && (
          <button className="morebtn" onClick={onMore}>See a few more like these →</button>
        )}
      </div>
    </div>
  )
}
