import { LISTINGS } from '../mock/data.js'
import { rawPhoto, PLACEHOLDER } from '../assets.js'

// Acts 4 — curated cards inline in the chat (no separate results screen).
// Match-reasoning chips tie each home back to the memory rail.
export default function ListingCards({ listingIds, profileId, onGenerate }) {
  const listings = LISTINGS.filter((l) => listingIds.includes(l.listing_id))
  return (
    <div className="cards">
      {listings.map((l) => (
        <div className="listing-card" key={l.listing_id}>
          <img
            src={l.hero ? rawPhoto('exterior') : PLACEHOLDER(l.title)}
            alt={l.title}
            onError={(e) => { e.currentTarget.src = PLACEHOLDER('photo coming') }}
          />
          <div className="body">
            <h3>{l.title}</h3>
            <div className="meta">
              {l.price} · {l.beds}bd {l.baths}ba · {l.location}
            </div>
            <div className="why">
              {(l.match_notes[profileId] ?? []).map((note) => (
                <span className="chip" key={note}>{note}</span>
              ))}
            </div>
            {l.hero && (
              <button className="cta" onClick={() => onGenerate(l.listing_id)}>
                See this home in your style
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
