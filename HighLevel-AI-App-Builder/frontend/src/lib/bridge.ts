import { z } from 'zod'
import { matchAllowlist, type AllowRule } from '@shared/allowlist'
import type { BridgeHlEventMessage, IframeToParentMessage, PreviewMessage } from '@shared/protocol'
import { callFn, ApiError } from '@/lib/api'

const MAX_CONCURRENT = 8
const MAX_MESSAGE_BYTES = 1_000_000

const requestSchema = z.object({
  v: z.literal(1),
  type: z.literal('hl.request'),
  id: z.string().min(1).max(128),
  method: z.enum(['GET', 'POST', 'PUT']),
  path: z.string().min(1).max(200),
  params: z.record(z.string(), z.union([z.string(), z.number()])).optional(),
  body: z.unknown().optional(),
})

const previewMessageSchema = z.union([
  z.object({ v: z.literal(1), type: z.literal('preview.ready') }),
  z.object({
    v: z.literal(1),
    type: z.literal('preview.console'),
    level: z.enum(['log', 'info', 'warn', 'error']),
    args: z.array(z.string()).max(16),
  }),
  z.object({
    v: z.literal(1),
    type: z.literal('preview.error'),
    message: z.string().max(4096),
    source: z.string().max(1024).optional(),
    line: z.number().optional(),
    col: z.number().optional(),
    stack: z.string().max(8192).optional(),
  }),
])

export interface ConfirmInfo {
  label: string
  method: string
  path: string
  detail: string
}

export interface BridgeOptions {
  /** Current preview iframe contentWindow — identity is the ONLY trust check
   *  (a sandboxed srcdoc iframe's origin is the string "null"). */
  getIframeWindow: () => Window | null
  /** Show the write-confirmation dialog; resolves with the user's decision. */
  requestConfirm: (info: ConfirmInfo) => Promise<boolean>
  onPreviewMessage: (msg: PreviewMessage) => void
}

export class PreviewBridge {
  private inFlight = 0
  private listener: ((e: MessageEvent) => void) | null = null

  constructor(private readonly opts: BridgeOptions) {}

  start(): void {
    if (this.listener) return
    this.listener = (e) => void this.onMessage(e)
    window.addEventListener('message', this.listener)
  }

  stop(): void {
    if (this.listener) window.removeEventListener('message', this.listener)
    this.listener = null
  }

  /** Broadcast a HighLevel webhook event into the preview. */
  broadcast(msg: BridgeHlEventMessage): void {
    this.opts.getIframeWindow()?.postMessage(msg, '*')
  }

  private async onMessage(event: MessageEvent): Promise<void> {
    const win = this.opts.getIframeWindow()
    if (!win || event.source !== win) return // identity check — never event.origin

    const raw = event.data as IframeToParentMessage | null
    if (!raw || typeof raw !== 'object') return

    const preview = previewMessageSchema.safeParse(raw)
    if (preview.success) {
      this.opts.onPreviewMessage(preview.data)
      return
    }

    const parsed = requestSchema.safeParse(raw)
    if (!parsed.success) return
    const req = parsed.data

    const respond = (payload: { ok: boolean; status: number; data?: unknown; error?: string }) => {
      // Re-check identity: a navigated/rebuilt frame must never receive stale
      // responses (responses go out with '*' — opaque origins can't be named).
      const current = this.opts.getIframeWindow()
      if (current !== win) return
      current?.postMessage({ v: 1, type: 'hl.response', id: req.id, ...payload }, '*')
    }

    try {
      if (JSON.stringify(raw).length > MAX_MESSAGE_BYTES) {
        respond({ ok: false, status: 413, error: 'request too large' })
        return
      }
    } catch {
      respond({ ok: false, status: 400, error: 'unserializable request' })
      return
    }

    if (this.inFlight >= MAX_CONCURRENT) {
      respond({ ok: false, status: 429, error: 'too many concurrent requests' })
      return
    }

    const match = matchAllowlist(req.method, req.path)
    if (!match) {
      respond({ ok: false, status: 403, error: 'endpoint not allowed' })
      return
    }

    if (match.rule.requiresConfirm) {
      const allowed = await this.opts.requestConfirm(confirmInfo(match.rule, req.path, req.body))
      if (!allowed) {
        respond({ ok: false, status: 403, error: 'user_denied' })
        return
      }
    }

    this.inFlight++
    try {
      const data = await callFn<unknown>('hlProxy', {
        method: req.method,
        path: req.path,
        params: req.params,
        body: req.body,
      })
      respond({ ok: true, status: 200, data })
    } catch (err) {
      if (err instanceof ApiError) {
        respond({ ok: false, status: err.status || 502, error: err.message })
      } else {
        respond({ ok: false, status: 502, error: 'Request failed' })
      }
    } finally {
      this.inFlight--
    }
  }
}

function confirmInfo(rule: AllowRule, path: string, body: unknown): ConfirmInfo {
  let detail = `${rule.method} ${path}`
  if (body && typeof body === 'object') {
    const entries = Object.entries(body as Record<string, unknown>)
      .filter(([, v]) => typeof v === 'string' || typeof v === 'number')
      .slice(0, 6)
      .map(([k, v]) => `${k}: ${String(v).slice(0, 60)}`)
    if (entries.length) detail += '\n' + entries.join('\n')
  }
  return { label: rule.label, method: rule.method, path, detail }
}
