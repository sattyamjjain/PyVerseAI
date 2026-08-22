import { onBeforeUnmount, onMounted } from 'vue'

export const isMac = /mac/i.test(
  (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData?.platform ??
    navigator.platform,
)

/** Display label for the platform modifier. */
export const modKeyLabel = isMac ? '⌘' : 'Ctrl'

/** aria-keyshortcuts token for the platform modifier (spec wants key names, not glyphs). */
export const ariaMod = isMac ? 'Meta' : 'Control'

export interface ShortcutDef {
  /** KeyboardEvent.key value ('k', 's', '.', 'Enter', 'F6'…). */
  key: string
  /** Requires the platform modifier (⌘ on mac, Ctrl elsewhere). */
  mod?: boolean
  shift?: boolean
  /** Fire even when focus is inside an input/textarea/contenteditable. */
  allowInInput?: boolean
  handler: (e: KeyboardEvent) => void
}

function isEditableTarget(e: KeyboardEvent): boolean {
  const el = e.target as HTMLElement | null
  if (!el) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable
}

/**
 * Global keyboard shortcuts for the mounting component's lifetime.
 * Monaco swallows its own keys; combos that must work inside the editor are
 * additionally registered as Monaco commands (see CodeEditor).
 */
export function useShortcuts(defs: ShortcutDef[]) {
  const onKeydown = (e: KeyboardEvent) => {
    for (const def of defs) {
      const mod = isMac ? e.metaKey : e.ctrlKey
      if (def.mod && !mod) continue
      if (!def.mod && mod) continue
      if (Boolean(def.shift) !== e.shiftKey) continue
      if (e.key.toLowerCase() !== def.key.toLowerCase()) continue
      if (!def.allowInInput && !def.mod && isEditableTarget(e)) continue
      e.preventDefault()
      def.handler(e)
      return
    }
  }
  onMounted(() => window.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
}
