// Mock conversation brain — mirrors agent/mocks/turns.json + the action/recall
// shape the real /api/chat endpoint will return (design 04). Swap point: api.js.

const TURNS = [
  {
    stage: 'S1',
    keywords: ['austin'],
    recalled: ['j1', 'j2', 'j11'],
    action: null,
    reply:
      "Welcome back, Jake — Austin, finally! Since you're working from home three days a week, I've been prioritizing places with a daylight office, and I know Daisy needs a real yard. Give me a second to pull what's on the market that actually fits you — not just your filters.",
  },
  {
    stage: 'S2',
    keywords: ['find'],
    recalled: ['j4', 'j9', 'j10'],
    action: { type: 'recommend', listing_ids: ['hero', 'alt1', 'alt2'] },
    reply:
      "Three worth your time, but one stands out: a 4BR in Travis Heights — bright corner lot, the office gets full morning light, fenced yard, and you can walk to South Congress. The other two are solid on price but darker inside, and you've told me bright-and-airy is non-negotiable.",
  },
  {
    stage: 'S3',
    keywords: ['show', 'version'],
    recalled: ['j4', 'j5', 'j7'],
    action: { type: 'generate_tour', listing_id: 'hero' },
    reply:
      'Generating your tour of the Travis Heights house now — same rooms, same architecture, restyled to your taste: pale oak, linen, that bright Scandinavian calm you keep pinning.',
  },
]

const DEFAULT_REPLY =
  "Tell me more about what you're looking for — neighborhood, light, how you actually live day to day — and I'll match it against what I already know about you.";

// Keyword backstop (design 04 §2): the generate moment can never fail to fire.
const GENERATE_RE = /(show me|my version|my style)/i

export function respond(userText) {
  const text = userText.toLowerCase()
  if (GENERATE_RE.test(text)) return TURNS[2]
  for (const turn of TURNS) {
    if (turn.keywords.every((kw) => text.includes(kw))) return turn
  }
  return { stage: 'NONE', recalled: [], action: null, reply: DEFAULT_REPLY }
}
