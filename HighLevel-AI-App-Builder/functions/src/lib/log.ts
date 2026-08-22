import { logger } from 'firebase-functions'
import { randomUUID } from 'node:crypto'

/** Correlation id: returned to clients on errors, attached to server logs. */
export function newCid(): string {
  return randomUUID().slice(0, 8)
}

/**
 * Error shape safe for logs. NEVER log raw upstream errors: HTTP client error
 * objects can carry the Authorization header (and token responses carry
 * tokens). Only status, a query-less path, and a truncated body survive.
 */
export function sanitizeUpstreamError(err: unknown, path?: string): Record<string, unknown> {
  const safePath = path?.split('?')[0]
  if (err instanceof UpstreamError) {
    return { status: err.status, path: safePath, body: truncate(err.bodyText, 500) }
  }
  if (err instanceof Error) {
    return { name: err.name, message: truncate(err.message, 300), path: safePath }
  }
  return { message: truncate(String(err), 300), path: safePath }
}

export function truncate(value: unknown, max: number): string {
  const s = typeof value === 'string' ? value : JSON.stringify(value ?? '')
  return s.length > max ? s.slice(0, max) + '…' : s
}

/** Non-2xx response from HighLevel (body already read, headers discarded). */
export class UpstreamError extends Error {
  constructor(
    readonly status: number,
    readonly bodyText: string,
  ) {
    super(`upstream ${status}`)
  }
}

export const log = {
  info(msg: string, data?: Record<string, unknown>) {
    logger.info(msg, data)
  },
  warn(msg: string, data?: Record<string, unknown>) {
    logger.warn(msg, data)
  },
  error(msg: string, data?: Record<string, unknown>) {
    logger.error(msg, data)
  },
}
