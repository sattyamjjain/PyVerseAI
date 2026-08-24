import { onRequest } from 'firebase-functions/https'
import { db } from './lib/db.js'
import { REGION } from './lib/env.js'

const startedAt = Date.now()

/**
 * Unauthenticated liveness/readiness probe for uptime monitoring.
 * Liveness = the function responds at all; readiness = Firestore is
 * reachable through the Admin SDK (one document read, no writes).
 */
export const healthz = onRequest(
  { region: REGION, timeoutSeconds: 10, memory: '256MiB', maxInstances: 1 },
  async (req, res) => {
    if (req.method !== 'GET') {
      res.status(405).set('Allow', 'GET').send('method_not_allowed')
      return
    }
    let firestore: 'ok' | 'error' = 'ok'
    try {
      await db.collection('health').doc('probe').get()
    } catch {
      firestore = 'error'
    }
    const healthy = firestore === 'ok'
    res
      .status(healthy ? 200 : 503)
      .set('Cache-Control', 'no-store')
      .json({
        status: healthy ? 'ok' : 'degraded',
        checks: { firestore },
        uptimeSeconds: Math.round((Date.now() - startedAt) / 1000),
      })
  },
)
