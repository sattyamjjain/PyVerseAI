import { onRequest } from 'firebase-functions/https'
import { z } from 'zod'
import type { CollectionReference, DocumentReference } from 'firebase-admin/firestore'
import { db, FieldValue } from './lib/db.js'
import { REGION } from './lib/env.js'
import { applyCors, HttpError, parseBody, requireAuth, sendError } from './lib/http.js'
import { log, truncate } from './lib/log.js'

const restoreSchema = z.object({
  projectId: z.string().regex(/^[A-Za-z0-9_-]{1,64}$/),
  snapshotId: z.string().regex(/^[A-Za-z0-9_-]{1,64}$/),
})

async function writeSnapshotFiles(
  snapRef: DocumentReference,
  files: Map<string, string>,
): Promise<void> {
  let batch = db.batch()
  let ops = 0
  for (const [path, content] of files) {
    batch.set(snapRef.collection('files').doc(), { path, content })
    ops++
    if (ops >= 400) {
      await batch.commit()
      batch = db.batch()
      ops = 0
    }
  }
  if (ops > 0) await batch.commit()
}

async function loadFiles(col: CollectionReference): Promise<Map<string, string>> {
  const snap = await col.get()
  const map = new Map<string, string>()
  for (const doc of snap.docs) map.set(doc.data().path as string, doc.data().content as string)
  return map
}

/**
 * Restore a snapshot with v0-style append-only semantics:
 *  1. the current state is saved as a "backup" snapshot (that's the Undo),
 *  2. current files are replaced by the snapshot's files,
 *  3. the restored state is appended as a new "restore" snapshot.
 * Nothing in history is ever destroyed.
 */
export const restoreSnapshot = onRequest(
  { region: REGION, timeoutSeconds: 120, memory: '256MiB', maxInstances: 3 },
  async (req, res) => {
    if (applyCors(req, res)) return
    let uid: string | undefined
    try {
      if (req.method !== 'POST') throw new HttpError(405, 'method_not_allowed')
      ;({ uid } = await requireAuth(req))
      const body = parseBody(req, restoreSchema)

      const projectRef = db.doc(`projects/${body.projectId}`)
      const projectSnap = await projectRef.get()
      if (!projectSnap.exists || projectSnap.data()?.ownerUid !== uid) {
        throw new HttpError(404, 'project_not_found')
      }
      if (projectSnap.data()?.status === 'generating') {
        throw new HttpError(409, 'generation_in_progress')
      }
      const snapshotRef = projectRef.collection('snapshots').doc(body.snapshotId)
      const snapshotSnap = await snapshotRef.get()
      if (!snapshotSnap.exists) throw new HttpError(404, 'snapshot_not_found')
      const snapshotMeta = snapshotSnap.data()!

      const filesCol = projectRef.collection('files')
      const current = await loadFiles(filesCol)
      const target = await loadFiles(snapshotRef.collection('files'))
      if (target.size === 0) throw new HttpError(409, 'snapshot_empty')

      // 1. Backup of the current state.
      const backupRef = projectRef.collection('snapshots').doc()
      await backupRef.set({
        label: 'Backup before restore',
        promptExcerpt: '',
        fileCount: current.size,
        added: 0,
        removed: 0,
        createdAt: FieldValue.serverTimestamp(),
        kind: 'backup',
      })
      await writeSnapshotFiles(backupRef, current)

      // 2. Replace current files (update in place by path, delete extras).
      const existingDocs = await filesCol.get()
      const byPath = new Map(existingDocs.docs.map((d) => [d.data().path as string, d.ref]))
      let batch = db.batch()
      let ops = 0
      const flush = async () => {
        if (ops > 0) {
          await batch.commit()
          batch = db.batch()
          ops = 0
        }
      }
      for (const [path, ref] of byPath) {
        if (!target.has(path)) {
          batch.delete(ref)
          if (++ops >= 400) await flush()
        }
      }
      for (const [path, content] of target) {
        const ref = byPath.get(path) ?? filesCol.doc()
        batch.set(ref, { path, content, updatedAt: FieldValue.serverTimestamp() })
        if (++ops >= 400) await flush()
      }
      await flush()

      // 3. Append the restored state as a new snapshot (linear history).
      const restoredRef = projectRef.collection('snapshots').doc()
      await restoredRef.set({
        label: `Restored: ${truncate(snapshotMeta.label ?? 'snapshot', 60)}`,
        promptExcerpt: (snapshotMeta.promptExcerpt as string | undefined) ?? '',
        fileCount: target.size,
        added: 0,
        removed: 0,
        createdAt: FieldValue.serverTimestamp(),
        kind: 'restore',
      })
      await writeSnapshotFiles(restoredRef, target)

      await projectRef.update({ status: 'ready', updatedAt: FieldValue.serverTimestamp() })
      log.info('snapshot restored', { uid, projectId: body.projectId, snapshotId: body.snapshotId })
      res.json({ ok: true, backupSnapshotId: backupRef.id, restoredSnapshotId: restoredRef.id })
    } catch (err) {
      sendError(res, err, 'restoreSnapshot', uid)
    }
  },
)
