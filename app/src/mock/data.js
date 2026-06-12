// Mock data layer — mirrors what the agent API (design 04 §5) will return.
// Swap point: api.js. Specs mirror the frozen /specs/*.json (the A↔B contract).

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

// Memory rail content, grouped the way mem0_client.all() will group it (design 01).
export const MEMORIES = {
  jake_v1: [
    { id: 'j1', category: 'Life', text: 'Relocating to Austin with partner + dog (Daisy)' },
    { id: 'j2', category: 'Life', text: 'Works from home 3 days a week' },
    { id: 'j3', category: 'Life', text: 'Budget band $750k–900k' },
    { id: 'j4', category: 'Taste', text: 'Bright and airy over cozy and dark' },
    { id: 'j5', category: 'Taste', text: 'Pale woods, no heavy ornamentation' },
    { id: 'j6', category: 'Taste', text: 'Few but intentional objects' },
    { id: 'j7', category: 'Inspiration', text: 'Pinterest: “Scandinavian living rooms” (via Composio)' },
    { id: 'j8', category: 'Inspiration', text: 'Pinterest: “minimalist oak kitchens” (via Composio)' },
    { id: 'j9', category: 'Must-haves', text: 'Home office with real daylight' },
    { id: 'j10', category: 'Must-haves', text: 'Walkable neighborhood' },
    { id: 'j11', category: 'Must-haves', text: 'Outdoor space for the dog' },
  ],
  pablo_v1: [
    { id: 'p1', category: 'Life', text: 'Trading up; design-led move' },
    { id: 'p2', category: 'Life', text: 'Hosts dinners most weekends' },
    { id: 'p3', category: 'Taste', text: 'Cozy and warm over bright and stark' },
    { id: 'p4', category: 'Taste', text: 'Walnut, brass, layered textiles' },
    { id: 'p5', category: 'Inspiration', text: 'Mood board: “golden hour living” (via Composio)' },
    { id: 'p6', category: 'Must-haves', text: 'A dining room worth gathering in' },
    { id: 'p7', category: 'Must-haves', text: 'Warm western light in the living room' },
  ],
}

export const MEMORY_CATEGORIES = ['Life', 'Taste', 'Inspiration', 'Must-haves']

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
