// Mock data layer — byte-compatible with the agent API's shapes, so api.js can
// fall back to it transparently. Categories use the agent's canonical names
// (life_situation | taste | mood_board | constraint); MemoryRail maps labels.

export const SPECS = {
  jake_v1: {
    profile_id: 'jake_v1',
    name: 'Jake',
    aesthetic_name: 'bright Scandinavian minimalist',
    palette_hex: ['#F5F3EF', '#D9D2C7', '#1C1C1C', '#A7B5A0'],
    materials: ['pale oak', 'linen', 'matte black steel', 'ceramic'],
    furniture_vocabulary: ['low platform sofa', 'paper pendant lamp', 'open oak shelving'],
    lighting_mood: 'bright, cool daylight, airy and even',
    provenance: { conversations: 1, mood_boards: 2 },
  },
  pablo_v1: {
    profile_id: 'pablo_v1',
    name: 'Pablo',
    aesthetic_name: 'warm mid-century modern',
    palette_hex: ['#C8A27A', '#2F3E46', '#E9E4DB', '#7A5C3E'],
    materials: ['walnut', 'boucle', 'brushed brass', 'wool'],
    furniture_vocabulary: ['low-profile sofa', 'slatted credenza', 'arc floor lamp'],
    lighting_mood: 'warm, golden hour, soft shadows',
    provenance: { conversations: 1, mood_boards: 2 },
  },
  // Cold start — no seeded memories anywhere (mem0 mock seeds only jake/pablo).
  // Everything VISTA knows about Guest comes from THIS session's interview/chat.
  guest_v1: {
    profile_id: 'guest_v1',
    name: 'Guest',
    aesthetic_name: 'still discovering',
    palette_hex: ['#E8E1D5', '#D9D2C7', '#C8BFAF', '#6F6557'],
    materials: [],
    furniture_vocabulary: [],
    lighting_mood: 'to be discovered',
    provenance: { conversations: 0, mood_boards: 0 },
  },
}

// Mirrors agent/clients/mem0_client.py flatten_profile() output.
// provenance: 'stated' (user said it) | 'inferred' (model concluded it) |
// 'imported' (came in via Composio) — design 08 §2 (03) honest-provenance mark.
export const MEMORIES = {
  guest_v1: [],
  jake_v1: [
    { id: 'j1', category: 'life_situation', provenance: 'stated', text: 'Jake: First-time buyer, relocating to Austin, works from home 3 days/week' },
    { id: 'j2', category: 'life_situation', provenance: 'stated', text: 'Household: couple, no kids, one dog (Daisy)' },
    { id: 'j3', category: 'life_situation', provenance: 'stated', text: 'Budget band: 750k-900k' },
    { id: 'j4', category: 'life_situation', provenance: 'stated', text: 'Must-have: home office with real daylight' },
    { id: 'j5', category: 'life_situation', provenance: 'stated', text: 'Must-have: walkable neighborhood' },
    { id: 'j6', category: 'life_situation', provenance: 'inferred', text: 'Must-have: outdoor space for the dog' },
    { id: 'j7', category: 'taste', provenance: 'stated', text: 'bright and airy over cozy and dark' },
    { id: 'j8', category: 'taste', provenance: 'inferred', text: 'uncluttered, few but intentional objects' },
    { id: 'j9', category: 'taste', provenance: 'stated', text: 'natural light is non-negotiable' },
    { id: 'j10', category: 'taste', provenance: 'inferred', text: 'pale woods, no heavy ornamentation' },
    { id: 'j11', category: 'mood_board', provenance: 'imported', text: 'Mood board: “Scandinavian living rooms” (pinterest, via composio)' },
    { id: 'j12', category: 'mood_board', provenance: 'imported', text: 'Mood board: “minimalist oak kitchens” (pinterest, via composio)' },
  ],
  pablo_v1: [
    { id: 'p1', category: 'life_situation', provenance: 'stated', text: 'Pablo: Trading up; design-led move, hosts dinners most weekends' },
    { id: 'p2', category: 'life_situation', provenance: 'stated', text: 'Household: couple' },
    { id: 'p3', category: 'life_situation', provenance: 'stated', text: 'Budget band: 800k-1.0M' },
    { id: 'p4', category: 'life_situation', provenance: 'stated', text: 'Must-have: a dining room worth gathering in' },
    { id: 'p5', category: 'life_situation', provenance: 'stated', text: 'Must-have: warm western light in the living room' },
    { id: 'p6', category: 'life_situation', provenance: 'inferred', text: 'Must-have: character over new-build polish' },
    { id: 'p7', category: 'taste', provenance: 'stated', text: 'cozy and warm over bright and stark' },
    { id: 'p8', category: 'taste', provenance: 'inferred', text: 'walnut, brass, layered textiles' },
    { id: 'p9', category: 'taste', provenance: 'inferred', text: 'golden-hour light, soft shadows' },
    { id: 'p10', category: 'taste', provenance: 'stated', text: 'rooms that feel collected, not staged' },
    { id: 'p11', category: 'mood_board', provenance: 'imported', text: 'Mood board: “golden hour living” (pinterest, via composio)' },
    { id: 'p12', category: 'mood_board', provenance: 'imported', text: 'Mood board: “mid-century dining rooms” (pinterest, via composio)' },
  ],
}

// Listing inventory — mirrors assets/listings/index.json (design 03 §2).
// Pool of 5 (design 08 §1: "small candidate pool, 5–8") so the interview
// re-rank visibly reorders. `traits` are the pure-scoring inputs.
export const LISTINGS = [
  {
    listing_id: 'hero',
    title: 'Modern 4BR in Travis Heights',
    price: '$865,000',
    location: 'Austin, TX',
    neighborhood: 'Travis Heights',
    beds: 4,
    baths: 3,
    sqft: 2410,
    hero: true,
    traits: ['bright', 'yard', 'walkable', 'office', 'hosting'],
    rooms: ['living', 'kitchen', 'primary_bed', 'office', 'dining', 'exterior'],
    blurb:
      'A light-soaked corner lot two blocks off South Congress. Tall windows on the south and west faces, a real office with morning sun, and a fully fenced backyard under mature live oaks.',
    neighborhood_note:
      'Travis Heights is the walkable heart of south Austin — coffee, music, and the hike-and-bike trail all on foot.',
    match_notes: {
      jake_v1: ['office gets full morning light', 'walk to South Congress', 'fenced yard for Daisy'],
      pablo_v1: ['original wood detailing', 'big western light in the living room'],
    },
    tradeoff: {
      jake_v1: 'top of your budget band',
      pablo_v1: 'less period character than a true mid-century',
    },
  },
  {
    listing_id: 'alt1',
    title: 'Craftsman 3BR in Zilker',
    price: '$799,000',
    location: 'Austin, TX',
    neighborhood: 'Zilker',
    beds: 3,
    baths: 2,
    sqft: 1980,
    hero: false,
    traits: ['character', 'walkable', 'cozy', 'yard'],
    rooms: [],
    blurb:
      'A 1938 craftsman with its original trim and built-ins intact, a deep front porch, and a shaded backyard a short walk from Zilker Park.',
    neighborhood_note: 'Zilker trades a little polish for park life — Barton Springs is your backyard.',
    match_notes: {
      jake_v1: ['great walk score', 'darker interiors — trade-off'],
      pablo_v1: ['warm character throughout'],
    },
    tradeoff: {
      jake_v1: 'interiors run dark for your taste',
      pablo_v1: 'only one real gathering room',
    },
  },
  {
    listing_id: 'alt2',
    title: 'New build 4BR in Mueller',
    price: '$845,000',
    location: 'Austin, TX',
    neighborhood: 'Mueller',
    beds: 4,
    baths: 3,
    sqft: 2300,
    hero: false,
    traits: ['bright', 'turnkey', 'quiet', 'office'],
    rooms: [],
    blurb:
      'A 2023 build on a quiet Mueller street — bright, efficient, zero projects. Dedicated office, small turfed yard, two-car garage.',
    neighborhood_note: 'Mueller is master-planned calm: parks, a weekend farmers market, easy airport runs.',
    match_notes: {
      jake_v1: ['blank-canvas interiors', 'yard is small for Daisy'],
      pablo_v1: ['lacks the character you love'],
    },
    tradeoff: {
      jake_v1: 'yard is small for Daisy',
      pablo_v1: 'new-build polish, no patina',
    },
  },
  {
    listing_id: 'alt3',
    title: 'Bungalow 3BR in Hyde Park',
    price: '$815,000',
    location: 'Austin, TX',
    neighborhood: 'Hyde Park',
    beds: 3,
    baths: 2,
    sqft: 1890,
    hero: false,
    traits: ['character', 'quiet', 'yard', 'cozy', 'parks'],
    rooms: [],
    blurb:
      'A storybook 1920s bungalow under pecan trees: long-grain wood floors, a screened porch, and a deep lot on one of Hyde Park’s quietest streets.',
    neighborhood_note: 'Hyde Park is old Austin — sidewalks, front porches, Shipe Park around the corner.',
    match_notes: {
      jake_v1: ['big yard', 'small windows — trade-off'],
      pablo_v1: ['collected-not-staged energy', 'evening porch light'],
    },
    tradeoff: {
      jake_v1: 'smaller windows than you’d like',
      pablo_v1: 'dining room is on the small side',
    },
  },
  {
    listing_id: 'alt4',
    title: 'Corner loft 2BR near East 6th',
    price: '$759,000',
    location: 'Austin, TX',
    neighborhood: 'East Austin',
    beds: 2,
    baths: 2,
    sqft: 1540,
    hero: false,
    traits: ['bright', 'walkable', 'hosting', 'downtown'],
    rooms: [],
    blurb:
      'Double-height corner glazing, polished concrete, and a kitchen island built for a crowd — steps from East 6th’s restaurants.',
    neighborhood_note: 'East Austin is the walk-everywhere bet: coffee, galleries, live music on foot.',
    match_notes: {
      jake_v1: ['flooded with light', 'no yard — trade-off'],
      pablo_v1: ['great hosting kitchen', 'cooler palette than yours'],
    },
    tradeoff: {
      jake_v1: 'no outdoor space for Daisy',
      pablo_v1: 'concrete-and-glass runs cold',
    },
  },
]

export const ROOM_LABELS = {
  living: 'Living room',
  kitchen: 'Kitchen',
  primary_bed: 'Primary bedroom',
  office: 'Office',
  dining: 'Dining',
  exterior: 'Exterior',
}

// Which of YOUR cues shaped each room — tour per-room taste chips
// (design 08 §2 (08): ties the magic back to the rail).
export const ROOM_CUES = {
  jake_v1: {
    living: ['bright and airy', 'pale oak', 'few intentional objects'],
    kitchen: ['“minimalist oak kitchens” board', 'matte black steel'],
    primary_bed: ['linen', 'uncluttered calm'],
    office: ['must-have: real daylight', 'cool, even light'],
    dining: ['pale woods', 'no heavy ornamentation'],
    exterior: ['yard for Daisy', 'walk to South Congress'],
  },
  pablo_v1: {
    living: ['warm western light', 'walnut + boucle'],
    kitchen: ['brushed brass', 'collected, not staged'],
    primary_bed: ['layered textiles', 'soft shadows'],
    office: ['golden-hour light'],
    dining: ['must-have: a dining room worth gathering in', '“mid-century dining rooms” board'],
    exterior: ['character over polish'],
  },
}
