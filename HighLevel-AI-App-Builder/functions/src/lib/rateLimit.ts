import { db, Timestamp } from './db.js'
import { HttpError } from './http.js'

export interface RateLimitRule {
  scope: string
  limit: number
  windowSec: number
}

export const LIMITS = {
  generatePerMin: { scope: 'gen_m', limit: 5, windowSec: 60 },
  generatePerDay: { scope: 'gen_d', limit: 50, windowSec: 86_400 },
  proxyPerMin: { scope: 'proxy_m', limit: 60, windowSec: 60 },
  oauthPerHour: { scope: 'oauth_h', limit: 10, windowSec: 3_600 },
} satisfies Record<string, RateLimitRule>

/**
 * Fixed-window counter in Firestore (`rate_limits` is deny-all to clients).
 * Docs expire via a TTL policy on `expireAt`. Throws 429 with retryAfter.
 */
export async function checkRateLimit(uid: string, rules: RateLimitRule[]): Promise<void> {
  const now = Date.now()
  for (const rule of rules) {
    const windowKey = Math.floor(now / (rule.windowSec * 1000))
    const ref = db.doc(`rate_limits/${uid}_${rule.scope}_${windowKey}`)
    const allowed = await db.runTransaction(async (tx) => {
      const snap = await tx.get(ref)
      const n = ((snap.data()?.n as number | undefined) ?? 0) + 1
      if (n > rule.limit) return false
      tx.set(
        ref,
        { n, expireAt: Timestamp.fromMillis((windowKey + 2) * rule.windowSec * 1000) },
        { merge: true },
      )
      return true
    })
    if (!allowed) {
      const retryAfter = Math.ceil(((windowKey + 1) * rule.windowSec * 1000 - now) / 1000)
      throw new HttpError(429, 'rate_limited', { retryAfter })
    }
  }
}
