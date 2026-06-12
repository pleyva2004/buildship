import { LISTINGS } from '../mock/data.js'

// Live re-rank panel (design 08 §1) — the learn→re-rank proof. Shows the
// candidate pool re-ordering as answers land: motion + "↑ moved up" + met /
// unmet must-have chips. Deliberately NO numeric match score (data slop).
export default function RerankPanel({ ranked, prevOrder }) {
  return (
    <div className="rerank-panel">
      {ranked.map((r, idx) => {
        const listing = LISTINGS.find((l) => l.listing_id === r.listing_id)
        if (!listing) return null
        const prevIdx = prevOrder.indexOf(r.listing_id)
        const moved = prevIdx === -1 ? 0 : prevIdx - idx
        return (
          <div
            key={r.listing_id}
            className={'rerank-row' + (moved > 0 ? ' up' : moved < 0 ? ' down' : '')}
            style={{ order: idx }}
          >
            <span className="rank-pos">{idx + 1}</span>
            <div className="rank-body">
              <span className="rank-title">{listing.title}</span>
              <span className="rank-meta">{listing.price} · {listing.neighborhood}</span>
            </div>
            <div className="rank-chips">
              {r.met.map((m) => <span key={m} className="chip met">✓ {m}</span>)}
              {r.unmet.map((m) => <span key={m} className="chip unmet">○ {m}</span>)}
              {moved > 0 && <span className="chip moved">↑ moved up</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
