import type { Request } from 'firebase-functions/https'
import type { Response } from 'express'
import type { ZodType } from 'zod'
import { adminAuth } from './db.js'
import { allowedOrigins } from './env.js'
import { log, newCid } from './log.js'

export class HttpError extends Error {
  constructor(
    readonly status: number,
    readonly clientMessage: string,
    readonly extra?: Record<string, unknown>,
  ) {
    super(clientMessage)
  }
}

/**
 * Exact-origin CORS. Returns true when the request was fully handled
 * (OPTIONS preflight) and the caller must stop.
 */
export function applyCors(req: Request, res: Response, methods = 'POST'): boolean {
  const origin = req.headers.origin
  if (origin && allowedOrigins().includes(origin)) {
    res.set('Access-Control-Allow-Origin', origin)
    res.set('Vary', 'Origin')
  }
  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', methods)
    res.set('Access-Control-Allow-Headers', 'Authorization, Content-Type')
    res.set('Access-Control-Max-Age', '3600')
    res.status(204).send('')
    return true
  }
  return false
}

/** Verify the Firebase ID token from the Authorization header. */
export async function requireAuth(req: Request): Promise<{ uid: string }> {
  const header = req.headers.authorization ?? ''
  const token = header.startsWith('Bearer ') ? header.slice(7) : ''
  if (!token) throw new HttpError(401, 'unauthenticated')
  try {
    const decoded = await adminAuth.verifyIdToken(token)
    return { uid: decoded.uid }
  } catch {
    throw new HttpError(401, 'unauthenticated')
  }
}

/** Parse + validate a JSON body (functions runtime pre-parses req.body). */
export function parseBody<T>(req: Request, schema: ZodType<T>): T {
  const parsed = schema.safeParse(req.body ?? {})
  if (!parsed.success) {
    throw new HttpError(400, 'invalid_request', {
      detail: parsed.error.issues[0]?.message,
    })
  }
  return parsed.data
}

/** Uniform error responder: generic client message + correlation id. */
export function sendError(res: Response, err: unknown, route: string, uid?: string): void {
  const cid = newCid()
  if (err instanceof HttpError) {
    log.warn(`${route} ${err.status}`, { cid, uid, msg: err.clientMessage, ...err.extra })
    res.status(err.status).json({ error: err.clientMessage, cid, ...err.extra })
    return
  }
  log.error(`${route} 500`, {
    cid,
    uid,
    err: err instanceof Error ? { name: err.name, message: err.message } : String(err),
  })
  res.status(500).json({ error: 'internal', cid })
}
