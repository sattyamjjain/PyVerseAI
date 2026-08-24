/**
 * Firestore security-rules tests. Require the Firestore emulator:
 *   firebase emulators:start --only firestore --project demo-genesis
 * (or: firebase emulators:exec --only firestore "npm test")
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
  type RulesTestEnvironment,
} from '@firebase/rules-unit-testing'

const rulesPath = fileURLToPath(new URL('../../firestore.rules', import.meta.url))

async function emulatorUp(): Promise<boolean> {
  try {
    // The Firestore emulator answers "Ok" at its root; checking the body
    // avoids running the suite against some unrelated service on :8080.
    const res = await fetch('http://127.0.0.1:8080/')
    return (await res.text()).trim() === 'Ok'
  } catch {
    return false
  }
}

const up = await emulatorUp()

describe.skipIf(!up)('firestore security rules', () => {
  let env: RulesTestEnvironment

  beforeAll(async () => {
    env = await initializeTestEnvironment({
      projectId: 'demo-genesis-rules',
      firestore: {
        host: '127.0.0.1',
        port: 8080,
        rules: readFileSync(rulesPath, 'utf8'),
      },
    })
    await env.clearFirestore()
    // Seed server-owned docs (Admin SDK bypasses rules; here we use the
    // rules-disabled context for the same effect).
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await db.doc('projects/p1').set({
        ownerUid: 'alice',
        name: 'Alice project',
        description: '',
        locationId: null,
        status: 'ready',
        softDeleted: false,
      })
      await db.doc('projects/p1/files/f1').set({ path: 'index.html', content: '<p>hi</p>' })
      await db.doc('projects/p1/snapshots/s1').set({ label: 'gen', kind: 'generation', fileCount: 1 })
      await db.doc('hl_connections/alice').set({ accessToken: 'SECRET', locationId: 'loc1' })
      await db.doc('rate_limits/alice_gen_1').set({ n: 1 })
      await db.doc('hl_events/e1').set({ ownerUid: 'alice', type: 'contactCreated', summary: 'x' })
    })
  })

  afterAll(async () => {
    await env?.cleanup()
  })

  const alice = () => env.authenticatedContext('alice').firestore()
  const mallory = () => env.authenticatedContext('mallory').firestore()
  const anon = () => env.unauthenticatedContext().firestore()

  it('users: owner creates own profile with allowed keys only', async () => {
    await assertSucceeds(
      alice().doc('users/alice').set({ displayName: 'Alice', email: 'a@x.dev', createdAt: new Date() }),
    )
    await assertFails(
      mallory().doc('users/alice').set({ displayName: 'evil', email: 'm@x.dev', createdAt: new Date() }),
    )
    await assertFails(
      alice()
        .doc('users/alice2')
        .set({ displayName: 'A', email: 'a@x.dev', createdAt: new Date() }),
    )
  })

  it('users: client cannot forge the hl connection mirror', async () => {
    await assertFails(
      alice().doc('users/alice').set({
        displayName: 'Alice',
        email: 'a@x.dev',
        createdAt: new Date(),
        hl: { status: 'connected', locationId: 'stolen' },
      }),
    )
    await assertFails(
      alice().doc('users/alice').update({ hl: { status: 'connected' } }),
    )
    await assertSucceeds(alice().doc('users/alice').update({ displayName: 'Alice 2' }))
  })

  it('hl_connections and rate_limits are invisible to clients', async () => {
    await assertFails(alice().doc('hl_connections/alice').get())
    await assertFails(alice().doc('hl_connections/alice').set({ accessToken: 'x' }))
    await assertFails(alice().doc('rate_limits/alice_gen_1').get())
    await assertFails(anon().doc('hl_connections/alice').get())
  })

  it('projects: owner-scoped CRUD with validation', async () => {
    await assertSucceeds(alice().doc('projects/p1').get())
    await assertFails(mallory().doc('projects/p1').get())
    await assertSucceeds(
      alice().doc('projects/p2').set({
        ownerUid: 'alice',
        name: 'New app',
        description: 'demo',
        locationId: null,
        status: 'draft',
        softDeleted: false,
        createdAt: new Date(),
        updatedAt: new Date(),
      }),
    )
    // Wrong ownerUid on create
    await assertFails(
      mallory().doc('projects/p3').set({
        ownerUid: 'alice',
        name: 'forged',
        description: '',
        softDeleted: false,
      }),
    )
    // Ownership transfer blocked; server-only fields blocked
    await assertFails(alice().doc('projects/p1').update({ ownerUid: 'mallory' }))
    await assertFails(alice().doc('projects/p1').update({ status: 'generating' }))
    await assertSucceeds(
      alice().doc('projects/p1').update({ name: 'Renamed', updatedAt: new Date() }),
    )
    await assertSucceeds(
      alice().doc('projects/p1').update({ softDeleted: true, updatedAt: new Date() }),
    )
    await assertSucceeds(
      alice().doc('projects/p1').update({ softDeleted: false, updatedAt: new Date() }),
    )
    await assertFails(alice().doc('projects/p1').delete())
  })

  it('files: owner may edit content only; no create/delete from clients', async () => {
    await assertSucceeds(alice().doc('projects/p1/files/f1').get())
    await assertFails(mallory().doc('projects/p1/files/f1').get())
    await assertSucceeds(
      alice().doc('projects/p1/files/f1').update({ content: '<p>edited</p>', updatedAt: new Date() }),
    )
    await assertFails(
      alice().doc('projects/p1/files/f1').update({ path: 'evil.js', content: 'x', updatedAt: new Date() }),
    )
    await assertFails(
      alice().doc('projects/p1/files/f2').set({ path: 'new.js', content: 'x', updatedAt: new Date() }),
    )
    await assertFails(alice().doc('projects/p1/files/f1').delete())
    // Oversized content rejected
    await assertFails(
      alice()
        .doc('projects/p1/files/f1')
        .update({ content: 'x'.repeat(200_001), updatedAt: new Date() }),
    )
  })

  it('messages: append-only, user role only from clients', async () => {
    await assertSucceeds(
      alice()
        .doc('projects/p1/messages/m1')
        .set({ role: 'user', content: 'build me an app', createdAt: new Date() }),
    )
    await assertFails(
      alice()
        .doc('projects/p1/messages/m2')
        .set({ role: 'assistant', content: 'fake response', createdAt: new Date() }),
    )
    await assertFails(alice().doc('projects/p1/messages/m1').update({ content: 'edited' }))
    await assertFails(alice().doc('projects/p1/messages/m1').delete())
    await assertFails(
      mallory()
        .doc('projects/p1/messages/m9')
        .set({ role: 'user', content: 'intruder', createdAt: new Date() }),
    )
  })

  it('snapshots: readable by owner, never writable by clients', async () => {
    await assertSucceeds(alice().doc('projects/p1/snapshots/s1').get())
    await assertFails(mallory().doc('projects/p1/snapshots/s1').get())
    await assertFails(alice().doc('projects/p1/snapshots/s2').set({ label: 'forged' }))
  })

  it('hl_events: owner-filtered reads, no writes', async () => {
    await assertSucceeds(alice().doc('hl_events/e1').get())
    await assertFails(mallory().doc('hl_events/e1').get())
    await assertFails(alice().doc('hl_events/e2').set({ ownerUid: 'alice', type: 'x' }))
  })
})

if (!up) {
  it('rules tests skipped — Firestore emulator not running on :8080', () => {
    expect(up).toBe(false)
  })
}
