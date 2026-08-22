#!/usr/bin/env node
/**
 * Genesis generation integration harness (runs against local emulators).
 *
 * Usage:
 *   node scripts/gen-test.mjs gen "build a contact dashboard with search"
 *   node scripts/gen-test.mjs gen "add a detail panel" --project <projectId>   # refinement
 *   node scripts/gen-test.mjs restore <projectId>                              # restore latest snapshot
 *   node scripts/gen-test.mjs events <projectId>                               # dump project state
 *
 * Requires: emulators running (auth/functions/firestore, --project demo-genesis)
 * and ANTHROPIC_API_KEY set in functions/.secret.local for `gen`.
 */

const BASE = 'http://127.0.0.1:5001/demo-genesis/us-central1'
const AUTH = 'http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1'
const FS = 'http://127.0.0.1:8080/v1/projects/demo-genesis/databases/(default)/documents'
const ORIGIN = 'http://localhost:5173'
const EMAIL = 'harness@test.dev'
const PASSWORD = 'secret123'

const [, , cmd = 'gen', ...rest] = process.argv

async function main() {
  const { idToken, uid } = await signIn()
  await ensureConnected(idToken)

  if (cmd === 'gen') {
    const promptArg = rest.filter((a) => !a.startsWith('--') && rest[rest.indexOf(a) - 1] !== '--project')
    const prompt = promptArg[0] ?? 'Build a contact dashboard with search and a list of upcoming appointments.'
    const projectFlag = rest.indexOf('--project')
    const model = rest.includes('--best') ? 'best' : 'fast'
    let projectId = projectFlag >= 0 ? rest[projectFlag + 1] : null
    if (!projectId) projectId = await createProject(idToken, uid, `Harness ${new Date().toISOString().slice(11, 19)}`)
    console.log(`project: ${projectId}  model: ${model}`)
    await writeUserMessage(idToken, projectId, prompt)
    await runGeneration(idToken, projectId, prompt, model)
    await dumpProject(idToken, projectId)
  } else if (cmd === 'restore') {
    const projectId = rest[0]
    if (!projectId) throw new Error('restore needs a projectId')
    const snaps = await listDocs(idToken, `projects/${projectId}/snapshots`)
    if (snaps.length === 0) throw new Error('no snapshots')
    snaps.sort((a, b) => (a.createTime < b.createTime ? 1 : -1))
    const target = snaps[snaps.length - 1] // oldest
    const sid = target.name.split('/').pop()
    console.log(`restoring oldest snapshot ${sid} (${snaps.length} total)`)
    const res = await fetch(`${BASE}/restoreSnapshot`, {
      method: 'POST',
      headers: headers(idToken),
      body: JSON.stringify({ projectId, snapshotId: sid }),
    })
    console.log(res.status, await res.text())
    await dumpProject(idToken, projectId)
  } else if (cmd === 'events') {
    const projectId = rest[0]
    await dumpProject(idToken, projectId)
  } else {
    throw new Error(`unknown command ${cmd}`)
  }
}

function headers(idToken) {
  return { 'Content-Type': 'application/json', Origin: ORIGIN, Authorization: `Bearer ${idToken}` }
}

async function signIn() {
  let res = await fetch(`${AUTH}/accounts:signInWithPassword?key=fake`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD, returnSecureToken: true }),
  })
  if (!res.ok) {
    res = await fetch(`${AUTH}/accounts:signUp?key=fake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: EMAIL, password: PASSWORD, returnSecureToken: true }),
    })
  }
  const data = await res.json()
  if (!data.idToken) throw new Error(`auth failed: ${JSON.stringify(data)}`)
  return { idToken: data.idToken, uid: data.localId }
}

async function ensureConnected(idToken) {
  const start = await fetch(`${BASE}/hlAuthStart`, {
    method: 'POST',
    headers: headers(idToken),
    body: '{}',
  })
  const { url, error } = await start.json()
  if (error === 'rate_limited') return // already connected enough times this hour
  if (!url) throw new Error('hlAuthStart failed')
  await fetch(url) // mock callback completes the connection
}

// ── Firestore REST helpers (client-authed; rules apply) ─────────────────────
const S = (v) => ({ stringValue: v })
const B = (v) => ({ booleanValue: v })
const TS = () => ({ timestampValue: new Date().toISOString() })

async function createProject(idToken, uid, name) {
  const res = await fetch(`${FS}/projects`, {
    method: 'POST',
    headers: headers(idToken),
    body: JSON.stringify({
      fields: {
        ownerUid: S(uid),
        name: S(name),
        description: S('integration harness project'),
        locationId: { nullValue: null },
        status: S('draft'),
        softDeleted: B(false),
        createdAt: TS(),
        updatedAt: TS(),
      },
    }),
  })
  const data = await res.json()
  if (!data.name) throw new Error(`project create failed: ${JSON.stringify(data)}`)
  return data.name.split('/').pop()
}

async function writeUserMessage(idToken, projectId, content) {
  await fetch(`${FS}/projects/${projectId}/messages`, {
    method: 'POST',
    headers: headers(idToken),
    body: JSON.stringify({ fields: { role: S('user'), content: S(content), createdAt: TS() } }),
  })
}

async function listDocs(idToken, path) {
  const res = await fetch(`${FS}/${path}?pageSize=300`, { headers: headers(idToken) })
  const data = await res.json()
  return data.documents ?? []
}

// ── SSE consumer ────────────────────────────────────────────────────────────
async function runGeneration(idToken, projectId, prompt, model) {
  const started = Date.now()
  const res = await fetch(`${BASE}/generate`, {
    method: 'POST',
    headers: { ...headers(idToken), Accept: 'text/event-stream' },
    body: JSON.stringify({ projectId, prompt, model }),
  })
  if (!res.ok || !res.body) {
    throw new Error(`generate HTTP ${res.status}: ${await res.text()}`)
  }
  const seen = []
  const fileBytes = new Map()
  let narrationChars = 0
  let buffer = ''
  const decoder = new TextDecoder()
  for await (const chunk of res.body) {
    buffer += decoder.decode(chunk, { stream: true })
    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      if (frame.startsWith(':')) continue // heartbeat
      const eventLine = frame.split('\n').find((l) => l.startsWith('event: '))
      const dataLine = frame.split('\n').find((l) => l.startsWith('data: '))
      if (!eventLine || !dataLine) continue
      const type = eventLine.slice(7).trim()
      const data = JSON.parse(dataLine.slice(6))
      seen.push(type)
      if (type === 'narration_delta') narrationChars += data.text.length
      else if (type === 'file_delta') fileBytes.set(data.path, (fileBytes.get(data.path) ?? 0) + data.content.length)
      else if (type === 'file_start') process.stdout.write(`\n  → ${data.path} (${data.action}) `)
      else if (type === 'file_complete') process.stdout.write(`✓ ${data.sizeBytes}B${data.truncated ? ' TRUNCATED' : ''}`)
      else if (type === 'generation_start') console.log(`generation ${data.generationId} [${data.model}] mode=${data.mode}`)
      else if (type === 'snapshot_created') console.log(`\n  snapshot ${data.snapshotId} (${data.filesChanged.length} files)`)
      else if (type === 'done') console.log(`  done: ${data.stopReason}, usage=${JSON.stringify(data.usage)}`)
      else if (type === 'error') console.log(`\n  ERROR [${data.code}] recoverable=${data.recoverable}: ${data.message}`)
    }
  }
  const secs = ((Date.now() - started) / 1000).toFixed(1)
  console.log(`\nstream closed after ${secs}s — events: ${summarize(seen)}; narration ${narrationChars} chars`)

  const required = ['generation_start']
  for (const r of required) if (!seen.includes(r)) throw new Error(`missing event: ${r}`)
  if (!seen.includes('done') && !seen.includes('error')) throw new Error('no terminal event')
  if (seen.includes('done') && !seen.includes('snapshot_created')) throw new Error('done without snapshot')
  const order = ['generation_start', 'file_start', 'snapshot_created']
  let last = -1
  for (const o of order) {
    const i = seen.indexOf(o)
    if (i !== -1 && i < last) throw new Error(`event out of order: ${o}`)
    if (i !== -1) last = i
  }
  console.log('event-sequence assertions passed ✓')
}

async function dumpProject(idToken, projectId) {
  const files = await listDocs(idToken, `projects/${projectId}/files`)
  const snaps = await listDocs(idToken, `projects/${projectId}/snapshots`)
  const msgs = await listDocs(idToken, `projects/${projectId}/messages`)
  console.log(`\nFirestore state — files: ${files.length}, snapshots: ${snaps.length}, messages: ${msgs.length}`)
  for (const f of files) {
    const path = f.fields?.path?.stringValue
    const len = f.fields?.content?.stringValue?.length ?? 0
    console.log(`  file ${path} (${len} chars)`)
  }
  for (const s of snaps) {
    console.log(`  snapshot [${s.fields?.kind?.stringValue}] ${s.fields?.label?.stringValue} files=${s.fields?.fileCount?.integerValue}`)
  }
}

function summarize(seen) {
  const counts = {}
  for (const s of seen) counts[s] = (counts[s] ?? 0) + 1
  return Object.entries(counts)
    .map(([k, v]) => (v > 1 ? `${k}×${v}` : k))
    .join(', ')
}

main().catch((err) => {
  console.error('HARNESS FAILED:', err.message)
  process.exit(1)
})
