import { LISTINGS, ROOM_LABELS, SPECS } from '../mock/data.js'
import { rawPhoto, PLACEHOLDER } from '../assets.js'
import Stamp from './Stamp.jsx'
import { AREA_INTEL } from '../mock/areas.js'

// 06 · Listing Detail (design 08 §2) — gives the home weight so the
// transformation feels meaningful: gallery + specs + neighborhood + expanded
// "why this fits you." ONE hero CTA — "See this home in your style" — gets a
// dedicated stage, not a card footer.
export default function ListingDetailView({ listingId, profileId, onGenerate, onBack }) {
  const listing = LISTINGS.find((l) => l.listing_id === listingId)
  if (!listing) return null
  const spec = SPECS[profileId]
  const galleryRooms = listing.rooms.length ? listing.rooms : ['living', 'kitchen', 'exterior']

  return (
    <div className="detail">
      <button className="back" onClick={onBack}>← Back to conversation</button>

      <div className="detail-head">
        <h1>{listing.title}</h1>
        <div className="sub">
          {listing.price} · {listing.beds}bd {listing.baths}ba · {listing.sqft.toLocaleString()} sqft · {listing.location}
        </div>
      </div>

      <div className="gallery">
        {galleryRooms.map((room) => (
          <figure key={room}>
            <img
              src={listing.hero ? rawPhoto(room) : PLACEHOLDER(ROOM_LABELS[room] ?? room)}
              alt={ROOM_LABELS[room] ?? room}
              onError={(e) => { e.currentTarget.src = PLACEHOLDER(ROOM_LABELS[room] ?? room) }}
            />
            <figcaption>{ROOM_LABELS[room] ?? room}</figcaption>
          </figure>
        ))}
      </div>

      <div className="detail-cols">
        <div className="detail-main">
          <p className="blurb">{listing.blurb}</p>

          <h3>Why this fits you, {spec.name}</h3>
          <div className="why">
            {(listing.match_notes[profileId] ?? []).map((note) => (
              <span className="chip met" key={note}>✓ {note}</span>
            ))}
          </div>
          {listing.tradeoff?.[profileId] && (
            <p className="tradeoff">Honest tradeoff: {listing.tradeoff[profileId]}.</p>
          )}

          <h3>The neighborhood <Stamp /></h3>
          <p className="blurb">{AREA_INTEL[listing.neighborhood] ?? listing.neighborhood_note}</p>
        </div>

        <div className="hero-cta-stage">
          <div className="hero-cta-card">
            <div className="swatches">
              {spec.palette_hex.map((hex) => (
                <div key={hex} className="swatch" style={{ background: hex }} />
              ))}
            </div>
            <p className="serif">
              Same rooms, same architecture — re-imagined in your {spec.aesthetic_name}.
            </p>
            {listing.hero ? (
              <button className="cta wide" onClick={() => onGenerate(listing.listing_id)}>
                See this home in your style
              </button>
            ) : (
              <p className="cta-note">Restyle available on your top match first.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
