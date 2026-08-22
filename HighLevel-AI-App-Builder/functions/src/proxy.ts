import { onRequest } from 'firebase-functions/https'
import { z } from 'zod'
import { HL_CLIENT_SECRET, REGION } from './lib/env.js'
import { applyCors, HttpError, parseBody, requireAuth, sendError } from './lib/http.js'
import { checkRateLimit, LIMITS } from './lib/rateLimit.js'
import { log, newCid, sanitizeUpstreamError, UpstreamError } from './lib/log.js'
import { getConnection, hlFetch } from './hl/client.js'
import { buildUpstreamUrl, matchAllowlist } from './shared/allowlist.js'

const envelopeSchema = z.object({
  method: z.enum(['GET', 'POST', 'PUT']),
  path: z.string().min(1).max(200),
  params: z
    .record(z.string().max(40), z.union([z.string().max(200), z.number()]))
    .refine((r) => Object.keys(r).length <= 20, 'too many params')
    .optional(),
  body: z.unknown().optional(),
})

const MAX_BODY_JSON = 100_000

/** Tenant keys the client may never smuggle into write bodies. */
const STRIPPED_BODY_KEYS = ['companyId', 'altId', 'altType'] as const

/**
 * The HighLevel proxy — the ONLY path between browsers (and therefore
 * generated apps, via the parent bridge) and the HighLevel API.
 * Pipeline: CORS → auth → rate limit → envelope validation → allowlist
 * match → URL rebuilt from OUR template → locationId forced → headers built
 * from scratch → capped fetch → normalized errors.
 */
export const hlProxy = onRequest(
  {
    region: REGION,
    timeoutSeconds: 30,
    memory: '256MiB',
    maxInstances: 10,
    concurrency: 40,
    secrets: [HL_CLIENT_SECRET],
  },
  async (req, res) => {
    if (applyCors(req, res)) return
    let uid: string | undefined
    try {
      if (req.method !== 'POST') throw new HttpError(405, 'method_not_allowed')
      ;({ uid } = await requireAuth(req))
      await checkRateLimit(uid, [LIMITS.proxyPerMin])
      const envelope = parseBody(req, envelopeSchema)

      const match = matchAllowlist(envelope.method, envelope.path)
      if (!match) throw new HttpError(403, 'route_not_allowed')

      const conn = await getConnection(uid)
      if (!conn || conn.status !== 'connected') throw new HttpError(403, 'hl_not_connected')

      const url = buildUpstreamUrl(match, envelope.params, conn.locationId)

      let body: unknown
      if (envelope.method !== 'GET') {
        if (envelope.body !== undefined) {
          if (JSON.stringify(envelope.body).length > MAX_BODY_JSON) {
            throw new HttpError(413, 'body_too_large')
          }
          if (typeof envelope.body !== 'object' || envelope.body === null || Array.isArray(envelope.body)) {
            throw new HttpError(400, 'invalid_request', { detail: 'body must be an object' })
          }
        }
        const raw = { ...((envelope.body as Record<string, unknown>) ?? {}) }
        for (const key of STRIPPED_BODY_KEYS) delete raw[key]
        if (match.rule.locationIdInBody) {
          raw.locationId = conn.locationId // forced — client value never wins
        } else {
          delete raw.locationId
        }
        body = raw
      }

      const result = await hlFetch(uid, envelope.method, url, body)
      res.status(200).json(result.data)
    } catch (err) {
      if (err instanceof UpstreamError) {
        const cid = newCid()
        log.warn('hl upstream error', { cid, uid, ...sanitizeUpstreamError(err, req.body?.path) })
        if (err.status === 429) {
          res.status(429).json({ error: 'hl_rate_limited', cid, retryAfter: 10 })
        } else if (err.status === 401 || err.status === 403) {
          res.status(403).json({ error: 'hl_forbidden', cid })
        } else if (err.status === 404) {
          res.status(404).json({ error: 'hl_not_found', cid })
        } else if (err.status === 400 || err.status === 422) {
          // Pass through validation feedback (sanitized) so generated apps can
          // show something actionable, without leaking headers or internals.
          res.status(400).json({ error: 'hl_bad_request', cid, detail: safeDetail(err.bodyText) })
        } else {
          res.status(502).json({ error: 'hl_upstream_error', cid })
        }
        return
      }
      sendError(res, err, 'hlProxy', uid)
    }
  },
)

function safeDetail(bodyText: string): string {
  try {
    const parsed = JSON.parse(bodyText) as { message?: string | string[] }
    const msg = Array.isArray(parsed.message) ? parsed.message.join('; ') : parsed.message
    return (msg ?? 'invalid request').slice(0, 300)
  } catch {
    return 'invalid request'
  }
}
