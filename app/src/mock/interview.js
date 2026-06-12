// Mock twin of the active-learning agent surface (design 08 §1):
//   next_question(answers)  → { id, prompt, chips[], optional }
//   record_answer(...)      → { new_facts[], reranked_listing_ids[] }
//   rank_listings(answers)  → ordered ids + met/unmet must-have chips
// Fully deterministic (mock-first rule, CLAUDE.md §7) — the loop demos with
// zero network. Re-rank is a pure scoring pass over the fixed 5-listing pool;
// never a fetch.

import { LISTINGS } from './data.js'

export const INTERVIEW_LENGTH = 7

// trait weights an answer contributes; `must` marks hard filters whose
// met/unmet state renders as chips (never a numeric score — design 08 §1).
const BUDGET_RE = /\$?(\d{3,4})\s*k?(?:\s*[-–to]+\s*\$?(\d{3,4})\s*k?)?/i

const HOODS_RE = /travis heights|zilker|mueller|hyde park|east austin|east 6th|circle c|clarksville/i

function fxWhere(raw) {
  const a = raw.toLowerCase()
  const out = { weights: {}, must: [], facts: [] }
  if (/close in|central|downtown|walkable/.test(a)) out.weights.walkable = 2
  if (/suburb|quieter|circle c/.test(a)) out.weights.quiet = 2
  const hood = HOODS_RE.exec(raw)
  let area = null
  if (hood) area = hood[0].replace(/\b\w/g, (c) => c.toUpperCase())
  else if (/austin/.test(a)) area = /close in|central/.test(a) ? 'Austin — close in' : 'Austin'
  if (area) out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Area: ${area}` })
  return out
}

function fxBudget(raw) {
  const a = raw.toLowerCase()
  const out = { weights: {}, must: [], facts: [] }
  const m = BUDGET_RE.exec(a)
  if (m && !/flexible/.test(a)) {
    const band = m[2] ? `${m[1]}k-${m[2]}k` : (/under|below|max/.test(a) ? `under ${m[1]}k` : `around ${m[1]}k`)
    out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Budget band: ${band}` })
  } else {
    out.facts.push({ category: 'life_situation', provenance: 'stated', text: `Budget: ${raw}` })
  }
  return out
}

function fxWho(raw) {
  const a = raw.toLowerCase()
  const seg = /(just me|me\s*(?:and|\+)\s*[^,.]+|family[^,.]*|couple[^,.]*|my partner[^,.]*|partner[^,.]*)/.exec(a)
  const household = seg ? seg[1].trim() : null
  const facts = household
    ? [{ category: 'life_situation', provenance: 'stated', text: `Household: ${household}` }]
    : []
  if (/dog|puppy|daisy/.test(a)) {
    return { weights: { yard: 3 }, must: ['yard'],
      facts: facts.concat([{ category: 'life_situation', provenance: 'inferred', text: 'Must-have: outdoor space for the dog' }]) }
  }
  if (/kids|family/.test(a)) return { weights: { yard: 2, quiet: 2 }, must: [], facts }
  return { weights: {}, must: [], facts }
}

const QUESTIONS = {
  // One conversational opener covers area + budget + household (Jake: "those
  // first few questions can be weaved into one"). Follow-ups only fill gaps.
  q_basics: {
    prompt: "Let's start with the basics — where are you looking, roughly what budget, and who's making the move with you?",
    chips: ['Austin close-in, ~$850k, me + partner + dog', 'Austin suburbs, under $750k, family of four', "Still deciding — let's talk"],
    optional: false,
    effects(answer) {
      const out = { weights: {}, must: [], facts: [] }
      for (const part of [fxWhere(answer), fxBudget(answer), fxWho(answer)]) {
        Object.assign(out.weights, part.weights)
        out.must.push(...part.must)
        out.facts.push(...part.facts)
      }
      if (!BUDGET_RE.test(answer)) out.facts = out.facts.filter((f) => !f.text.startsWith('Budget:'))
      return out
    },
    next: (a) => (!BUDGET_RE.test(a) ? 'q_budget' : /dog|puppy|daisy/i.test(a) ? 'q_dog' : 'q_saturday'),
  },

  q_budget: {
    prompt: 'And what budget are we working with, roughly?',
    chips: ['Under $750k', '$750k–900k', 'Up to $1M', 'Flexible for the right one'],
    optional: false,
    effects: fxBudget,
    next: () => 'q_saturday',
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
    next: () => 'q_anything',
  },

  // The standing final question — ALWAYS asked last, whatever path got here.
  // Open lane: whatever they say lands in the profile ("Also worth knowing").
  q_anything: {
    prompt: 'Last one — what else do you want out of your new home? Activities you love, things you want nearby, anything at all.',
    chips: ['Near a dog park', 'Space for hobbies', 'Good coffee close by', 'Room for guests'],
    optional: true,
    effects(answer) {
      const a = answer.toLowerCase()
      const out = { weights: {}, must: [], facts: [] }
      if (/park|trail|outdoor|hik/.test(a)) out.weights.parks = 2
      if (/walk|coffee|caf|restaurant|bar/.test(a)) out.weights.walkable = 2
      if (/quiet|peace/.test(a)) out.weights.quiet = 2
      if (/host|guest|friends|entertain/.test(a)) out.weights.hosting = 2
      if (/downtown|city/.test(a)) out.weights.downtown = 2
      if (/yard|garden/.test(a)) out.weights.yard = 2
      out.facts.push({ category: 'other', provenance: 'stated', text: `Also important: ${answer}` })
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
    return { id: 'q_basics', ...pick(QUESTIONS.q_basics), asked: 1, total: INTERVIEW_LENGTH }
  }
  const last = answers[answers.length - 1]
  const askedIds = new Set(answers.map((a) => a.questionId))
  let id = QUESTIONS[last.questionId]?.next(last.answer)
  // The last slot ALWAYS holds the open catch-all (and it never repeats).
  if (!id || answers.length === INTERVIEW_LENGTH - 1) {
    id = askedIds.has('q_anything') ? null : 'q_anything'
  }
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

// The panel's palette/aesthetic evolution (08b §7) — deterministic in mock:
// only the light/mood question moves the taste reading. Mirrored in
// agent/interview.py _profile_delta_mock — keep in lockstep.
export function profileDelta(questionId, answer) {
  if (questionId !== 'q_light') return { palette_add: [], aesthetic: null }
  const a = answer.toLowerCase()
  if (/bright|airy/.test(a)) {
    return { palette_add: ['#F5F3EF', '#D9D2C7', '#A7B5A0'], aesthetic: 'bright & airy modern' }
  }
  if (/cozy|warm/.test(a)) {
    return { palette_add: ['#C8A27A', '#7A5C3E', '#2F3E46'], aesthetic: 'warm & collected' }
  }
  return { palette_add: ['#E9E4DB'], aesthetic: null }
}

// Deterministic exit spec — mirrors agent/interview.py _spec_mock; keep in
// lockstep. Varies with the light/mood answer so cold runs aren't identical.
export function buildSpec(profileId, answers) {
  const light = (answers.find((a) => a.questionId === 'q_light')?.answer ?? '').toLowerCase()
  const hosts = answers.some((a) => /host|friends|dinner|guests/.test(a.answer.toLowerCase()))
  let spec
  if (/bright|airy/.test(light)) {
    spec = { aesthetic_name: 'bright & airy modern', palette_hex: ['#F5F3EF', '#D9D2C7', '#A7B5A0', '#1C1C1C'], materials: ['pale oak', 'linen', 'ceramic'], lighting_mood: 'bright, even daylight' }
  } else if (/cozy|warm/.test(light)) {
    spec = { aesthetic_name: 'warm & collected', palette_hex: ['#C8A27A', '#7A5C3E', '#2F3E46', '#E9E4DB'], materials: ['walnut', 'wool', 'brushed brass'], lighting_mood: 'warm, golden hour' }
  } else {
    spec = { aesthetic_name: 'balanced & natural', palette_hex: ['#E9E4DB', '#D9D2C7', '#A7B5A0', '#6F6557'], materials: ['oak', 'linen', 'stone'], lighting_mood: 'soft natural light' }
  }
  spec.furniture_vocabulary = (hosts ? ['long gathering table'] : []).concat(['low-profile sofa'])
  return {
    profile_id: profileId,
    ...spec,
    hard_constraints: ['preserve architecture', 'preserve windows/doors', 'preserve room geometry', 'no people'],
  }
}

// "I'm done" detection — mirrors agent/interview.py DONE_RE; keep in lockstep.
const DONE_RE = new RegExp(
  "\\b(i'?m (all )?done|that'?s (all|everything|enough|it)|nothing else" +
  "|no,? (that'?s|we'?re) (it|good|all)|we'?re good|wrap (it )?up|let'?s see (the )?homes)\\b", 'i')

function applyDoneSignal(next, allAnswers, answer) {
  if (!DONE_RE.test(answer)) return next
  const asked = new Set(allAnswers.map((a) => a.questionId))
  if (asked.has('q_anything') || asked.has('final.anything_else')) return null
  const q = QUESTIONS.q_anything
  return {
    id: 'q_anything', ...pick(q),
    asked: Math.min(allAnswers.length + 1, INTERVIEW_LENGTH), total: INTERVIEW_LENGTH,
  }
}

export function recordAnswer(answers, questionId, answer) {
  const fx = QUESTIONS[questionId]?.effects(answer) ?? { facts: [] }
  const all = [...answers, { questionId, answer }]
  return {
    new_facts: fx.facts,
    profile_delta: profileDelta(questionId, answer),
    ranked: rankListings(all),
    next: applyDoneSignal(nextQuestion(all), all, answer),
  }
}
