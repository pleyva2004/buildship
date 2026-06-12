// Mock twin of the active-learning agent surface (design 08 §1):
//   next_question(answers)  → { id, prompt, chips[], optional }
//   record_answer(...)      → { new_facts[], reranked_listing_ids[] }
//   rank_listings(answers)  → ordered ids + met/unmet must-have chips
// Fully deterministic (mock-first rule, CLAUDE.md §7) — the loop demos with
// zero network. Re-rank is a pure scoring pass over the fixed 5-listing pool;
// never a fetch.

import { LISTINGS } from './data.js'

export const INTERVIEW_LENGTH = 5

// trait weights an answer contributes; `must` marks hard filters whose
// met/unmet state renders as chips (never a numeric score — design 08 §1).
const QUESTIONS = {
  q_who: {
    prompt: 'Who’s making this move with you?',
    chips: ['Just me', 'Me + partner', 'Family with kids', 'Partner + a dog'],
    optional: false,
    effects(answer) {
      const a = answer.toLowerCase()
      const out = { weights: {}, must: [], facts: [] }
      if (/dog|puppy|daisy/.test(a)) {
        out.weights.yard = 3
        out.must.push('yard')
        out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Household: ${answer}` })
        out.facts.push({ category: 'life_situation', provenance: 'inferred', text: 'Must-have: outdoor space for the dog' })
      } else if (/kids|family/.test(a)) {
        out.weights.yard = 2
        out.weights.quiet = 2
        out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Household: ${answer}` })
      } else {
        out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Household: ${answer}` })
      }
      return out
    },
    next: (answer) => (/dog|puppy|daisy/i.test(answer) ? 'q_dog' : 'q_saturday'),
  },

  q_dog: {
    prompt: 'Tell me about the dog — what do walks look like?',
    chips: ['Long daily walks', 'Quick trips + a real yard', 'Dog park regular'],
    optional: false,
    effects(answer) {
      const a = answer.toLowerCase()
      const out = { weights: { yard: 1 }, must: [], facts: [] }
      if (/walk/.test(a)) out.weights.walkable = 2
      if (/yard/.test(a)) { out.weights.yard = 3; out.must.push('yard') }
      if (/park/.test(a)) out.weights.parks = 2
      out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Dog routine: ${answer.toLowerCase()}` })
      return out
    },
    next: () => 'q_saturday',
  },

  q_saturday: {
    prompt: 'What does a great Saturday at home look like?',
    chips: ['Slow coffee and reading light', 'Hosting friends for dinner', 'Cooking a long meal', 'Out all day, home to recharge'],
    optional: false,
    effects(answer) {
      const a = answer.toLowerCase()
      const out = { weights: {}, must: [], facts: [] }
      if (/host|friends|dinner|guests/.test(a)) {
        out.weights.hosting = 3
        out.facts.push({ category: 'life_situation', provenance: 'stated', text: 'Hosts friends at home most weekends' })
        out.facts.push({ category: 'taste', provenance: 'inferred', text: 'Needs rooms that gather people' })
      } else if (/coffee|reading|light/.test(a)) {
        out.weights.bright = 2
        out.facts.push({ category: 'taste', provenance: 'inferred', text: 'Slow mornings — values reading light' })
      } else if (/cook|meal/.test(a)) {
        out.weights.hosting = 2
        out.facts.push({ category: 'life_situation', provenance: 'stated', text: 'Cooks long meals — the kitchen is the room' })
      } else {
        out.weights.quiet = 1
        out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Saturdays: ${answer.toLowerCase()}` })
      }
      return out
    },
    next: () => 'q_light',
  },

  q_light: {
    prompt: 'Bright and airy, or cozy and warm?',
    chips: ['Bright & airy', 'Cozy & warm', 'Somewhere between'],
    optional: false,
    effects(answer) {
      const a = answer.toLowerCase()
      const out = { weights: {}, must: [], facts: [] }
      if (/bright|airy/.test(a)) {
        out.weights.bright = 3
        out.weights.cozy = -2
        out.facts.push({ category: 'taste', provenance: 'stated', text: 'bright and airy over cozy and dark' })
      } else if (/cozy|warm/.test(a)) {
        out.weights.cozy = 3
        out.weights.character = 2
        out.facts.push({ category: 'taste', provenance: 'stated', text: 'cozy and warm over bright and stark' })
      } else {
        out.weights.bright = 1
        out.facts.push({ category: 'taste', provenance: 'stated', text: 'somewhere between bright and cozy' })
      }
      return out
    },
    next: () => 'q_dealbreaker',
  },

  q_dealbreaker: {
    prompt: 'Any deal-breakers I should never show you?',
    chips: ['No dark interiors', 'No tiny yards', 'No long commutes', 'No major renovations'],
    optional: true,
    effects(answer) {
      const a = answer.toLowerCase()
      const out = { weights: {}, must: [], facts: [] }
      if (/dark/.test(a)) { out.weights.bright = 2; out.must.push('bright') }
      if (/yard/.test(a)) { out.weights.yard = 2; out.must.push('yard') }
      if (/commute/.test(a)) { out.weights.walkable = 2; out.must.push('walkable') }
      if (/renovation/.test(a)) out.weights.turnkey = 2
      out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Deal-breaker: ${answer.toLowerCase()}` })
      return out
    },
    next: () => 'q_center',
  },

  q_center: {
    prompt: 'Where does life center for you?',
    chips: ['Walkable cafés and shops', 'Quiet streets', 'Near parks and trails', 'Close to downtown'],
    optional: true,
    effects(answer) {
      const a = answer.toLowerCase()
      const out = { weights: {}, must: [], facts: [] }
      if (/walk|caf|shop/.test(a)) { out.weights.walkable = 3; out.must.push('walkable') }
      if (/quiet/.test(a)) out.weights.quiet = 3
      if (/park|trail/.test(a)) out.weights.parks = 3
      if (/downtown/.test(a)) out.weights.downtown = 3
      out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Life centers on: ${answer.toLowerCase()}` })
      return out
    },
    next: () => null,
  },
}

const MUST_LABELS = {
  yard: 'real yard',
  bright: 'bright interiors',
  walkable: 'walkable',
}

// answers: [{ questionId, answer }] in order.
export function nextQuestion(answers) {
  if (answers.length >= INTERVIEW_LENGTH) return null
  if (answers.length === 0) {
    return { id: 'q_who', ...pick(QUESTIONS.q_who), asked: 1, total: INTERVIEW_LENGTH }
  }
  const last = answers[answers.length - 1]
  const id = QUESTIONS[last.questionId]?.next(last.answer)
  if (!id) return null
  return { id, ...pick(QUESTIONS[id]), asked: answers.length + 1, total: INTERVIEW_LENGTH }
}

function pick(q) {
  return { prompt: q.prompt, chips: q.chips, optional: q.optional }
}

function accumulate(answers) {
  const weights = {}
  const must = new Set()
  for (const { questionId, answer } of answers) {
    const q = QUESTIONS[questionId]
    if (!q) continue
    const fx = q.effects(answer)
    for (const [trait, w] of Object.entries(fx.weights)) {
      weights[trait] = (weights[trait] ?? 0) + w
    }
    fx.must.forEach((t) => must.add(t))
  }
  return { weights, must }
}

// Pure scoring pass over the already-fetched pool (design 08 §1) — score is
// internal only; the UI renders order + movement + must-have chips, never a %.
// Ties break price-ascending: with zero answers the panel reads as a neutral
// price sort, and the right home visibly CLIMBS as the interview learns.
export function rankListings(answers) {
  const { weights, must } = accumulate(answers)
  const scored = LISTINGS.map((l) => {
    let score = 0
    for (const t of l.traits) score += weights[t] ?? 0
    for (const m of must) if (!l.traits.includes(m)) score -= 4 // unmet hard filter sinks it
    return { l, score, price: parseInt(l.price.replace(/\D/g, ''), 10) }
  })
  scored.sort((a, b) => b.score - a.score || a.price - b.price)
  return scored.map(({ l }) => ({
    listing_id: l.listing_id,
    met: [...must].filter((m) => l.traits.includes(m)).map((m) => MUST_LABELS[m] ?? m),
    unmet: [...must].filter((m) => !l.traits.includes(m)).map((m) => MUST_LABELS[m] ?? m),
  }))
}

export function recordAnswer(answers, questionId, answer) {
  const fx = QUESTIONS[questionId]?.effects(answer) ?? { facts: [] }
  const all = [...answers, { questionId, answer }]
  return {
    new_facts: fx.facts,
    ranked: rankListings(all),
    next: nextQuestion(all),
  }
}
