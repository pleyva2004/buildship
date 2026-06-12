// The ONLY A↔B runtime coupling: asset paths by filename convention (design 05 §4).
// Every consumer must degrade gracefully when a file is missing.

export const rawPhoto = (room) => `/assets/listings/hero/raw/hero__${room}.jpg`

export const restyledPhoto = (room, profileId) =>
  `/assets/listings/hero/restyled/${profileId}/hero__${room}__${profileId}.png`

export const tourVideo = (profileId) => `/assets/listings/hero/video/${profileId}/tour.mp4`

// Branded inline placeholder for any missing render (no broken-image icons, ever).
export const PLACEHOLDER = (label = 'render landing soon') =>
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500">
      <rect width="100%" height="100%" fill="#E8E1D5"/>
      <text x="50%" y="50%" font-family="Georgia, serif" font-size="24" fill="#8A7E6D"
        text-anchor="middle" dominant-baseline="middle">${label}</text>
    </svg>`,
  )
