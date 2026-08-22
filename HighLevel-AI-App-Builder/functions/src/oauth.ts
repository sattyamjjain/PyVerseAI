import { onRequest } from 'firebase-functions/https'
import { z } from 'zod'
import { db, FieldValue, Timestamp } from './lib/db.js'
import {
  allowedOrigins,
  HL_CLIENT_ID,
  HL_CLIENT_SECRET,
  HL_REDIRECT_URI,
  isMockMode,
  REGION,
} from './lib/env.js'
import { applyCors, HttpError, parseBody, requireAuth, sendError } from './lib/http.js'
import { checkRateLimit, LIMITS } from './lib/rateLimit.js'
import { log, sanitizeUpstreamError } from './lib/log.js'
import { deleteConnection, exchangeAuthCode, hlFetch, saveConnection } from './hl/client.js'
import { HL_API_BASE } from './shared/allowlist.js'

/** Space-joined scopes requested at install (must be enabled on the HL app). */
export const HL_SCOPES = [
  'contacts.readonly',
  'contacts.write',
  'conversations.readonly',
  'conversations/message.readonly',
  'conversations/message.write',
  'calendars.readonly',
  'calendars/events.readonly',
  'calendars/events.write',
  'locations.readonly',
  'users.readonly',
].join(' ')

const AUTHORIZE_URL = 'https://marketplace.gohighlevel.com/v2/oauth/chooselocation'
const STATE_TTL_MS = 15 * 60_000

/** Begin the OAuth flow: mint a single-use state nonce, return the URL. */
export const hlAuthStart = onRequest(
  { region: REGION, timeoutSeconds: 30, memory: '256MiB', maxInstances: 2 },
  async (req, res) => {
    if (applyCors(req, res)) return
    let uid: string | undefined
    try {
      if (req.method !== 'POST') throw new HttpError(405, 'method_not_allowed')
      ;({ uid } = await requireAuth(req))
      await checkRateLimit(uid, [LIMITS.oauthPerHour])

      const origin = req.headers.origin ?? ''
      if (!allowedOrigins().includes(origin)) throw new HttpError(403, 'bad_origin')

      const stateRef = db.collection('oauth_states').doc()
      await stateRef.set({
        uid,
        returnOrigin: origin,
        createdAt: FieldValue.serverTimestamp(),
        expireAt: Timestamp.fromMillis(Date.now() + STATE_TTL_MS),
      })

      const redirectUri = HL_REDIRECT_URI.value()
      if (!redirectUri) throw new HttpError(500, 'misconfigured', { detail: 'HL_REDIRECT_URI unset' })

      let url: string
      if (isMockMode()) {
        url = `${redirectUri}?code=mock-code&state=${stateRef.id}`
      } else {
        const params = new URLSearchParams({
          response_type: 'code',
          redirect_uri: redirectUri,
          client_id: HL_CLIENT_ID.value(),
          scope: HL_SCOPES,
          state: stateRef.id,
        })
        url = `${AUTHORIZE_URL}?${params}`
      }
      res.json({ url })
    } catch (err) {
      sendError(res, err, 'hlAuthStart', uid)
    }
  },
)

/** Tiny HTML page that reports the result to the opener and closes itself. */
function callbackPage(ok: boolean, message: string, returnOrigin: string | null): string {
  const payload = JSON.stringify({ type: 'genesis:oauth', ok })
  const target = JSON.stringify(returnOrigin ?? '')
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Genesis — HighLevel</title>
<style>body{font-family:system-ui,sans-serif;background:#121419;color:#e6e8ee;display:grid;place-items:center;min-height:100vh;margin:0}main{text-align:center;max-width:420px;padding:24px}h1{font-size:18px}p{color:#99a0ad;font-size:14px}</style>
</head><body><main>
<h1>${ok ? 'HighLevel connected' : 'Connection failed'}</h1>
<p>${message}</p>
<p>You can close this window.</p>
<script>
  (function () {
    var target = ${target};
    if (window.opener && target) {
      try { window.opener.postMessage(${payload}, target); } catch (e) {}
    }
    setTimeout(function () { window.close(); }, ${ok ? 800 : 4000});
  })();
</script>
</main></body></html>`
}

/**
 * OAuth redirect target — registered VERBATIM as a Redirect URL in the
 * HighLevel app settings. No Firebase auth here (it's a top-level redirect);
 * the single-use state nonce binds the callback to the initiating user.
 */
export const hlAuthCallback = onRequest(
  { region: REGION, timeoutSeconds: 60, memory: '256MiB', maxInstances: 2, secrets: [HL_CLIENT_SECRET] },
  async (req, res) => {
    res.set('Content-Type', 'text/html; charset=utf-8')
    const code = typeof req.query.code === 'string' ? req.query.code : ''
    const state = typeof req.query.state === 'string' ? req.query.state : ''
    try {
      if (!code) throw new Error('missing authorization code')
      if (!state) {
        // Marketplace-initiated installs arrive without our state — we cannot
        // bind them to a Firebase user, so ask to start from the app.
        res
          .status(400)
          .send(callbackPage(false, 'Please start the connection from inside Genesis.', null))
        return
      }
      const stateRef = db.doc(`oauth_states/${state}`)
      const stateSnap = await stateRef.get()
      const stateData = stateSnap.data() as
        | { uid: string; returnOrigin: string; expireAt: Timestamp }
        | undefined
      await stateRef.delete().catch(() => {}) // single-use
      if (!stateData || stateData.expireAt.toMillis() < Date.now()) {
        res.status(400).send(callbackPage(false, 'This sign-in link expired — try again from Genesis.', null))
        return
      }
      const { uid, returnOrigin } = stateData

      const tokens = await exchangeAuthCode(code)
      const conn = await saveConnection(uid, tokens)

      let locationName = 'Connected location'
      try {
        const loc = await hlFetch(uid, 'GET', new URL(`/locations/${conn.locationId}`, HL_API_BASE))
        const data = loc.data as { location?: { name?: string } }
        locationName = data.location?.name ?? locationName
      } catch (err) {
        log.warn('location name fetch failed', sanitizeUpstreamError(err, '/locations'))
      }

      await db.doc(`users/${uid}`).set(
        {
          hl: {
            status: 'connected',
            locationId: conn.locationId,
            locationName,
            connectedAt: FieldValue.serverTimestamp(),
          },
        },
        { merge: true },
      )
      log.info('hl connected', { uid, locationId: conn.locationId })
      res.send(callbackPage(true, `Linked to ${locationName}.`, returnOrigin))
    } catch (err) {
      log.warn('oauth callback failed', sanitizeUpstreamError(err, '/oauth/token'))
      res
        .status(400)
        .send(
          callbackPage(
            false,
            'HighLevel did not accept the connection. Close this window and try again.',
            null,
          ),
        )
    }
  },
)

const emptySchema = z.looseObject({})

/** Disconnect: delete stored tokens entirely and flip the mirror. */
export const hlDisconnect = onRequest(
  { region: REGION, timeoutSeconds: 30, memory: '256MiB', maxInstances: 2 },
  async (req, res) => {
    if (applyCors(req, res)) return
    let uid: string | undefined
    try {
      if (req.method !== 'POST') throw new HttpError(405, 'method_not_allowed')
      ;({ uid } = await requireAuth(req))
      parseBody(req, emptySchema)
      await deleteConnection(uid)
      await db.doc(`users/${uid}`).update({
        hl: { status: 'disconnected' },
      })
      log.info('hl disconnected', { uid })
      res.json({ ok: true })
    } catch (err) {
      sendError(res, err, 'hlDisconnect', uid)
    }
  },
)
