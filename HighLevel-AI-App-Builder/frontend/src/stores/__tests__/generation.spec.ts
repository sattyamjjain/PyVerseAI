import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { StreamCallbacks, StreamHandle } from '@/lib/sse'
import type { GenerateRequest, SseEvent } from '@shared/protocol'

/**
 * The store is tested as a pure state machine: the SSE stream, Firestore,
 * Monaco models, and the workspace store are boundaries, mocked at the module
 * seam. Tests drive the captured stream callbacks by hand. The Monaco mock is
 * a real string map so delta accumulation and reverts are observable.
 */
const h = vi.hoisted(() => {
  const contents = new Map<string, string>()
  return {
    contents,
    workspace: {
      projectId: 'p1' as string | null,
      fileContents: new Map<string, string>(),
      setStreamingGuard: vi.fn<(guard: (path: string) => boolean) => void>(),
      markStreaming: vi.fn<(path: string) => void>(),
      clearStreaming: vi.fn<() => void>(),
      openFile: vi.fn<(path: string) => void>(),
      closeTab: vi.fn<(path: string) => void>(),
    },
    streamGeneration: vi.fn<(body: GenerateRequest, cb: StreamCallbacks) => StreamHandle>(),
    addDoc: vi.fn<() => Promise<{ id: string }>>(async () => ({ id: 'msg-1' })),
    announce: vi.fn<(text: string) => void>(),
    announceAlert: vi.fn<(text: string) => void>(),
    pushUndoStop: vi.fn<(path: string) => void>(),
    disposeModel: vi.fn<(path: string) => void>((path) => void contents.delete(path)),
  }
})

vi.mock('@/lib/firebase', () => ({ db: {} }))
vi.mock('firebase/firestore', () => ({
  addDoc: h.addDoc,
  collection: vi.fn<() => object>(() => ({})),
  serverTimestamp: vi.fn<() => object>(() => ({})),
}))
vi.mock('@/stores/workspace', () => ({ useWorkspaceStore: () => h.workspace }))
vi.mock('@/composables/useAnnouncer', () => ({
  announce: h.announce,
  announceAlert: h.announceAlert,
}))
vi.mock('@/lib/sse', () => ({ streamGeneration: h.streamGeneration }))
vi.mock('@/lib/models', () => ({
  getModel: (path: string) =>
    h.contents.has(path) ? { getValue: () => h.contents.get(path) ?? '' } : null,
  getOrCreateModel: (path: string, content = '') => {
    if (!h.contents.has(path)) h.contents.set(path, content)
    return { getValue: () => h.contents.get(path) ?? '' }
  },
  setModelValue: (path: string, content: string) => void h.contents.set(path, content),
  appendToModel: (path: string, text: string) =>
    void h.contents.set(path, (h.contents.get(path) ?? '') + text),
  pushUndoStop: h.pushUndoStop,
  disposeModel: h.disposeModel,
}))

import { useGenerationStore } from '@/stores/generation'

interface Captured {
  body: GenerateRequest
  cb: StreamCallbacks
  handle: StreamHandle & { cancel: Mock<() => void> }
}

let captured: Captured | null = null

async function startGeneration(prompt = 'build a todo app') {
  const store = useGenerationStore()
  await store.send(prompt)
  if (!captured) throw new Error('streamGeneration was not called')
  return { store, ...captured }
}

const fileStart = (path: string, action: 'create' | 'update' = 'create'): SseEvent => ({
  type: 'file_start',
  path,
  index: 0,
  action,
})
const fileComplete = (path: string, truncated = false, content?: string): SseEvent => ({
  type: 'file_complete',
  path,
  sizeBytes: 0,
  truncated,
  ...(content !== undefined ? { content } : {}),
})
const doneEvent = (stopReason: 'end_turn' | 'aborted' = 'end_turn'): SseEvent => ({
  type: 'done',
  stopReason,
  filesWritten: [],
})

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
  captured = null
  h.contents.clear()
  h.workspace.fileContents.clear()
  h.workspace.projectId = 'p1'
  h.streamGeneration.mockImplementation((body: GenerateRequest, cb: StreamCallbacks) => {
    const handle = { cancel: vi.fn<() => void>(), finished: Promise.resolve() }
    captured = { body, cb, handle }
    return handle
  })
})

describe('generation store', () => {
  it('starts idle and persists the model preference across store instances', () => {
    const store = useGenerationStore()
    expect(store.phase).toBe('idle')
    expect(store.isActive).toBe(false)
    expect(store.pillText).toBe('')
    expect(store.model).toBe('fast')

    store.setModel('best')
    expect(localStorage.getItem('genesis:model')).toBe('best')

    setActivePinia(createPinia()) // fresh app boot re-reads the persisted choice
    expect(useGenerationStore().model).toBe('best')
  })

  it('send() enters sending, records the chat bubble, and issues the stream request', async () => {
    const { store, body } = await startGeneration('make it purple')
    expect(store.phase).toBe('sending')
    expect(store.isActive).toBe(true)
    expect(body).toEqual({ projectId: 'p1', prompt: 'make it purple', model: 'fast' })
    expect(h.addDoc).toHaveBeenCalledTimes(1)

    // A second send while active must not open a competing stream.
    await store.send('another prompt')
    expect(h.streamGeneration).toHaveBeenCalledTimes(1)
    expect(store.lastPrompt).toBe('make it purple')

    // No project selected → no request at all.
    h.workspace.projectId = null
    setActivePinia(createPinia())
    const orphan = useGenerationStore()
    await orphan.send('hello')
    expect(h.streamGeneration).toHaveBeenCalledTimes(1)
    expect(orphan.phase).toBe('idle')
  })

  it('moves to planning on generation_start and accumulates narration deltas', async () => {
    const { store, cb } = await startGeneration()
    cb.onEvent({ type: 'generation_start', generationId: 'g1', mode: 'create', model: 'm1' })
    expect(store.phase).toBe('planning')
    expect(store.activeGenerationId).toBe('g1')

    cb.onEvent({ type: 'narration_delta', text: 'Adding ' })
    cb.onEvent({ type: 'narration_delta', text: 'a form.' })
    expect(store.narration).toBe('Adding a form.')
  })

  it('file_start enters streaming with a reset model and a live-file entry', async () => {
    h.contents.set('app.js', 'stale editor content')
    const { store, cb } = await startGeneration()
    cb.onEvent(fileStart('app.js'))

    expect(store.phase).toBe('streaming')
    expect(store.streamingPath).toBe('app.js')
    expect(store.pillText).toBe('Writing app.js (1)')
    expect(store.liveFiles).toEqual([
      { path: 'app.js', status: 'writing', action: 'create', added: 0, removed: 0, truncated: false },
    ])
    expect(h.contents.get('app.js')).toBe('') // streamed files start from empty
    expect(h.workspace.markStreaming).toHaveBeenCalledWith('app.js')
    expect(h.workspace.openFile).toHaveBeenCalledWith('app.js')
  })

  it('accumulates deltas and diffs the completed file against its pre-generation content', async () => {
    h.workspace.fileContents.set('app.js', 'old line 1\nold line 2')
    const { store, cb } = await startGeneration()

    cb.onEvent(fileStart('app.js', 'update'))
    cb.onEvent({ type: 'file_delta', path: 'app.js', content: 'new line 1\n' })
    cb.onEvent({ type: 'file_delta', path: 'app.js', content: 'new line 2\nnew line 3' })
    expect(h.contents.get('app.js')).toBe('new line 1\nnew line 2\nnew line 3')
    expect(store.followTick).toBe(2)

    cb.onEvent(fileComplete('app.js'))
    expect(store.liveFiles).toEqual([
      { path: 'app.js', status: 'done', action: 'update', added: 3, removed: 2, truncated: false },
    ])
    expect(store.streamingPath).toBeNull()
  })

  it('file_complete with authoritative content overrides the streamed bytes', async () => {
    const { store, cb } = await startGeneration()
    cb.onEvent(fileStart('app.js'))
    cb.onEvent({ type: 'file_delta', path: 'app.js', content: 'partial garbage' })

    cb.onEvent(fileComplete('app.js', true, 'final line 1\nfinal line 2'))
    expect(h.contents.get('app.js')).toBe('final line 1\nfinal line 2')
    expect(store.liveFiles[0]).toMatchObject({ status: 'done', added: 2, removed: 0, truncated: true })
  })

  it('runs the full happy path: snapshot → finalizing, done → undo stops and cleared streaming', async () => {
    const { store, cb } = await startGeneration()
    cb.onEvent(fileStart('app.js'))
    cb.onEvent({ type: 'file_delta', path: 'app.js', content: 'x' })
    cb.onEvent(fileComplete('app.js'))

    cb.onEvent({ type: 'file_deleted', path: 'legacy.js' })
    expect(store.deletedPaths).toEqual(['legacy.js'])
    expect(h.workspace.closeTab).toHaveBeenCalledWith('legacy.js')
    expect(h.disposeModel).toHaveBeenCalledWith('legacy.js')

    cb.onEvent({ type: 'snapshot_created', snapshotId: 's1', filesChanged: ['app.js'] })
    expect(store.phase).toBe('finalizing')
    expect(store.lastSnapshotId).toBe('s1')

    cb.onEvent({
      type: 'done',
      stopReason: 'end_turn',
      usage: { inputTokens: 10, outputTokens: 20, cacheReadInputTokens: 5 },
      filesWritten: ['app.js'],
    })
    expect(store.phase).toBe('done')
    expect(store.isActive).toBe(false)
    expect(store.stopReason).toBe('end_turn')
    expect(store.usage).toEqual({ inputTokens: 10, outputTokens: 20, cacheReadInputTokens: 5 })
    expect(store.pillText).toMatch(/^Done in \d+s$/)
    expect(h.pushUndoStop).toHaveBeenCalledWith('app.js') // one undo stop per touched file
    expect(h.workspace.clearStreaming).toHaveBeenCalledTimes(1)
    expect(h.announce).toHaveBeenCalledWith(expect.stringContaining('Generation complete'))

    store.settle() // transient done state clears (pill fade)
    expect(store.phase).toBe('idle')
  })

  it('done with stopReason aborted lands in stopped, not done', async () => {
    const { store, cb } = await startGeneration()
    cb.onEvent(fileStart('app.js'))
    cb.onEvent(fileComplete('app.js'))
    cb.onEvent(doneEvent('aborted'))
    expect(store.phase).toBe('stopped')
    expect(h.announce).toHaveBeenCalledWith('Generation stopped')
  })

  it('an error event fails the run, keeps code/recoverable, and is not settled away', async () => {
    const { store, cb } = await startGeneration()
    cb.onEvent(fileStart('app.js'))
    cb.onEvent({ type: 'error', code: 'rate_limited', message: 'Slow down', recoverable: true })

    expect(store.phase).toBe('failed')
    expect(store.error).toEqual({ code: 'rate_limited', message: 'Slow down', recoverable: true })
    expect(h.workspace.clearStreaming).toHaveBeenCalledTimes(1)
    expect(h.announceAlert).toHaveBeenCalledWith('Generation failed: Slow down')

    store.settle() // settle clears only done/stopped — a failure must stay visible
    expect(store.phase).toBe('failed')
  })

  it('a transport error reverts only the in-flight partial file', async () => {
    // Fresh file mid-stream: the partial tab and model are discarded entirely,
    // while the already-completed file survives.
    {
      const { store, cb } = await startGeneration()
      cb.onEvent(fileStart('done.js'))
      cb.onEvent(fileComplete('done.js'))
      cb.onEvent(fileStart('partial.js'))
      cb.onEvent({ type: 'file_delta', path: 'partial.js', content: 'half a fi' })

      cb.onTransportError(new Error('boom'))
      expect(store.phase).toBe('failed')
      expect(store.error).toMatchObject({ code: 'network', recoverable: true })
      expect(h.workspace.closeTab).toHaveBeenCalledWith('partial.js')
      expect(h.disposeModel).toHaveBeenCalledWith('partial.js')
      expect(store.liveFiles.map((f) => f.path)).toEqual(['done.js'])
      expect(store.streamingPath).toBeNull()
    }

    // Pre-existing file mid-update: content is restored, the tab stays open.
    setActivePinia(createPinia())
    vi.clearAllMocks()
    h.workspace.fileContents.set('app.js', 'original content')
    {
      const { store, cb } = await startGeneration()
      cb.onEvent(fileStart('app.js', 'update'))
      cb.onEvent({ type: 'file_delta', path: 'app.js', content: 'junk' })

      cb.onTransportError(new Error('boom'))
      expect(store.phase).toBe('failed')
      expect(h.contents.get('app.js')).toBe('original content')
      expect(h.workspace.closeTab).not.toHaveBeenCalled()
      expect(h.disposeModel).not.toHaveBeenCalled()
    }
  })

  it('ignores transport errors that arrive after a terminal state', async () => {
    const { store, cb } = await startGeneration()
    cb.onEvent(doneEvent())
    expect(store.phase).toBe('done')

    cb.onTransportError(new Error('late network hiccup'))
    expect(store.phase).toBe('done')
    expect(store.error).toBeNull()
  })

  it('cancel() enters stopping, mutes transport errors, and settles to stopped on close', async () => {
    const idle = useGenerationStore()
    idle.cancel() // nothing active — must be a no-op
    expect(idle.phase).toBe('idle')

    const { store, cb, handle } = await startGeneration()
    cb.onEvent(fileStart('app.js'))
    cb.onEvent({ type: 'file_delta', path: 'app.js', content: 'half' })

    store.cancel()
    expect(store.phase).toBe('stopping')
    expect(handle.cancel).toHaveBeenCalledTimes(1)

    cb.onTransportError(new Error('aborted')) // abort fallout, not a real failure
    expect(store.error).toBeNull()
    expect(store.phase).toBe('stopping')

    cb.onClose(false)
    expect(store.phase).toBe('stopped')
    expect(store.liveFiles).toEqual([]) // the partial file was reverted
    expect(h.announce).toHaveBeenCalledWith('Generation stopped')
  })

  it('retry() re-issues the last prompt after a failure', async () => {
    const { store, cb } = await startGeneration('first prompt')
    cb.onEvent({ type: 'error', code: 'overloaded', message: 'busy', recoverable: true })
    expect(store.phase).toBe('failed')

    store.retry()
    await vi.waitFor(() => expect(h.streamGeneration).toHaveBeenCalledTimes(2))
    expect(captured!.body.prompt).toBe('first prompt')
    expect(store.error).toBeNull()
    expect(store.isActive).toBe(true)
  })
})
