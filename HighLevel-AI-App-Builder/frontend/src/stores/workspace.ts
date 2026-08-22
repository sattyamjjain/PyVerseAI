import { computed, ref, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import {
  collection,
  doc,
  limit,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp,
  updateDoc,
  where,
} from 'firebase/firestore'
import { toast } from 'vue-sonner'
import { auth, db } from '@/lib/firebase'
import { announce, announceAlert } from '@/composables/useAnnouncer'
import type {
  FileDoc,
  GenerationDoc,
  HlEventDoc,
  MessageDoc,
  ProjectDoc,
  SnapshotDoc,
} from '@shared/models'
import { getOrCreateModel, setModelValue, disposeAllModels, getModel } from '@/lib/models'

export type FileRow = FileDoc & { docId: string }
export type MessageRow = MessageDoc & { id: string }
export type GenerationRow = GenerationDoc & { id: string }
export type SnapshotRow = SnapshotDoc & { id: string }
export type HlEventRow = HlEventDoc & { id: string }

export const useWorkspaceStore = defineStore('workspace', () => {
  const projectId = ref<string | null>(null)
  const project = shallowRef<(ProjectDoc & { id: string }) | null>(null)
  const projectMissing = ref(false)
  const projectLoading = ref(true)

  const files = ref<Map<string, FileRow>>(new Map())
  const messages = ref<MessageRow[]>([])
  const generations = ref<GenerationRow[]>([])
  const snapshots = ref<SnapshotRow[]>([])
  const hlEvents = ref<HlEventRow[]>([])
  /** Set once the hl_events listener has delivered its initial snapshot —
   *  used so only NEW webhook events trigger toasts/broadcasts. */
  const hlEventsPrimed = ref(false)

  const openTabs = ref<string[]>([])
  const activePath = ref<string | null>(null)
  const dirtyPaths = ref<Set<string>>(new Set())
  const savingPaths = ref<Set<string>>(new Set())
  const lastSavedAt = ref<number>(0)

  let unsubs: Array<() => void> = []

  const fileContents = computed<Map<string, string>>(() => {
    const m = new Map<string, string>()
    for (const [path, row] of files.value) m.set(path, row.content)
    return m
  })

  const filePaths = computed(() => [...files.value.keys()].sort())
  const latestGeneration = computed(() => generations.value[0] ?? null)

  function open(id: string) {
    close()
    projectId.value = id
    projectMissing.value = false
    projectLoading.value = true

    const projectRef = doc(db, 'projects', id)
    unsubs.push(
      onSnapshot(
        projectRef,
        (snap) => {
          projectLoading.value = false
          if (!snap.exists()) {
            projectMissing.value = true
            project.value = null
            return
          }
          const data = snap.data() as ProjectDoc
          if (data.ownerUid !== auth.currentUser?.uid) {
            projectMissing.value = true
            project.value = null
            return
          }
          project.value = { id: snap.id, ...data }
        },
        () => {
          // Permission denied (foreign project) presents as missing.
          projectLoading.value = false
          projectMissing.value = true
        },
      ),
    )

    unsubs.push(
      onSnapshot(collection(db, 'projects', id, 'files'), (snap) => {
        const next = new Map<string, FileRow>()
        for (const d of snap.docs) {
          const data = d.data() as FileDoc
          next.set(data.path, { ...data, docId: d.id })
        }
        files.value = next
        syncModelsFromFirestore()
        pruneTabs()
      }),
    )

    unsubs.push(
      onSnapshot(query(collection(db, 'projects', id, 'messages'), orderBy('createdAt', 'asc')), (snap) => {
        messages.value = snap.docs.map((d) => ({ id: d.id, ...(d.data() as MessageDoc) }))
      }),
    )

    unsubs.push(
      onSnapshot(
        query(collection(db, 'projects', id, 'generations'), orderBy('startedAt', 'desc'), limit(5)),
        (snap) => {
          generations.value = snap.docs.map((d) => ({ id: d.id, ...(d.data() as GenerationDoc) }))
        },
      ),
    )

    unsubs.push(
      onSnapshot(
        query(collection(db, 'projects', id, 'snapshots'), orderBy('createdAt', 'desc')),
        (snap) => {
          snapshots.value = snap.docs.map((d) => ({ id: d.id, ...(d.data() as SnapshotDoc) }))
        },
      ),
    )

    const uid = auth.currentUser?.uid
    if (uid) {
      hlEventsPrimed.value = false
      unsubs.push(
        onSnapshot(
          query(
            collection(db, 'hl_events'),
            where('ownerUid', '==', uid),
            orderBy('createdAt', 'desc'),
            limit(20),
          ),
          (snap) => {
            hlEvents.value = snap.docs.map((d) => ({ id: d.id, ...(d.data() as HlEventDoc) }))
            // First delivery is history, not news.
            queueMicrotask(() => (hlEventsPrimed.value = true))
          },
        ),
      )
    }
  }

  function close() {
    unsubs.forEach((u) => u())
    unsubs = []
    projectId.value = null
    project.value = null
    projectMissing.value = false
    projectLoading.value = true
    files.value = new Map()
    messages.value = []
    generations.value = []
    snapshots.value = []
    hlEvents.value = []
    openTabs.value = []
    activePath.value = null
    dirtyPaths.value = new Set()
    savingPaths.value = new Set()
    disposeAllModels()
  }

  /** Firestore is the source of truth for non-dirty, non-streaming files. */
  let streamingGuard: (path: string) => boolean = () => false
  function setStreamingGuard(fn: (path: string) => boolean) {
    streamingGuard = fn
  }

  function syncModelsFromFirestore() {
    for (const [path, row] of files.value) {
      if (dirtyPaths.value.has(path) || streamingGuard(path)) continue
      const model = getModel(path)
      if (!model) continue
      if (model.getValue() !== row.content) setModelValue(path, row.content)
    }
  }

  /**
   * Paths currently being streamed by a generation. They exist as Monaco
   * models and open tabs BEFORE their Firestore write lands at file_complete,
   * so tab pruning must not evict them mid-stream.
   */
  const streamingPaths = ref<ReadonlySet<string>>(new Set())
  function markStreaming(path: string) {
    streamingPaths.value = new Set(streamingPaths.value).add(path)
  }
  function clearStreaming() {
    if (streamingPaths.value.size > 0) streamingPaths.value = new Set()
  }

  function pruneTabs() {
    const keep = (p: string) => files.value.has(p) || streamingPaths.value.has(p)
    openTabs.value = openTabs.value.filter(keep)
    if (activePath.value && !keep(activePath.value)) {
      activePath.value = openTabs.value[0] ?? null
    }
  }

  function openFile(path: string) {
    const row = files.value.get(path)
    getOrCreateModel(path, row?.content ?? '')
    if (!openTabs.value.includes(path)) openTabs.value = [...openTabs.value, path]
    activePath.value = path
  }

  function closeTab(path: string) {
    const idx = openTabs.value.indexOf(path)
    openTabs.value = openTabs.value.filter((p) => p !== path)
    if (activePath.value === path) {
      activePath.value = openTabs.value[Math.min(idx, openTabs.value.length - 1)] ?? null
    }
    dirtyPaths.value.delete(path)
    dirtyPaths.value = new Set(dirtyPaths.value)
  }

  function markDirty(path: string) {
    if (!dirtyPaths.value.has(path)) {
      dirtyPaths.value = new Set(dirtyPaths.value).add(path)
    }
  }

  async function saveFile(path: string, opts?: { announceResult?: boolean }): Promise<void> {
    const pid = projectId.value
    const row = files.value.get(path)
    const model = getModel(path)
    if (!pid || !row || !model) return
    const content = model.getValue()
    if (content === row.content) {
      dirtyPaths.value.delete(path)
      dirtyPaths.value = new Set(dirtyPaths.value)
      if (opts?.announceResult) announce('Saved')
      return
    }
    savingPaths.value = new Set(savingPaths.value).add(path)
    try {
      await updateDoc(doc(db, 'projects', pid, 'files', row.docId), {
        content,
        updatedAt: serverTimestamp(),
      })
      dirtyPaths.value.delete(path)
      dirtyPaths.value = new Set(dirtyPaths.value)
      lastSavedAt.value = Date.now()
      if (opts?.announceResult) announce('Saved')
    } catch (err) {
      // A silent failed save loses work invisibly (WCAG 4.1.3).
      toast.error(`Could not save ${path}`, {
        description: err instanceof Error ? err.message : undefined,
      })
      announceAlert(`Could not save ${path}`)
    } finally {
      savingPaths.value.delete(path)
      savingPaths.value = new Set(savingPaths.value)
    }
  }

  async function renameProject(name: string) {
    if (!projectId.value) return
    await updateDoc(doc(db, 'projects', projectId.value), {
      name: name.trim(),
      updatedAt: serverTimestamp(),
    })
  }

  async function restoreFromTrash() {
    if (!projectId.value) return
    await updateDoc(doc(db, 'projects', projectId.value), {
      softDeleted: false,
      updatedAt: serverTimestamp(),
    })
  }

  return {
    projectId,
    project,
    projectMissing,
    projectLoading,
    files,
    fileContents,
    filePaths,
    messages,
    generations,
    latestGeneration,
    snapshots,
    hlEvents,
    hlEventsPrimed,
    openTabs,
    activePath,
    dirtyPaths,
    savingPaths,
    lastSavedAt,
    open,
    close,
    openFile,
    closeTab,
    markStreaming,
    clearStreaming,
    markDirty,
    saveFile,
    renameProject,
    restoreFromTrash,
    setStreamingGuard,
  }
})
