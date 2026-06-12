import { LISTINGS } from '../mock/data.js'
import { rawPhoto, restyledPhoto, PLACEHOLDER } from '../assets.js'

// 05 · Recommendations (design 08 §2) — curated cards inline in the chat.
// Lead with the "why you," not the price; one honest tradeoff each; the set
// follows the live re-rank order; a tiny before/after peek teases the restyle.
export default function ListingCards({ listingIds, profileId, rankOrder, onOpen, onGenerate }) {
  let listings = LISTINGS.filter((l) => listingIds.includes(l.listing_id))
  if (rankOrder?.length) {
    listings = [...listings].sort(
      (a, b) => rankOrder.indexOf(a.listing_id) - rankOrder.indexOf(b.listing_id),
    )
  }
  return (
    <div className="cards">
      {listings.map((l) => (
        <div
          className="listing-card"
          key={l.listing_id}
          role="button"
          tabIndex={0}
          onClick={() => onOpen(l.listing_id)}
          onKeyDown={(e) => e.key === 'Enter' && onOpen(l.listing_id)}
        >
          <div className="card-media">
            <img
              src={l.hero ? rawPhoto('exterior') : PLACEHOLDER(l.title)}
              alt={l.title}
              onError={(e) => { e.currentTarget.src = PLACEHOLDER('photo coming') }}
            />
            {l.hero && (
              <img
                className="peek"
                src={restyledPhoto('exterior', profileId)}
                alt=""
                aria-hidden
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                  e.currentTarget.nextElementSibling?.style.setProperty('display', 'none') // tag dies with the peek
                }}
              />
            )}
            {l.hero && <span className="peek-tag">your style ↗</span>}
          </div>
          <div className="body">
            <div className="why-headline">{(l.match_notes[profileId] ?? [])[0] ?? l.neighborhood}</div>
            <h3>{l.title}</h3>
            <div className="meta">
              {l.price} · {l.beds}bd {l.baths}ba · {l.location}
            </div>
            <div className="why">
              {(l.match_notes[profileId] ?? []).slice(1).map((note) => (
                <span className="chip met" key={note}>✓ {note}</span>
              ))}
              {l.tradeoff?.[profileId] && (
                <span className="chip unmet">○ {l.tradeoff[profileId]}</span>
              )}
            </div>
            {l.hero && (
              <button
                className="cta"
                onClick={(e) => { e.stopPropagation(); onGenerate(l.listing_id) }}
              >
                See this home in your style
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
