// Area intel — mock twin of agent/mocks/areas.json (design 11). Canned
// neighborhood notes keyed to match LISTINGS neighborhoods; the stage-fallback
// baseline for "what VISTA researched". Live findings (area_research memories
// from mem0) take over per-hood as they land.

export const AREA_INTEL = {
  'Travis Heights':
    "Travis Heights is the walkable heart of south Austin — South Congress's cafés and music are 10-12 minutes on foot, and the Blunn Creek greenbelt threads right through the neighborhood for morning dog walks. Streets are leafy and slow, with a mix of original bungalows and newer builds.",
  Zilker:
    'Zilker trades a little polish for park life: Barton Springs Pool and the great lawn are effectively your backyard, and the dog scene at the off-leash trails is the best in the city. Interiors in the older craftsman stock run darker, but the porches earn their keep.',
  Mueller:
    "Mueller is master-planned calm — a weekend farmers market, the lake park loop, and wide sidewalks everywhere. It's quieter and newer than central Austin, with easy airport runs; walkability is good within the development, thinner beyond it.",
  'Hyde Park':
    "Hyde Park is old Austin: sidewalks under pecan trees, front porches, Shipe Park and its pool around the corner, and Quack's bakery as the de facto living room. Quiet streets, strong character, smaller lots.",
  'East Austin':
    "East Austin is the walk-everywhere bet — coffee, galleries, and live music on foot along East 6th and East Cesar Chavez. It's the liveliest (and loudest) of the close-in options; yards are rare, rooftops are not.",
  'Circle C':
    "Circle C is south-west suburban: big lots, big yards, top-rated schools, and the Veloway and Lady Bird Johnson Wildflower Center nearby. You'll drive for coffee — the trade for space and quiet is car-dependence.",
  Clarksville:
    "Clarksville is one of Austin's oldest neighborhoods — storied homes, a tight grid you can walk, Fresh Plus on the corner, and Jeffrey's if the night calls for it. Premium prices for premium character, minutes from downtown.",
}

// First clause of an intel note — the compact form for alternate cards.
export const areaShort = (text) =>
  text.split(/—|;|:/)[0].trim().replace(/\.$/, '') + '.'

// researcher.py writes mem0 facts as "{area} — {note}" (focused passes:
// "{area} (for you) — {note}"). Returns {hood, note} or null.
export function parseAreaFact(text) {
  const m = /^(.+?)(?:\s*\(for you\))?\s+—\s+(.+)$/.exec(text ?? '')
  return m ? { hood: m[1], note: m[2] } : null
}
