/**
 * Wire protocol shared between Cloud Functions, the SPA, and the preview
 * bridge. This module is imported by BOTH the functions build (NodeNext) and
 * the Vite frontend (via the @shared alias) — keep it dependency-free.
 */

// ─── SSE generation stream ───────────────────────────────────────────────────
// The generate endpoint parses the LLM stream server-side and emits semantic
// events; the browser never sees raw model output. Frames are standard SSE:
//   id: <seq>\nevent: <type>\ndata: <one-line JSON>\n\n
// plus comment heartbeats (": ping") every 15s.

export type GenerationMode = 'create' | 'refine'

export type StopReason = 'end_turn' | 'max_tokens' | 'aborted' | 'refused'

export type SseErrorCode =
  | 'overloaded'
  | 'rate_limited'
  | 'timeout'
  | 'policy_violation'
  | 'file_too_large'
  | 'parse_failed'
  | 'refused'
  | 'hl_not_connected'
  | 'internal'

export interface TokenUsage {
  inputTokens: number
  outputTokens: number
  cacheReadInputTokens: number
}

export type SseEvent =
  | { type: 'generation_start'; generationId: string; mode: GenerationMode; model: string }
  | { type: 'narration_delta'; text: string }
  | { type: 'file_start'; path: string; index: number; action: 'create' | 'update' }
  | { type: 'file_delta'; path: string; content: string }
  | {
      type: 'file_complete'
      path: string
      sizeBytes: number
      truncated: boolean
      /** Present when server-side finalization changed bytes — authoritative content. */
      content?: string
    }
  | { type: 'file_deleted'; path: string }
  | { type: 'snapshot_created'; snapshotId: string; filesChanged: string[] }
  | { type: 'done'; stopReason: StopReason; usage?: TokenUsage; filesWritten: string[] }
  | { type: 'error'; code: SseErrorCode; message: string; recoverable: boolean }

export type SseEventType = SseEvent['type']

/** Client → generate endpoint request body. */
export interface GenerateRequest {
  projectId: string
  prompt: string
  /** UI model toggle; the server maps this to a real model id. */
  model: 'fast' | 'best'
}

// ─── Preview bridge (postMessage RPC) ────────────────────────────────────────
// The sandboxed srcdoc iframe has NO network (CSP connect-src 'none'). The
// injected `genesis` SDK posts requests to the parent; the parent validates
// them against the shared allowlist, attaches the user's Firebase ID token,
// calls the hlProxy function, and posts the result back. Correlation by id.

export const BRIDGE_VERSION = 1 as const

export interface BridgeRequestMessage {
  v: typeof BRIDGE_VERSION
  type: 'hl.request'
  id: string
  method: 'GET' | 'POST' | 'PUT'
  path: string
  params?: Record<string, string | number>
  body?: unknown
}

export interface BridgeResponseMessage {
  v: typeof BRIDGE_VERSION
  type: 'hl.response'
  id: string
  ok: boolean
  status: number
  data?: unknown
  error?: string
}

/** Boot/diagnostics messages from the preview bootstrap script. */
export type PreviewMessage =
  | { v: typeof BRIDGE_VERSION; type: 'preview.ready' }
  | {
      v: typeof BRIDGE_VERSION
      type: 'preview.console'
      level: 'log' | 'info' | 'warn' | 'error'
      args: string[]
    }
  | {
      v: typeof BRIDGE_VERSION
      type: 'preview.error'
      message: string
      source?: string
      line?: number
      col?: number
      stack?: string
    }

/** Parent → iframe broadcast when a HighLevel webhook event lands. */
export interface BridgeHlEventMessage {
  v: typeof BRIDGE_VERSION
  type: 'hl.event'
  event: 'contactCreated' | 'contactUpdated' | 'contactDeleted' | 'inboundMessage' | 'appointmentCreated' | 'appointmentUpdated'
  payload: Record<string, unknown>
}

export type ParentToIframeMessage = BridgeResponseMessage | BridgeHlEventMessage
export type IframeToParentMessage = BridgeRequestMessage | PreviewMessage

// ─── hlProxy HTTP envelope ───────────────────────────────────────────────────
// The SPA (parent) forwards bridge requests to the proxy with this body.

export interface HlProxyRequest {
  method: 'GET' | 'POST' | 'PUT'
  path: string
  params?: Record<string, string | number>
  body?: unknown
}

export interface HlProxyErrorBody {
  error: string
  cid?: string
  retryAfter?: number
}
