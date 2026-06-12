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
  value: 'above budget', character: 'newer build', open: 'closed-off kitchen', quiet: 'busier street',
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

export const initialState = (profileId) => ({
  weights: { ...(START_WEIGHTS[profileId] ?? START_WEIGHTS.guest_v1) },
  dismissed: [],
  saved: [],
  showMore: false,
})

const byId = (id) => LISTINGS.find((l) => l.listing_id === id)

export function score(l, w) {
  let s = 0, t = 0
  for (const k in w) { s += (l.features?.[k] ?? 0) * w[k]; t += w[k] }
  return t ? s / t : 0
}

export function rankIds(weights, dismissed) {
  return LISTINGS.filter((l) => !dismissed.includes(l.listing_id))
    .map((l) => ({ id: l.listing_id, s: score(l, weights) }))
    .sort((a, b) => b.s - a.s)
    .map((x) => x.id)
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
  const ordered = rankIds(state.weights, state.dismissed)
  return {
    intro: intro ?? 'homes that fit everything so far — my top pick first. Tell me what to change and I’ll re-rank live.',
    visible: ordered.slice(0, state.showMore ? 5 : 3),
    hasMore: !state.showMore && ordered.length > 3,
    badges,
    weights: { ...state.weights },
  }
}

export function discover(profileId, state) {
  return { narration: null, set: rankedSet(state) }
}

// reaction/refine: returns { state, narration, set } — caller commits state.
export function refine(state, bumpKey, say) {
  const before = rankIds(state.weights, state.dismissed).slice(0, 3)
  const weights = { ...state.weights, [bumpKey]: Math.min(WEIGHT_CAP, (state.weights[bumpKey] ?? 0) + BUMP) }
  const next = { ...state, weights, showMore: false }
  const after = rankIds(weights, state.dismissed).slice(0, 3)

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
  const next = { ...state, dismissed: [...state.dismissed, listingId] }
  const remaining = rankIds(next.weights, next.dismissed)
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
