// API layer — talks to the FastAPI bridge; falls back to the local mock on ANY
// failure (server down, network off). The fallback IS the stage insurance:
// the app demos end-to-end with zero backend.

import { respond } from './mock/brain.js'
import { MEMORIES } from './mock/data.js'
import * as interviewMock from './mock/interview.js'

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
      new_facts: turn.new_facts ?? [],
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

// ---- active-learning loop (design 08 §1) -----------------------------------
// Mirrors agent/core.py next_question / record_answer / rerank. The mock twin
// is deterministic and pure — the interview + live re-rank demo with zero
// network. `answers` is the client-held session state: [{questionId, answer}].

export async function nextQuestion(profileId, answers) {
  try {
    return await post('/api/interview/next', { profile_id: profileId, answers })
  } catch {
    return interviewMock.nextQuestion(answers)
  }
}

export async function recordAnswer(profileId, answers, questionId, answer) {
  try {
    return await post('/api/interview/answer', {
      profile_id: profileId,
      answers,
      question_id: questionId,
      answer,
    })
  } catch {
    return interviewMock.recordAnswer(answers, questionId, answer)
  }
}

export function rankListings(answers) {
  // pure client-side scoring over the cached pool — never a network call
  return interviewMock.rankListings(answers)
}

// ---- memory hygiene (design 08 §2 (03): confirm / edit / remove) ------------
// Best-effort against the live agent (which cleans mem0); silent on mock.

export async function updateMemory(profileId, memoryId, text) {
  try {
    await post(`/api/memory/${profileId}/update`, { memory_id: memoryId, text })
  } catch {
    /* mock memories live in app state */
  }
}

export async function deleteMemory(profileId, memoryId) {
  try {
    await post(`/api/memory/${profileId}/delete`, { memory_id: memoryId })
  } catch {
    /* mock memories live in app state */
  }
}
