import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ConfirmInfo } from '@/lib/bridge'

interface PendingConfirm {
  info: ConfirmInfo
  resolve: (allowed: boolean) => void
}

export const useUiStore = defineStore('ui', () => {
  // Dialog/sheet visibility
  const paletteOpen = ref(false)
  const shortcutsOpen = ref(false)
  const hlDialogOpen = ref(false)
  const snapshotSheetOpen = ref(false)
  const diffDialog = ref<{
    open: boolean
    /** Base (older) snapshot id, or null for an empty project baseline. */
    base: string | null
    /** Target: a snapshot id, or 'current' for the live files. */
    target: string | 'current'
    title: string
  }>({ open: false, base: null, target: 'current', title: '' })

  // Workspace layout
  const chatCollapsed = ref(false)
  const previewCollapsed = ref(false)
  const mobileTab = ref<'chat' | 'code' | 'preview'>('chat')
  const followMode = ref(true)

  // Composer
  const composerPrefill = ref<string | null>(null)

  // Blocking overlay while a snapshot restore is applying.
  const restoring = ref(false)

  // Accessibility: screen-reader optimized Monaco (persisted).
  const srOptimized = ref(localStorage.getItem('genesis:sr-optimized') === 'true')
  function setSrOptimized(v: boolean) {
    srOptimized.value = v
    localStorage.setItem('genesis:sr-optimized', String(v))
  }

  // Bridge write-confirmation queue (one dialog at a time, FIFO).
  const confirmQueue = ref<PendingConfirm[]>([])
  function requestConfirm(info: ConfirmInfo): Promise<boolean> {
    return new Promise((resolve) => {
      confirmQueue.value = [...confirmQueue.value, { info, resolve }]
    })
  }
  function settleConfirm(allowed: boolean) {
    const [head, ...rest] = confirmQueue.value
    if (head) head.resolve(allowed)
    confirmQueue.value = rest
  }

  function openDiff(base: string | null, target: string | 'current', title: string) {
    diffDialog.value = { open: true, base, target, title }
  }
  function closeDiff() {
    diffDialog.value = { open: false, base: null, target: 'current', title: '' }
  }

  return {
    paletteOpen,
    shortcutsOpen,
    hlDialogOpen,
    snapshotSheetOpen,
    diffDialog,
    chatCollapsed,
    previewCollapsed,
    mobileTab,
    followMode,
    composerPrefill,
    restoring,
    srOptimized,
    setSrOptimized,
    confirmQueue,
    requestConfirm,
    settleConfirm,
    openDiff,
    closeDiff,
  }
})
