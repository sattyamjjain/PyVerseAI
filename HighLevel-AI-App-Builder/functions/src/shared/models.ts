/**
 * Firestore document shapes shared by the SPA and Cloud Functions.
 * Timestamps are structurally typed so both firebase-admin and the web SDK fit.
 */

export interface TsLike {
  toMillis(): number
  toDate(): Date
}

export interface UserDoc {
  displayName: string
  email: string
  createdAt: TsLike
  /** HighLevel connection mirror — written ONLY by the Admin SDK. */
  hl?: {
    status: 'connected' | 'needs_reconnect' | 'disconnected'
    locationId: string
    locationName: string
    connectedAt: TsLike
  }
}

export type ProjectStatus = 'draft' | 'generating' | 'ready' | 'error'

export interface ProjectDoc {
  ownerUid: string
  name: string
  description: string
  locationId: string | null
  status: ProjectStatus
  softDeleted: boolean
  createdAt: TsLike
  updatedAt: TsLike
}

export interface FileDoc {
  path: string
  content: string
  updatedAt: TsLike
}

export interface MessageDoc {
  role: 'user' | 'assistant'
  content: string
  createdAt: TsLike
  generationId?: string
  /** Assistant messages carry generation metadata for the summary card. */
  meta?: {
    filesChanged: string[]
    filesDeleted: string[]
    durationMs: number
    added: number
    removed: number
    snapshotId?: string
    stopReason?: string
    error?: string
  }
}

export type GenerationStatus = 'running' | 'done' | 'error' | 'aborted'

export interface GenerationDoc {
  status: GenerationStatus
  mode: 'create' | 'refine'
  model: string
  prompt: string
  filesWritten: string[]
  error?: string
  usage?: { inputTokens: number; outputTokens: number; cacheReadInputTokens: number }
  startedAt: TsLike
  finishedAt?: TsLike
}

export interface SnapshotDoc {
  label: string
  promptExcerpt: string
  fileCount: number
  added: number
  removed: number
  createdAt: TsLike
  generationId?: string
  kind: 'generation' | 'backup' | 'restore' | 'stopped'
}

export interface HlEventDoc {
  ownerUid: string
  locationId: string
  type: string
  summary: string
  payload: Record<string, unknown>
  createdAt: TsLike
}
