import { EventSourceParserStream } from 'eventsource-parser/stream'
import { FUNCTIONS_BASE, idToken } from '@/lib/firebase'
import type { GenerateRequest, SseEvent } from '@shared/protocol'

export interface StreamHandle {
  cancel(): void
  finished: Promise<void>
}

export interface StreamCallbacks {
  onEvent(event: SseEvent): void
  /** Terminal transport-level failure (network drop, stall, HTTP error). */
  onTransportError(err: Error): void
  /** Stream closed after a terminal `done`/`error` event was seen. */
  onClose(sawTerminal: boolean): void
}

const STALL_MS = 30_000

/**
 * Authenticated SSE over fetch (EventSource can't send Authorization headers
 * or POST bodies). Heartbeat comments reset the stall watchdog; a terminal
 * `done` or `error` event ends the stream cleanly. Abort via handle.cancel().
 */
export function streamGeneration(body: GenerateRequest, cb: StreamCallbacks): StreamHandle {
  const ac = new AbortController()
  let stallTimer: ReturnType<typeof setTimeout> | null = null
  let sawTerminal = false
  let cancelled = false

  const bump = () => {
    if (stallTimer) clearTimeout(stallTimer)
    stallTimer = setTimeout(() => {
      ac.abort(new DOMException('stall', 'AbortError'))
      cb.onTransportError(new Error('Connection stalled — no data for 30 seconds.'))
    }, STALL_MS)
  }

  const finished = (async () => {
    try {
      const token = await idToken()
      bump()
      const res = await fetch(`${FUNCTIONS_BASE}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(body),
        signal: ac.signal,
      })
      if (!res.ok || !res.body) {
        let code = `HTTP ${res.status}`
        try {
          const j = (await res.json()) as { error?: string }
          if (j.error) code = j.error
        } catch {
          /* body not json */
        }
        throw new Error(code)
      }

      // Raw byte reader wrapped manually so heartbeat COMMENT frames also
      // reset the watchdog (the parser swallows comments silently).
      const reader = res.body
        .pipeThrough(new TextDecoderStream())
        .pipeThrough(
          new TransformStream<string, string>({
            transform(chunk, controller) {
              bump()
              controller.enqueue(chunk)
            },
          }),
        )
        .pipeThrough(new EventSourceParserStream({ onError: 'terminate' }))
        .getReader()

      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        if (!value.event) continue
        let parsed: SseEvent
        try {
          parsed = { ...(JSON.parse(value.data) as object), type: value.event } as SseEvent
        } catch {
          continue // malformed frame — skip rather than kill the stream
        }
        cb.onEvent(parsed)
        if (parsed.type === 'done' || parsed.type === 'error') {
          sawTerminal = true
          ac.abort() // close the connection; server already finished
          break
        }
      }
      cb.onClose(sawTerminal)
    } catch (err) {
      if (cancelled || sawTerminal) {
        cb.onClose(sawTerminal)
        return
      }
      if (err instanceof DOMException && err.name === 'AbortError') {
        cb.onClose(false)
        return
      }
      cb.onTransportError(err instanceof Error ? err : new Error(String(err)))
      cb.onClose(false)
    } finally {
      if (stallTimer) clearTimeout(stallTimer)
    }
  })()

  return {
    cancel() {
      cancelled = true
      ac.abort()
    },
    finished,
  }
}
