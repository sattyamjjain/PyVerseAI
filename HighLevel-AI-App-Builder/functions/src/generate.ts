import Anthropic from '@anthropic-ai/sdk'
import { onRequest } from 'firebase-functions/https'
import type { Response } from 'express'
import { z } from 'zod'
import { db, FieldValue, Timestamp } from './lib/db.js'
import { ANTHROPIC_API_KEY, HL_CLIENT_SECRET, isMockMode, REGION } from './lib/env.js'
import { applyCors, HttpError, parseBody, requireAuth, sendError } from './lib/http.js'
import { checkRateLimit, LIMITS } from './lib/rateLimit.js'
import { log, truncate } from './lib/log.js'
import { getConnection } from './hl/client.js'
import { GenParseError, GenStreamParser } from './genesis/parser.js'
import {
  artifactStub,
  buildMessages,
  buildRepairMessage,
  CONTINUE_PROMPT,
  MAX_OUTPUT_TOKENS,
  MAX_RESPONSE_SEGMENTS,
  MODEL_IDS,
  REPAIR_SYSTEM_PROMPT,
  SYSTEM_PROMPT,
  type HistoryTurn,
  type ProjectFileInput,
} from './genesis/prompt.js'
import { lineDiffCounts, validateGeneration } from './genesis/validate.js'
import { validateFilePath } from './shared/paths.js'
import type { SseErrorCode, SseEvent, StopReason, TokenUsage } from './shared/protocol.js'

const requestSchema = z.object({
  projectId: z.string().regex(/^[A-Za-z0-9_-]{1,64}$/),
  prompt: z.string().min(1).max(20_000),
  model: z.enum(['fast', 'best']),
})

/** Sequenced SSE writer with comment-frame heartbeats. */
class SseWriter {
  private seq = 0
  private heartbeat: ReturnType<typeof setInterval>
  closed = false

  constructor(private res: Response) {
    res.set({
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      'X-Accel-Buffering': 'no',
    })
    res.flushHeaders()
    this.heartbeat = setInterval(() => {
      if (!this.closed) this.res.write(': ping\n\n')
    }, 15_000)
  }

  send(event: SseEvent): void {
    if (this.closed) return
    this.seq += 1
    this.res.write(`id: ${this.seq}\nevent: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`)
  }

  end(): void {
    if (this.closed) return
    this.closed = true
    clearInterval(this.heartbeat)
    this.res.end()
  }
}

type OutboxItem =
  | { kind: 'narration'; text: string }
  | { kind: 'file_start'; path: string }
  | { kind: 'file_delta'; path: string; content: string }
  | { kind: 'file_complete'; path: string; content: string; truncated: boolean; changed: boolean }
  | { kind: 'file_deleted'; path: string }
  | { kind: 'app_start'; id?: string; title?: string }

interface GenState {
  previous: Map<string, string>
  merged: Map<string, string>
  docIds: Map<string, string>
  written: Array<{ path: string; content: string; truncated: boolean }>
  deleted: string[]
  narration: string
  appTitle?: string
  fileIndex: number
  aborted: boolean
}

export const generate = onRequest(
  {
    region: REGION,
    timeoutSeconds: 540,
    memory: '512MiB',
    maxInstances: 5,
    concurrency: 20,
    secrets: [ANTHROPIC_API_KEY, HL_CLIENT_SECRET],
  },
  async (req, res) => {
    if (applyCors(req, res)) return
    let uid: string | undefined
    try {
      if (req.method !== 'POST') throw new HttpError(405, 'method_not_allowed')
      ;({ uid } = await requireAuth(req))
      const body = parseBody(req, requestSchema)
      await checkRateLimit(uid, [LIMITS.generatePerMin, LIMITS.generatePerDay])

      const projectRef = db.doc(`projects/${body.projectId}`)
      const projectSnap = await projectRef.get()
      const project = projectSnap.data()
      if (!projectSnap.exists || project?.ownerUid !== uid || project?.softDeleted) {
        throw new HttpError(404, 'project_not_found')
      }

      const conn = await getConnection(uid)
      if (!conn || conn.status !== 'connected') {
        if (!isMockMode()) throw new HttpError(403, 'hl_not_connected')
      }

      // Per-project generation lock (stale locks expire after 10 min).
      const generationRef = projectRef.collection('generations').doc()
      await db.runTransaction(async (tx) => {
        const snap = await tx.get(projectRef)
        const p = snap.data()!
        const since = (p.generatingSince as Timestamp | undefined)?.toMillis() ?? 0
        if (p.status === 'generating' && Date.now() - since < 10 * 60_000) {
          throw new HttpError(409, 'generation_in_progress')
        }
        tx.update(projectRef, {
          status: 'generating',
          activeGenerationId: generationRef.id,
          generatingSince: FieldValue.serverTimestamp(),
          updatedAt: FieldValue.serverTimestamp(),
          // Stamp the connected HL location onto the project (spec: each
          // project has a connected HighLevel location ID). Server-written:
          // the client's rules whitelist doesn't include this key.
          ...(conn?.locationId ? { locationId: conn.locationId } : {}),
        })
      })

      // Load current files + recent chat history.
      const filesSnap = await projectRef.collection('files').get()
      const state: GenState = {
        previous: new Map(),
        merged: new Map(),
        docIds: new Map(),
        written: [],
        deleted: [],
        narration: '',
        fileIndex: 0,
        aborted: false,
      }
      for (const doc of filesSnap.docs) {
        const d = doc.data()
        state.previous.set(d.path as string, d.content as string)
        state.merged.set(d.path as string, d.content as string)
        state.docIds.set(d.path as string, doc.id)
      }

      const msgsSnap = await projectRef
        .collection('messages')
        .orderBy('createdAt', 'desc')
        .limit(12)
        .get()
      const history: HistoryTurn[] = msgsSnap.docs
        .map((d) => ({ role: d.data().role as 'user' | 'assistant', content: d.data().content as string }))
        .reverse()
      // The client writes the user turn before calling us — don't double it.
      const last = history[history.length - 1]
      if (last && last.role === 'user' && last.content === body.prompt) history.pop()

      const mode = state.previous.size > 0 ? 'refine' : 'create'
      const modelId = MODEL_IDS[body.model]

      await generationRef.set({
        status: 'running',
        mode,
        model: modelId,
        prompt: body.prompt,
        filesWritten: [],
        startedAt: FieldValue.serverTimestamp(),
      })

      const startedAt = Date.now()
      const sse = new SseWriter(res)
      const abort = new AbortController()
      res.on('close', () => {
        if (!sse.closed) {
          state.aborted = true
          abort.abort()
        }
      })
      sse.send({ type: 'generation_start', generationId: generationRef.id, mode, model: modelId })

      const outbox: OutboxItem[] = []
      const parser = new GenStreamParser({
        onNarrationDelta: (text) => outbox.push({ kind: 'narration', text }),
        onAppStart: (attrs) => outbox.push({ kind: 'app_start', ...attrs }),
        onFileStart: (path) => outbox.push({ kind: 'file_start', path }),
        onFileDelta: (path, content) => outbox.push({ kind: 'file_delta', path, content }),
        onFileComplete: (path, content, opts) =>
          outbox.push({ kind: 'file_complete', path, content, ...opts }),
        onFileDeleted: (path) => outbox.push({ kind: 'file_deleted', path }),
        onAppEnd: () => {},
      })

      const writeFileDoc = async (path: string, content: string): Promise<void> => {
        const existing = state.docIds.get(path)
        if (existing) {
          await projectRef
            .collection('files')
            .doc(existing)
            .update({ content, updatedAt: FieldValue.serverTimestamp() })
        } else {
          const ref = await projectRef
            .collection('files')
            .add({ path, content, updatedAt: FieldValue.serverTimestamp() })
          state.docIds.set(path, ref.id)
        }
        state.merged.set(path, content)
      }

      const drainOutbox = async (): Promise<void> => {
        while (outbox.length > 0) {
          const item = outbox.shift()!
          switch (item.kind) {
            case 'narration':
              state.narration += item.text
              sse.send({ type: 'narration_delta', text: item.text })
              break
            case 'app_start':
              if (item.title) state.appTitle = item.title
              break
            case 'file_start': {
              const pv = validateFilePath(item.path)
              if (!pv.ok) throw new GenParseError('parse_failed', `illegal file path "${item.path}": ${pv.reason}`)
              state.fileIndex += 1
              sse.send({
                type: 'file_start',
                path: item.path,
                index: state.fileIndex,
                action: state.merged.has(item.path) ? 'update' : 'create',
              })
              break
            }
            case 'file_delta':
              sse.send({ type: 'file_delta', path: item.path, content: item.content })
              break
            case 'file_complete': {
              if (state.aborted && item.truncated) break // cancel discards the partial file
              await writeFileDoc(item.path, item.content)
              state.written.push({ path: item.path, content: item.content, truncated: item.truncated })
              sse.send({
                type: 'file_complete',
                path: item.path,
                sizeBytes: Buffer.byteLength(item.content),
                truncated: item.truncated,
                ...(item.changed ? { content: item.content } : {}),
              })
              break
            }
            case 'file_deleted': {
              const docId = state.docIds.get(item.path)
              if (docId) {
                await projectRef.collection('files').doc(docId).delete()
                state.docIds.delete(item.path)
                state.merged.delete(item.path)
                state.deleted.push(item.path)
                sse.send({ type: 'file_deleted', path: item.path })
              }
              break
            }
          }
        }
      }

      // ── Claude streaming with continuation on max_tokens ──────────────────
      const anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY.value(), maxRetries: 2 })
      let messages = buildMessages(
        [...state.previous.entries()].map(([path, content]): ProjectFileInput => ({ path, content })),
        history,
        body.prompt,
      )
      let stopReason: StopReason = 'end_turn'
      const usage: TokenUsage = { inputTokens: 0, outputTokens: 0, cacheReadInputTokens: 0 }
      let errorEvent: Extract<SseEvent, { type: 'error' }> | null = null

      try {
        for (let segment = 0; segment < MAX_RESPONSE_SEGMENTS; segment++) {
          let segmentText = ''
          const stream = anthropic.messages.stream(
            {
              model: modelId,
              max_tokens: MAX_OUTPUT_TOKENS,
              system: [{ type: 'text', text: SYSTEM_PROMPT, cache_control: { type: 'ephemeral' } }],
              messages,
            },
            { signal: abort.signal },
          )
          for await (const event of stream) {
            if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
              segmentText += event.delta.text
              parser.feed(event.delta.text)
              await drainOutbox()
            }
          }
          const finalMsg = await stream.finalMessage()
          usage.inputTokens += finalMsg.usage.input_tokens
          usage.outputTokens += finalMsg.usage.output_tokens
          usage.cacheReadInputTokens += finalMsg.usage.cache_read_input_tokens ?? 0

          if (finalMsg.stop_reason === 'max_tokens' && segment < MAX_RESPONSE_SEGMENTS - 1) {
            messages = [
              ...messages,
              { role: 'assistant', content: segmentText },
              { role: 'user', content: CONTINUE_PROMPT },
            ]
            continue
          }
          if (finalMsg.stop_reason === 'max_tokens') stopReason = 'max_tokens'
          else if (finalMsg.stop_reason === 'refusal') stopReason = 'refused'
          break
        }
        parser.finish()
        await drainOutbox()
      } catch (err) {
        errorEvent = mapStreamError(err, state)
        // Flush whatever is safely parseable; keep completed files durable.
        try {
          parser.finish()
          await drainOutbox()
        } catch {
          /* parser state unusable — completed files are already persisted */
        }
      }

      if (state.aborted) stopReason = 'aborted'
      if (stopReason === 'refused' && !errorEvent) {
        errorEvent = { type: 'error', code: 'refused', message: 'The model declined this request.', recoverable: false }
      }

      // ── Repair pass (one attempt): truncated tail file ────────────────────
      const truncatedFile = state.written.find((f) => f.truncated)
      if (!state.aborted && !errorEvent && truncatedFile) {
        try {
          const repaired = await repairFile(
            anthropic,
            state,
            body.prompt,
            truncatedFile.path,
            truncatedFile.content,
            'the file was cut off mid-stream and is incomplete',
          )
          if (repaired) {
            await writeFileDoc(truncatedFile.path, repaired)
            truncatedFile.content = repaired
            truncatedFile.truncated = false
            sse.send({
              type: 'file_complete',
              path: truncatedFile.path,
              sizeBytes: Buffer.byteLength(repaired),
              truncated: false,
              content: repaired,
            })
          }
        } catch (err) {
          log.warn('repair failed', { path: truncatedFile.path, err: truncate(err, 200) })
        }
      }

      // ── Validation (tripwire; sandbox CSP is the real boundary) ───────────
      if (!errorEvent && state.written.length > 0) {
        const validation = validateGeneration(state.written, state.merged, state.previous)
        if (validation.violations.length > 0) {
          const summary = validation.violations
            .slice(0, 3)
            .map((v) => `${v.path ?? 'project'}: ${v.detail}`)
            .join('; ')
          log.warn('generation policy violations', { uid, count: validation.violations.length, summary })
          errorEvent = {
            type: 'error',
            code: 'policy_violation',
            message: `Generated code violated sandbox policy (${summary}). Files were saved — ask Genesis to fix them, or retry.`,
            recoverable: true,
          }
        }
      }

      // ── Snapshot + persistence ────────────────────────────────────────────
      const filesChanged = state.written.map((f) => f.path)
      let snapshotId: string | undefined
      const { added, removed } = lineDiffCounts(state.previous, state.merged)
      if (filesChanged.length > 0 || state.deleted.length > 0) {
        const kind = state.aborted ? 'stopped' : errorEvent ? 'generation' : 'generation'
        const snapRef = projectRef.collection('snapshots').doc()
        await snapRef.set({
          label: state.appTitle ?? (mode === 'create' ? 'First generation' : 'Refinement'),
          promptExcerpt: truncate(body.prompt, 140),
          fileCount: state.merged.size,
          added,
          removed,
          createdAt: FieldValue.serverTimestamp(),
          generationId: generationRef.id,
          kind: state.aborted ? 'stopped' : kind,
        })
        let batch = db.batch()
        let ops = 0
        for (const [path, content] of state.merged) {
          batch.set(snapRef.collection('files').doc(), { path, content })
          ops++
          if (ops >= 400) {
            await batch.commit()
            batch = db.batch()
            ops = 0
          }
        }
        if (ops > 0) await batch.commit()
        snapshotId = snapRef.id
        sse.send({ type: 'snapshot_created', snapshotId, filesChanged })
      }

      const durationMs = Date.now() - startedAt
      await projectRef.collection('messages').add({
        role: 'assistant',
        content: artifactStub(
          state.narration ||
            (errorEvent ? 'Generation did not complete.' : state.aborted ? 'Generation stopped.' : 'Done.'),
          filesChanged,
          state.deleted,
        ),
        createdAt: FieldValue.serverTimestamp(),
        generationId: generationRef.id,
        meta: {
          filesChanged,
          filesDeleted: state.deleted,
          durationMs,
          added,
          removed,
          ...(snapshotId ? { snapshotId } : {}),
          stopReason,
          ...(errorEvent ? { error: errorEvent.message } : {}),
        },
      })

      await generationRef.update({
        status: errorEvent && !state.aborted ? 'error' : state.aborted ? 'aborted' : 'done',
        filesWritten: filesChanged,
        usage,
        ...(errorEvent ? { error: `${errorEvent.code}: ${errorEvent.message}` } : {}),
        finishedAt: FieldValue.serverTimestamp(),
      })
      await projectRef.update({
        status: errorEvent && !state.aborted ? 'error' : 'ready',
        activeGenerationId: FieldValue.delete(),
        generatingSince: FieldValue.delete(),
        updatedAt: FieldValue.serverTimestamp(),
      })

      if (errorEvent) sse.send(errorEvent)
      else sse.send({ type: 'done', stopReason, usage, filesWritten: filesChanged })
      sse.end()
      log.info('generation finished', {
        uid,
        generationId: generationRef.id,
        mode,
        model: modelId,
        files: filesChanged.length,
        durationMs,
        stopReason,
        cacheRead: usage.cacheReadInputTokens,
        error: errorEvent?.code,
      })
    } catch (err) {
      // Pre-stream failures (auth, limits, lock…) — plain JSON error.
      if (!res.headersSent) {
        sendError(res, err, 'generate', uid)
      } else {
        res.end()
      }
    }
  },
)

function mapStreamError(err: unknown, state: GenState): Extract<SseEvent, { type: 'error' }> | null {
  if (state.aborted || err instanceof Anthropic.APIUserAbortError) return null // clean cancel
  if (err instanceof GenParseError) {
    return {
      type: 'error',
      code: err.code as SseErrorCode,
      message:
        err.code === 'file_too_large'
          ? 'A generated file exceeded the size limit. Completed files were kept.'
          : `The model produced malformed output (${err.message}). Completed files were kept — please retry.`,
      recoverable: true,
    }
  }
  if (err instanceof Anthropic.RateLimitError) {
    return { type: 'error', code: 'rate_limited', message: 'The model is rate-limited right now — retry in a moment.', recoverable: true }
  }
  if (err instanceof Anthropic.APIConnectionError) {
    return { type: 'error', code: 'timeout', message: 'Connection to the model was lost. Completed files were kept — please retry.', recoverable: true }
  }
  if (err instanceof Anthropic.APIError) {
    const overloaded = err.status === 529 || /overloaded/i.test(String(err.message))
    return {
      type: 'error',
      code: overloaded ? 'overloaded' : 'internal',
      message: overloaded
        ? 'The model is overloaded right now — retry in a moment.'
        : 'The model request failed. Completed files were kept — please retry.',
      recoverable: true,
    }
  }
  log.error('unexpected generation error', { err: err instanceof Error ? err.message : String(err) })
  return { type: 'error', code: 'internal', message: 'Generation failed unexpectedly. Completed files were kept.', recoverable: true }
}

/** Single-file non-streamed repair on the cheap model. */
async function repairFile(
  anthropic: Anthropic,
  state: GenState,
  appSummary: string,
  path: string,
  brokenContent: string,
  defect: string,
): Promise<string | null> {
  const others = [...state.merged.entries()]
    .filter(([p]) => p !== path)
    .map(([p, content]): ProjectFileInput => ({ path: p, content }))
  const msg = await anthropic.messages.create({
    model: MODEL_IDS.repair,
    max_tokens: 16_000,
    system: REPAIR_SYSTEM_PROMPT,
    messages: [
      { role: 'user', content: buildRepairMessage(truncate(appSummary, 300), others, path, brokenContent, defect) },
    ],
  })
  const text = msg.content
    .filter((b): b is Anthropic.TextBlock => b.type === 'text')
    .map((b) => b.text)
    .join('')
  let repaired: string | null = null
  const parser = new GenStreamParser({
    onNarrationDelta: () => {},
    onAppStart: () => {},
    onFileStart: () => {},
    onFileDelta: () => {},
    onFileComplete: (p, content, { truncated }) => {
      if (p === path && !truncated) repaired = content
    },
    onFileDeleted: () => {},
    onAppEnd: () => {},
  })
  parser.feed(text)
  parser.finish()
  return repaired
}
