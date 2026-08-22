import { readonly, ref } from 'vue'

/**
 * The app's ONLY live-region channel (accessibility review item A5).
 * `announce` → role="status" (polite): generation state transitions, restores.
 * `alert`    → role="alert" (assertive): failures, connection loss.
 * Polite announcements are coalesced to at most one per 1.5s (latest wins) so
 * fast multi-file generations don't flood the screen-reader queue.
 * CI-grep rule: aria-live/role="status"/role="alert" appear only in
 * AppAnnouncer.vue (plus vendored sonner internals, which are suppressed).
 */
const politeText = ref('')
const alertText = ref('')

let pending: string | null = null
let timer: ReturnType<typeof setTimeout> | null = null
let lastAnnounce = 0
const COALESCE_MS = 1500

function flush() {
  if (pending !== null) {
    // Re-setting identical text doesn't re-announce; nudge with a space toggle.
    politeText.value = pending === politeText.value ? pending + ' ' : pending
    pending = null
    lastAnnounce = Date.now()
  }
  timer = null
}

export function announce(text: string) {
  pending = text
  if (timer) return
  const elapsed = Date.now() - lastAnnounce
  if (elapsed >= COALESCE_MS) flush()
  else timer = setTimeout(flush, COALESCE_MS - elapsed)
}

export function announceAlert(text: string) {
  alertText.value = text === alertText.value ? text + ' ' : text
}

export function useAnnouncerState() {
  return { politeText: readonly(politeText), alertText: readonly(alertText) }
}
