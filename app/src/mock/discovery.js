// Home-discovery model (design 10 §4) — port of the prototype's weighted
// scoring, on OUR listing ids. Pure functions over explicit state
// {weights, dismissed, saved, showMore}; the UI owns the state object.
// RANKING ENGINE NOTE: unification with the interview trait scorer is PARKED
// (design 10b) — this model serves discovery only.

import { LISTINGS } from './data.js'

export const FEATURES = {
  light:     { label: 'morning light', fit: 'South-facing rooms' },
  walkable:  { label: 'walkable',      fit: 'Walk to cafés & parks' },
  yard:      { label: 'yard',          fit: 'Fenced yard for the dog' },
  value:     { label: 'value',         fit: 'Well under budget' },
  character: { label: 'character',     fit: 'Original character' },
  open:      { label: 'open kitchen',  fit: 'Open kitchen to host' },
  quiet:     { label: 'quiet street',  fit: 'Quiet, leafy street' },
}

const TRADE = {
  light: 'fewer south windows', walkable: 'more car-dependent', yard: 'smaller yard',
  value: 'priced at a premium', character: 'newer build', open: 'closed-off kitchen', quiet: 'busier street',
}

export const REFINES = [
  { id: 'light', label: 'Brighter & airier', bump: 'light', say: 'more natural light' },
  { id: 'walkable', label: 'Closer in / walkable', bump: 'walkable', say: 'walkability' },
  { id: 'yard', label: 'Bigger yard for the dog', bump: 'yard', say: 'outdoor space' },
  { id: 'value', label: 'Better value', bump: 'value', say: 'value' },
  { id: 'character', label: 'More character', bump: 'character', say: 'character & charm' },
  { id: 'quiet', label: 'Quieter street', bump: 'quiet', say: 'a quieter street' },
]

// Profile-seeded starting weights (guest learns from scratch — flat).
export const START_WEIGHTS = {
  jake_v1: { light: 1.0, walkable: 0.8, yard: 0.7, value: 0.5, character: 0.4, open: 0.35, quiet: 0.3 },
  pablo_v1: { character: 1.0, open: 0.85, light: 0.6, walkable: 0.6, quiet: 0.5, value: 0.4, yard: 0.35 },
  guest_v1: { light: 0.5, walkable: 0.5, yard: 0.5, value: 0.5, character: 0.5, open: 0.5, quiet: 0.5 },
}

export const WEIGHT_CAP = 1.4
const BUMP = 0.55

export const initialState = (profileId, filters = {}) => ({
  weights: { ...(START_WEIGHTS[profileId] ?? START_WEIGHTS.guest_v1) },
  filters, // HARD filters (design 10 §4): {maxPrice, minBeds, area} — never weights
  pinned: [], // LLM rerank (recommend action): these ids lead, in the agent's order
  dismissed: [],
  saved: [],
  showMore: false,
})

// Logistics facts (interview q_where/q_budget, "Budget band: 750k-900k") -> hard filters.
export function filtersFromMemories(memories) {
  const f = {}
  for (const m of memories ?? []) {
    const band = /Budget band:\s*(?:under\s*|around\s*)?(\d{3,4})k(?:-(\d{3,4})k)?/i.exec(m.text ?? '')
    if (band) f.maxPrice = (band[2] ? +band[2] : +band[1]) * 1000
    if (/family with kids/i.test(m.text ?? '')) f.minBeds = 3
  }
  return f
}

const passesFilters = (l, f = {}) => {
  if (f.maxPrice && parseInt(l.price.replace(/\D/g, ''), 10) > f.maxPrice) return false
  if (f.minBeds && l.beds < f.minBeds) return false
  return true
}

const byId = (id) => LISTINGS.find((l) => l.listing_id === id)

export function score(l, w) {
  let s = 0, t = 0
  for (const k in w) { s += (l.features?.[k] ?? 0) * w[k]; t += w[k] }
  return t ? s / t : 0
}

export function rankIds(weights, dismissed, filters) {
  return LISTINGS.filter((l) => !dismissed.includes(l.listing_id) && passesFilters(l, filters))
    .map((l) => ({ id: l.listing_id, s: score(l, weights) }))
    .sort((a, b) => b.s - a.s)
    .map((x) => x.id)
}

// Pinned ids lead in the agent's order (its explicit picks bypass the hard
// filters — it knows the budget and chose anyway); weights rank the rest.
function orderedIds(state) {
  const pinned = (state.pinned ?? []).filter((id) => byId(id) && !state.dismissed.includes(id))
  const rest = rankIds(state.weights, state.dismissed, state.filters)
  return [...pinned, ...rest.filter((id) => !pinned.includes(id))]
}

export function fitChips(listing, weights, n) {
  return Object.keys(weights)
    .filter((k) => (listing.features?.[k] ?? 0) >= 0.7)
    .sort((a, b) => listing.features[b] * weights[b] - listing.features[a] * weights[a])
    .slice(0, n)
    .map((k) => FEATURES[k].fit)
}

export function tradeChip(listing, weights) {
  const k = Object.keys(weights)
    .sort((a, b) => (1 - (listing.features?.[b] ?? 0)) * weights[b] - (1 - (listing.features?.[a] ?? 0)) * weights[a])[0]
  return (listing.features?.[k] ?? 0) < 0.55 ? TRADE[k] : null
}

function rankedSet(state, badges = {}, intro = null) {
  const ordered = orderedIds(state)
  // never hide a card the agent explicitly recommended
  const count = state.showMore ? 5 : Math.min(5, Math.max(3, (state.pinned ?? []).length))
  return {
    intro: intro ?? 'that fit everything so far — my top pick first. Tell me what to change and I’ll re-rank live.',
    visible: ordered.slice(0, count),
    hasMore: !state.showMore && ordered.length > count,
    badges,
    weights: { ...state.weights },
  }
}

export function discover(profileId, state) {
  return { narration: null, set: rankedSet(state) }
}

// LLM rerank (design 10b unification, chat side): the agent's recommend action
// carries listing_ids best-match-first; pin them to the top of the set. The
// agent's reply is the narration, so none is returned here.
export function recommend(state, listingIds) {
  const ids = (listingIds ?? []).filter((id) => byId(id) && !state.dismissed.includes(id))
  if (!ids.length) return { state, set: rankedSet(state) }
  const before = orderedIds(state).slice(0, 3)
  const next = { ...state, pinned: ids, showMore: false }
  const after = orderedIds(next).slice(0, 3)

  const badges = {}
  after.forEach((id, i) => {
    const was = before.indexOf(id)
    if (was === -1) badges[id] = 'fresh'
    else if (was > i) badges[id] = 'moved'
  })
  return { state: next, set: rankedSet(next, badges) }
}

// Facts the agent saves mid-chat ("Natural light is non-negotiable") map onto
// the same feature weights the refine chips bump — preferences learned in
// conversation must visibly re-rank the cards, not just land in the rail.
const FACT_BUMPS = [
  [/natural light|sunlight|bright|airy|south-?facing|big windows/i, 'light'],
  [/walkab|on foot|walk to|car-?free|near (cafés|cafes|coffee|shops)/i, 'walkable'],
  [/yard|outdoor space|garden|\bdog\b/i, 'yard'],
  [/budget|cheaper|affordab|value|price/i, 'value'],
  [/character|charm|original|vintage|period|patina/i, 'character'],
  [/quiet|peaceful/i, 'quiet'],
  [/open (kitchen|plan|floor)|host|entertain/i, 'open'],
]

export function bumpsFromFacts(facts) {
  const keys = []
  for (const f of facts ?? [])
    for (const [re, k] of FACT_BUMPS)
      if (re.test(f.text ?? '') && !keys.includes(k)) keys.push(k)
  return keys
}

// Apply learned-preference bumps. quiet: the agent ALSO reranked explicitly
// this turn — its pins lead, so just shift the weights underneath, silently.
// Otherwise this is a chip-style refine: release pins, narrate, badge moves.
export function learn(state, bumpKeys, { quiet = false } = {}) {
  const before = orderedIds(state).slice(0, 3)
  const weights = { ...state.weights }
  for (const k of bumpKeys) weights[k] = Math.min(WEIGHT_CAP, (weights[k] ?? 0) + BUMP)
  const next = { ...state, weights, pinned: quiet ? state.pinned : [], showMore: false }
  if (quiet) return { state: next, narration: null, set: rankedSet(next) }

  const after = orderedIds(next).slice(0, 3)
  const badges = {}
  after.forEach((id, i) => {
    const was = before.indexOf(id)
    if (was === -1) badges[id] = 'fresh'
    else if (was > i) badges[id] = 'moved'
  })
  const names = bumpKeys.map((k) => FEATURES[k].label).join(' and ')
  const newLead = byId(after[0]).title
  let narration = `Weighting **${names}** higher from here on. `
  narration += after[0] !== before[0] ? `**${newLead}** moves to the top.` : `**${newLead}** still leads.`
  return { state: next, narration, set: rankedSet(next, badges) }
}

// reaction/refine: returns { state, narration, set } — caller commits state.
// A chip click re-steers the weighted model, so it releases any LLM pins —
// otherwise the pinned order would swallow the bump and nothing would move.
export function refine(state, bumpKey, say) {
  const before = orderedIds(state).slice(0, 3)
  const weights = { ...state.weights, [bumpKey]: Math.min(WEIGHT_CAP, (state.weights[bumpKey] ?? 0) + BUMP) }
  const next = { ...state, weights, pinned: [], showMore: false }
  const after = orderedIds(next).slice(0, 3)

  const badges = {}
  after.forEach((id, i) => {
    const was = before.indexOf(id)
    if (was === -1) badges[id] = 'fresh'
    else if (was > i) badges[id] = 'moved'
  })

  const newLead = byId(after[0]).title
  const entered = after.find((id) => !before.includes(id))
  let narration = `Got it — weighting **${say}** higher. `
  narration += after[0] !== before[0] ? `**${newLead}** moves to the top` : `**${newLead}** still leads`
  narration += entered ? `, and **${byId(entered).title}** comes into the mix.` : `, with the order reshuffled.`

  return { state: next, narration, set: rankedSet(next, badges) }
}

export function dismiss(state, listingId) {
  const next = {
    ...state,
    dismissed: [...state.dismissed, listingId],
    pinned: (state.pinned ?? []).filter((id) => id !== listingId),
  }
  const remaining = orderedIds(next)
  const filler = remaining[2]
  const badges = filler ? { [filler]: 'fresh' } : {}
  const narration = `Noted — I’ll steer away from places like that.${filler ? ` **${byId(filler).title}** takes its spot.` : ''}`
  return { state: next, narration, set: rankedSet(next, badges) }
}

export function toggleSave(state, listingId) {
  const saved = state.saved.includes(listingId)
    ? state.saved.filter((x) => x !== listingId)
    : [...state.saved, listingId]
  return { ...state, saved }
}

export function showMore(state) {
  const next = { ...state, showMore: true }
  return { state: next, set: rankedSet(next) }
}
