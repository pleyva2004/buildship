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
    lighting_mood: 'bright, cool daylight, airy and even',
  },
  pablo_v1: {
    profile_id: 'pablo_v1',
    name: 'Pablo',
    aesthetic_name: 'warm mid-century modern',
    palette_hex: ['#C8A27A', '#2F3E46', '#E9E4DB', '#7A5C3E'],
    materials: ['walnut', 'boucle', 'brushed brass', 'wool'],
    lighting_mood: 'warm, golden hour, soft shadows',
  },
}

// Mirrors agent/clients/mem0_client.py flatten_profile() output.
export const MEMORIES = {
  jake_v1: [
    { id: 'j1', category: 'life_situation', text: 'Jake: First-time buyer, relocating to Austin, works from home 3 days/week' },
    { id: 'j2', category: 'life_situation', text: 'Household: couple, no kids, one dog (Daisy)' },
    { id: 'j3', category: 'life_situation', text: 'Budget band: 750k-900k' },
    { id: 'j4', category: 'life_situation', text: 'Must-have: home office with real daylight' },
    { id: 'j5', category: 'life_situation', text: 'Must-have: walkable neighborhood' },
    { id: 'j6', category: 'life_situation', text: 'Must-have: outdoor space for the dog' },
    { id: 'j7', category: 'taste', text: 'bright and airy over cozy and dark' },
    { id: 'j8', category: 'taste', text: 'uncluttered, few but intentional objects' },
    { id: 'j9', category: 'taste', text: 'natural light is non-negotiable' },
    { id: 'j10', category: 'taste', text: 'pale woods, no heavy ornamentation' },
    { id: 'j11', category: 'mood_board', text: 'Mood board: “Scandinavian living rooms” (pinterest, via composio)' },
    { id: 'j12', category: 'mood_board', text: 'Mood board: “minimalist oak kitchens” (pinterest, via composio)' },
  ],
  pablo_v1: [
    { id: 'p1', category: 'life_situation', text: 'Pablo: Trading up; design-led move, hosts dinners most weekends' },
    { id: 'p2', category: 'life_situation', text: 'Household: couple' },
    { id: 'p3', category: 'life_situation', text: 'Budget band: 800k-1.0M' },
    { id: 'p4', category: 'life_situation', text: 'Must-have: a dining room worth gathering in' },
    { id: 'p5', category: 'life_situation', text: 'Must-have: warm western light in the living room' },
    { id: 'p6', category: 'life_situation', text: 'Must-have: character over new-build polish' },
    { id: 'p7', category: 'taste', text: 'cozy and warm over bright and stark' },
    { id: 'p8', category: 'taste', text: 'walnut, brass, layered textiles' },
    { id: 'p9', category: 'taste', text: 'golden-hour light, soft shadows' },
    { id: 'p10', category: 'taste', text: 'rooms that feel collected, not staged' },
    { id: 'p11', category: 'mood_board', text: 'Mood board: “golden hour living” (pinterest, via composio)' },
    { id: 'p12', category: 'mood_board', text: 'Mood board: “mid-century dining rooms” (pinterest, via composio)' },
  ],
}

// Listing inventory — mirrors assets/listings/index.json (design 03 §2).
export const LISTINGS = [
  {
    listing_id: 'hero',
    title: 'Modern 4BR in Travis Heights',
    price: '$865,000',
    location: 'Austin, TX',
    beds: 4,
    baths: 3,
    sqft: 2410,
    hero: true,
    rooms: ['living', 'kitchen', 'primary_bed', 'office', 'dining', 'exterior'],
    match_notes: {
      jake_v1: ['office gets full morning light', 'walk to South Congress', 'fenced yard for Daisy'],
      pablo_v1: ['original wood detailing', 'big western light in the living room'],
    },
  },
  {
    listing_id: 'alt1',
    title: 'Craftsman 3BR in Zilker',
    price: '$799,000',
    location: 'Austin, TX',
    beds: 3,
    baths: 2,
    sqft: 1980,
    hero: false,
    rooms: [],
    match_notes: {
      jake_v1: ['great walk score', 'darker interiors — trade-off'],
      pablo_v1: ['warm character throughout'],
    },
  },
  {
    listing_id: 'alt2',
    title: 'New build 4BR in Mueller',
    price: '$845,000',
    location: 'Austin, TX',
    beds: 4,
    baths: 3,
    sqft: 2300,
    hero: false,
    rooms: [],
    match_notes: {
      jake_v1: ['blank-canvas interiors', 'yard is small for Daisy'],
      pablo_v1: ['lacks the character you love'],
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
