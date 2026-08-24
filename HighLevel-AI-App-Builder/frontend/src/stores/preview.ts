import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { PreviewMessage } from '@shared/protocol'
import { assembleSrcdoc } from '@/lib/srcdoc'
import { announce, announceAlert } from '@/composables/useAnnouncer'

export interface ConsoleEntry {
  level: 'log' | 'info' | 'warn' | 'error'
  text: string
  at: number
}

const MAX_CONSOLE_ENTRIES = 500
// Tailwind Play CDN (if ever used by generated code) logs an unsuppressible
// dev warning — keep it out of the visible console.
const NOISE_PATTERNS = [/cdn\.tailwindcss\.com|@tailwindcss\/browser/i]

export const usePreviewStore = defineStore('preview', () => {
  const srcdoc = ref('')
  const srcdocKey = ref(0)
  const updating = ref(false)
  const ready = ref(false)
  const hasBuilt = ref(false)
  const warnings = ref<string[]>([])
  const consoleEntries = ref<ConsoleEntry[]>([])
  const consoleOpen = ref(false)
  const runtimeError = ref<{ message: string; source?: string; line?: number } | null>(null)
  const errorDismissed = ref(false)
  const deviceMode = ref<'desktop' | 'mobile'>('desktop')
  /** One assertive announcement per build for runtime errors. */
  let errorAnnounced = false

  const errorCount = computed(
    () => consoleEntries.value.filter((e) => e.level === 'error').length,
  )
  const warnCount = computed(() => consoleEntries.value.filter((e) => e.level === 'warn').length)

  let overlayTimer: ReturnType<typeof setTimeout> | null = null
  let loadGraceTimer: ReturnType<typeof setTimeout> | null = null

  function rebuild(files: ReadonlyMap<string, string>, parentOrigin: string) {
    if (loadGraceTimer) clearTimeout(loadGraceTimer)
    const result = assembleSrcdoc(files, parentOrigin)
    warnings.value = result.warnings
    consoleEntries.value = []
    runtimeError.value = null
    errorDismissed.value = false
    errorAnnounced = false
    ready.value = false
    hasBuilt.value = files.has('index.html')
    srcdoc.value = result.srcdoc
    srcdocKey.value++
    updating.value = true
    if (overlayTimer) clearTimeout(overlayTimer)
    // Minimum overlay display so the refresh doesn't flash.
    overlayTimer = setTimeout(() => {
      if (ready.value) updating.value = false
    }, 400)
  }

  function onPreviewMessage(msg: PreviewMessage) {
    switch (msg.type) {
      case 'preview.ready':
        ready.value = true
        updating.value = false
        announce(
          errorCount.value > 0
            ? `Preview loaded with ${errorCount.value} error${errorCount.value === 1 ? '' : 's'}`
            : 'Preview loaded',
        )
        break
      case 'preview.console': {
        const text = msg.args.join(' ')
        if (NOISE_PATTERNS.some((p) => p.test(text))) return
        pushEntry({ level: msg.level, text, at: Date.now() })
        break
      }
      case 'preview.error': {
        const where = msg.source ? ` (${shortSource(msg.source)}${msg.line ? `:${msg.line}` : ''})` : ''
        pushEntry({ level: 'error', text: `${msg.message}${where}`, at: Date.now() })
        if (!runtimeError.value && !errorDismissed.value) {
          runtimeError.value = {
            message: msg.message,
            source: msg.source ? shortSource(msg.source) : undefined,
            line: msg.line,
          }
        }
        if (!errorAnnounced) {
          errorAnnounced = true
          announceAlert(`Preview runtime error: ${msg.message}`)
        }
        break
      }
    }
  }

  function pushEntry(entry: ConsoleEntry) {
    const next = [...consoleEntries.value, entry]
    consoleEntries.value = next.length > MAX_CONSOLE_ENTRIES ? next.slice(-MAX_CONSOLE_ENTRIES) : next
  }

  function clearConsole() {
    consoleEntries.value = []
  }

  function dismissError() {
    runtimeError.value = null
    errorDismissed.value = true
  }

  function markLoaded() {
    // iframe load fired; if the bootstrap never signals ready, drop the
    // overlay after a grace period so a broken app doesn't spin forever.
    // Tracked so reset()/rebuild() cancel it — a stale timer from a previous
    // build must not hide the next build's overlay early.
    if (loadGraceTimer) clearTimeout(loadGraceTimer)
    loadGraceTimer = setTimeout(() => {
      if (!ready.value) updating.value = false
    }, 1500)
  }

  /**
   * Clear all per-project state. Without this, switching projects briefly
   * rendered the PREVIOUS project's app: the stale srcdoc stayed mounted
   * until the new project's Firestore files arrived and triggered a rebuild.
   * deviceMode survives — it is a viewer preference, not project content.
   */
  function reset() {
    if (overlayTimer) clearTimeout(overlayTimer)
    if (loadGraceTimer) clearTimeout(loadGraceTimer)
    srcdoc.value = ''
    srcdocKey.value++
    updating.value = false
    ready.value = false
    hasBuilt.value = false
    warnings.value = []
    consoleEntries.value = []
    consoleOpen.value = false
    runtimeError.value = null
    errorDismissed.value = false
    errorAnnounced = false
  }

  return {
    srcdoc,
    srcdocKey,
    updating,
    ready,
    hasBuilt,
    warnings,
    consoleEntries,
    consoleOpen,
    runtimeError,
    deviceMode,
    errorCount,
    warnCount,
    rebuild,
    onPreviewMessage,
    clearConsole,
    dismissError,
    markLoaded,
    reset,
  }
})

function shortSource(src: string): string {
  try {
    const u = new URL(src)
    return u.pathname.split('/').pop() ?? src
  } catch {
    return src.length > 40 ? src.slice(0, 40) + '…' : src
  }
}
