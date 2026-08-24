import { db, FieldValue, Timestamp } from '../lib/db.js'
import { HL_CLIENT_ID, HL_CLIENT_SECRET, HL_REDIRECT_URI, isMockMode } from '../lib/env.js'
import { HttpError } from '../lib/http.js'
import { log, sanitizeUpstreamError, UpstreamError } from '../lib/log.js'
import { HL_API_BASE, hlVersionFor } from '../shared/allowlist.js'
import { mockHlFetch, MOCK_TOKENS } from './mock.js'

export interface HlConnection {
  accessToken: string
  refreshToken: string
  locationId: string
  companyId: string
  scopes: string
  expiresAt: Timestamp
  refreshLockAt?: Timestamp
  status: 'connected' | 'needs_reconnect'
  userId?: string
}

const TOKEN_URL = `${HL_API_BASE}/oauth/token`
const SKEW_MS = 5 * 60 * 1000 // refresh when <5 min remain
const LEASE_MS = 15_000
const FETCH_TIMEOUT_MS = 10_000
const MAX_RESPONSE_BYTES = 5_000_000

export interface HlTokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  scope?: string
  locationId?: string
  companyId?: string
  userType?: string
  userId?: string
}

/** OAuth code/refresh exchange — form-urlencoded per the HighLevel spec. */
async function tokenRequest(fields: Record<string, string>): Promise<HlTokenResponse> {
  const body = new URLSearchParams({
    client_id: HL_CLIENT_ID.value(),
    client_secret: HL_CLIENT_SECRET.value(),
    ...fields,
  })
  const res = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
    body,
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  })
  const text = await res.text()
  if (!res.ok) throw new UpstreamError(res.status, text)
  return JSON.parse(text) as HlTokenResponse
}

export function exchangeAuthCode(code: string): Promise<HlTokenResponse> {
  if (isMockMode()) return Promise.resolve(MOCK_TOKENS)
  return tokenRequest({
    grant_type: 'authorization_code',
    code,
    user_type: 'Location',
    // Must byte-match the authorize request's redirect_uri or the exchange 400s.
    redirect_uri: HL_REDIRECT_URI.value(),
  })
}

function refreshTokens(refreshToken: string): Promise<HlTokenResponse> {
  if (isMockMode()) return Promise.resolve(MOCK_TOKENS)
  return tokenRequest({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    user_type: 'Location',
  })
}

export async function getConnection(uid: string): Promise<HlConnection | null> {
  const snap = await db.doc(`hl_connections/${uid}`).get()
  return (snap.data() as HlConnection | undefined) ?? null
}

export async function saveConnection(uid: string, tokens: HlTokenResponse): Promise<HlConnection> {
  if (!tokens.locationId) {
    throw new HttpError(400, 'hl_no_location', {
      detail: 'Install the app on a location (sub-account), not at agency level.',
    })
  }
  const conn: HlConnection = {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    locationId: tokens.locationId,
    companyId: tokens.companyId ?? '',
    scopes: tokens.scope ?? '',
    expiresAt: Timestamp.fromMillis(Date.now() + tokens.expires_in * 1000),
    status: 'connected',
    ...(tokens.userId ? { userId: tokens.userId } : {}),
  }
  await db.doc(`hl_connections/${uid}`).set(conn)
  return conn
}

export async function deleteConnection(uid: string): Promise<void> {
  await db.doc(`hl_connections/${uid}`).delete()
}

async function markNeedsReconnect(uid: string): Promise<void> {
  await db
    .doc(`hl_connections/${uid}`)
    .set({ status: 'needs_reconnect', accessToken: '', refreshToken: '' }, { merge: true })
  await db
    .doc(`users/${uid}`)
    .set({ hl: { status: 'needs_reconnect' } }, { mergeFields: ['hl.status'] })
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/**
 * Valid access token for the caller, refreshing when near expiry.
 * HighLevel ROTATES refresh tokens (single-use), so refreshes are serialized
 * with a short Firestore lease and the rotated pair is persisted immediately.
 * The network call happens OUTSIDE the transaction (transactions retry).
 */
export async function getValidHlToken(uid: string, depth = 0): Promise<HlConnection> {
  const conn = await getConnection(uid)
  if (!conn || conn.status !== 'connected') throw new HttpError(403, 'hl_not_connected')
  if (isMockMode()) return conn
  if (conn.expiresAt.toMillis() - Date.now() > SKEW_MS) return conn
  if (depth > 4) throw new HttpError(503, 'hl_refresh_busy')

  const ref = db.doc(`hl_connections/${uid}`)
  type Lease =
    | { gone: true }
    | { fresh: HlConnection }
    | { wait: true }
    | { doRefresh: true; refreshToken: string }
  const lease = await db.runTransaction<Lease>(async (tx) => {
    const snap = await tx.get(ref)
    const s = snap.data() as HlConnection | undefined
    if (!s || s.status !== 'connected') return { gone: true as const }
    if (s.expiresAt.toMillis() - Date.now() > SKEW_MS) return { fresh: s }
    const lockAge = Date.now() - (s.refreshLockAt?.toMillis() ?? 0)
    if (lockAge < LEASE_MS) return { wait: true as const }
    tx.update(ref, { refreshLockAt: FieldValue.serverTimestamp() })
    return { doRefresh: true as const, refreshToken: s.refreshToken }
  })

  if ('gone' in lease) throw new HttpError(403, 'hl_not_connected')
  if ('fresh' in lease) return lease.fresh
  if ('wait' in lease) {
    await sleep(1500)
    return getValidHlToken(uid, depth + 1)
  }

  try {
    const t = await refreshTokens(lease.refreshToken)
    await ref.update({
      accessToken: t.access_token,
      refreshToken: t.refresh_token, // rotated — the old one is dead
      expiresAt: Timestamp.fromMillis(Date.now() + t.expires_in * 1000),
      refreshLockAt: FieldValue.delete(),
    })
    return (await getConnection(uid))!
  } catch (err) {
    log.warn('hl token refresh failed', sanitizeUpstreamError(err, '/oauth/token'))
    if (err instanceof UpstreamError && (err.status === 400 || err.status === 401)) {
      await markNeedsReconnect(uid)
      throw new HttpError(403, 'hl_not_connected')
    }
    // Transient failure: drop the lease so the next caller can retry.
    await ref.update({ refreshLockAt: FieldValue.delete() }).catch(() => {})
    throw new HttpError(502, 'hl_upstream_error')
  }
}

export interface HlFetchResult {
  status: number
  data: unknown
}

/**
 * Authenticated HighLevel API call. Headers are built from scratch — no
 * client header is ever forwarded. Retries exactly once on 401 by forcing
 * the refresh path.
 */
export async function hlFetch(
  uid: string,
  method: 'GET' | 'POST' | 'PUT',
  url: URL,
  body?: unknown,
  retried = false,
): Promise<HlFetchResult> {
  if (isMockMode()) return mockHlFetch(method, url, body)
  const conn = await getValidHlToken(uid)
  const res = await fetch(url, {
    method,
    headers: {
      Authorization: `Bearer ${conn.accessToken}`,
      Version: hlVersionFor(url.pathname),
      Accept: 'application/json',
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  })

  if (res.status === 401 && !retried) {
    await db
      .doc(`hl_connections/${uid}`)
      .update({ expiresAt: Timestamp.fromMillis(0) })
      .catch(() => {})
    return hlFetch(uid, method, url, body, true)
  }

  const contentLength = Number(res.headers.get('content-length') ?? 0)
  if (contentLength > MAX_RESPONSE_BYTES) throw new UpstreamError(502, 'response too large')
  const text = await res.text()
  if (text.length > MAX_RESPONSE_BYTES) throw new UpstreamError(502, 'response too large')

  if (!res.ok) throw new UpstreamError(res.status, text)
  try {
    return { status: res.status, data: text ? JSON.parse(text) : null }
  } catch {
    throw new UpstreamError(502, 'non-JSON upstream response')
  }
}
