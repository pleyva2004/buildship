import { LISTINGS } from '../mock/data.js'

// Live re-rank panel (design 08 §1) — the learn→re-rank proof. Shows the
// candidate pool re-ordering as answers land: motion + "↑ moved up" + met /
// unmet must-have chips. Deliberately NO numeric match score (data slop).
export default function RerankPanel({ ranked, prevOrder, answerSeq = 0 }) {
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
            {/* chips re-key per answer so they pop even when the order holds —
                every answer gets visible feedback (design 08 §1) */}
            <div className="rank-chips" key={answerSeq}>
              {r.met.map((m) => <span key={m} className="chip met pop">✓ {m}</span>)}
              {r.unmet.map((m) => <span key={m} className="chip unmet pop">○ {m}</span>)}
              {moved > 0 && <span className="chip moved pop">↑ moved up</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
