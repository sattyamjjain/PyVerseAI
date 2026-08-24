import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { addDoc, collection, serverTimestamp } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { streamGeneration, type StreamHandle } from '@/lib/sse'
import { announce, announceAlert } from '@/composables/useAnnouncer'
import { appendToModel, disposeModel, getModel, getOrCreateModel, pushUndoStop, setModelValue } from '@/lib/models'
import { lineDiffCounts } from '@/lib/diff'
import { useWorkspaceStore } from '@/stores/workspace'
import type { SseErrorCode, StopReason, TokenUsage } from '@shared/protocol'

export type GenerationPhase =
  | 'idle'
  | 'sending'
  | 'planning'
  | 'streaming'
  | 'finalizing'
  | 'stopping'
  | 'done'
  | 'failed'
  | 'stopped'

export interface LiveFile {
  path: string
  status: 'writing' | 'done'
  action: 'create' | 'update'
  added: number
  removed: number
  truncated: boolean
}

export interface GenError {
  code: SseErrorCode | 'network'
  message: string
  recoverable: boolean
}

const ACTIVE_PHASES: GenerationPhase[] = ['sending', 'planning', 'streaming', 'finalizing', 'stopping']

export const useGenerationStore = defineStore('generation', () => {
  const workspace = useWorkspaceStore()

  const phase = ref<GenerationPhase>('idle')
  const narration = ref('')
  const liveFiles = ref<LiveFile[]>([])
  const streamingPath = ref<string | null>(null)
  const deletedPaths = ref<string[]>([])
  const error = ref<GenError | null>(null)
  const activeGenerationId = ref<string | null>(null)
  const lastPrompt = ref('')
  const lastSnapshotId = ref<string | null>(null)
  const usage = ref<TokenUsage | null>(null)
  const stopReason = ref<StopReason | null>(null)
  const startedAt = ref(0)
  const durationMs = ref(0)
  const model = ref<'fast' | 'best'>(
    (localStorage.getItem('genesis:model') as 'fast' | 'best') || 'fast',
  )

  const beforeContents = new Map<string, string | null>()
  let handle: StreamHandle | null = null

  const isActive = computed(() => ACTIVE_PHASES.includes(phase.value))
  const followTick = ref(0) // bumped per delta so the editor can reveal

  // While a generation is live, its touched files are owned by the stream, not
  // by Firestore echoes (registered as the workspace store's streaming guard).
  workspace.setStreamingGuard(
    (path) => isActive.value && liveFiles.value.some((f) => f.path === path),
  )

  function setModel(m: 'fast' | 'best') {
    model.value = m
    localStorage.setItem('genesis:model', m)
  }

  const pillText = computed(() => {
    switch (phase.value) {
      case 'sending':
        return 'Starting…'
      case 'planning':
        return 'Planning…'
      case 'streaming': {
        const n = liveFiles.value.length
        const path = streamingPath.value
        return path ? `Writing ${path} (${n})` : 'Generating…'
      }
      case 'finalizing':
        return 'Finishing up…'
      case 'stopping':
        return 'Stopping…'
      case 'done':
        return `Done in ${Math.max(1, Math.round(durationMs.value / 1000))}s`
      case 'failed':
        return 'Failed'
      case 'stopped':
        return 'Stopped'
      default:
        return ''
    }
  })

  async function send(prompt: string): Promise<void> {
    const projectId = workspace.projectId
    if (!projectId || isActive.value) return
    lastPrompt.value = prompt
    phase.value = 'sending'
    narration.value = ''
    liveFiles.value = []
    deletedPaths.value = []
    error.value = null
    usage.value = null
    stopReason.value = null
    lastSnapshotId.value = null
    streamingPath.value = null
    beforeContents.clear()
    startedAt.value = Date.now()

    try {
      await addDoc(collection(db, 'projects', projectId, 'messages'), {
        role: 'user',
        content: prompt,
        createdAt: serverTimestamp(),
      })
    } catch {
      // Non-fatal: the server also has the prompt; chat will lack the bubble.
    }

    handle = streamGeneration(
      { projectId, prompt, model: model.value },
      {
        onEvent(event) {
          switch (event.type) {
            case 'generation_start':
              activeGenerationId.value = event.generationId
              phase.value = 'planning'
              announce('Generating: planning')
              break
            case 'narration_delta':
              narration.value += event.text
              break
            case 'file_start': {
              phase.value = 'streaming'
              streamingPath.value = event.path
              const before = workspace.fileContents.get(event.path) ?? null
              beforeContents.set(event.path, before)
              getOrCreateModel(event.path, '')
              setModelValue(event.path, '')
              workspace.markStreaming(event.path)
              liveFiles.value = [
                ...liveFiles.value,
                { path: event.path, status: 'writing', action: event.action, added: 0, removed: 0, truncated: false },
              ]
              workspace.openFile(event.path)
              announce(`Writing ${event.path}, file ${liveFiles.value.length}`)
              break
            }
            case 'file_delta':
              appendToModel(event.path, event.content)
              followTick.value++
              break
            case 'file_complete': {
              const finalContent = event.content ?? getModel(event.path)?.getValue() ?? ''
              if (event.content !== undefined) setModelValue(event.path, event.content)
              const before = beforeContents.get(event.path) ?? null
              const counts = lineDiffCounts(before ?? '', finalContent)
              liveFiles.value = liveFiles.value.map((f) =>
                f.path === event.path
                  ? { ...f, status: 'done', added: counts.added, removed: counts.removed, truncated: event.truncated }
                  : f,
              )
              if (streamingPath.value === event.path) streamingPath.value = null
              break
            }
            case 'file_deleted':
              deletedPaths.value = [...deletedPaths.value, event.path]
              workspace.closeTab(event.path)
              disposeModel(event.path)
              break
            case 'snapshot_created':
              phase.value = 'finalizing'
              lastSnapshotId.value = event.snapshotId
              break
            case 'done': {
              durationMs.value = Date.now() - startedAt.value
              usage.value = event.usage ?? null
              stopReason.value = event.stopReason
              finishTouchedFiles()
              if (event.stopReason === 'aborted') {
                phase.value = 'stopped'
                announce('Generation stopped')
              } else {
                phase.value = 'done'
                announce(
                  `Generation complete: ${liveFiles.value.length} files in ${Math.max(1, Math.round(durationMs.value / 1000))} seconds`,
                )
              }
              break
            }
            case 'error':
              durationMs.value = Date.now() - startedAt.value
              error.value = { code: event.code, message: event.message, recoverable: event.recoverable }
              phase.value = 'failed'
              finishTouchedFiles()
              announceAlert(`Generation failed: ${event.message}`)
              break
          }
        },
        onTransportError(err) {
          if (phase.value === 'stopping') return
          if (['done', 'failed', 'stopped', 'idle'].includes(phase.value)) return
          durationMs.value = Date.now() - startedAt.value
          revertPartialFile()
          error.value = {
            code: 'network',
            message: err.message || 'Connection lost. The generation may still be running.',
            recoverable: true,
          }
          phase.value = 'failed'
          announceAlert('Connection lost during generation.')
        },
        onClose() {
          if (phase.value === 'stopping') {
            durationMs.value = Date.now() - startedAt.value
            revertPartialFile()
            finishTouchedFiles()
            phase.value = 'stopped'
            announce('Generation stopped')
          }
          handle = null
        },
      },
    )
  }

  /** Revert the in-flight partial file (kept files stay). */
  function revertPartialFile() {
    const path = streamingPath.value
    if (!path) return
    const before = beforeContents.get(path) ?? null
    if (before === null) {
      workspace.closeTab(path)
      disposeModel(path)
    } else {
      setModelValue(path, before)
    }
    liveFiles.value = liveFiles.value.filter((f) => !(f.path === path && f.status === 'writing'))
    streamingPath.value = null
  }

  /** One undo stop per generation for every touched file. */
  function finishTouchedFiles() {
    for (const f of liveFiles.value) pushUndoStop(f.path)
    // Streamed files are durable in Firestore by now — normal pruning resumes.
    workspace.clearStreaming()
  }

  function cancel() {
    if (!handle || !isActive.value) return
    phase.value = 'stopping'
    handle.cancel()
  }

  function retry() {
    const prompt = lastPrompt.value
    if (!prompt) return
    reset()
    void send(prompt)
  }

  function reset() {
    phase.value = 'idle'
    error.value = null
    narration.value = ''
    liveFiles.value = []
    streamingPath.value = null
  }

  /** Clear transient done/stopped state (pill fade). */
  function settle() {
    if (phase.value === 'done' || phase.value === 'stopped') reset()
  }

  return {
    phase,
    isActive,
    narration,
    liveFiles,
    streamingPath,
    deletedPaths,
    error,
    activeGenerationId,
    lastPrompt,
    lastSnapshotId,
    usage,
    stopReason,
    durationMs,
    model,
    pillText,
    followTick,
    setModel,
    send,
    cancel,
    retry,
    reset,
    settle,
  }
})
