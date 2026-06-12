// API layer — talks to the FastAPI bridge; falls back to the local mock on ANY
// failure (server down, network off). The fallback IS the stage insurance:
// the app demos end-to-end with zero backend.

import { respond } from './mock/brain.js'
import { MEMORIES } from './mock/data.js'

async function post(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

async function get(path) {
  const r = await fetch(path)
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json()
}

export async function chat(profileId, message) {
  try {
    return await post('/api/chat', { profile_id: profileId, message })
  } catch {
    const turn = respond(message)
    const all = MEMORIES[profileId] ?? []
    return {
      reply: turn.reply,
      action: turn.action,
      recalled: all.filter((m) => turn.recalled.includes(m.id)),
    }
  }
}

export async function getContext(profileId) {
  try {
    const data = await get(`/api/context/${profileId}`)
    return data.memories
  } catch {
    return MEMORIES[profileId] ?? []
  }
}

export async function resetSession(profileId) {
  try {
    await post(`/api/reset/${profileId}`, {})
  } catch {
    /* mock has no session state */
  }
}
