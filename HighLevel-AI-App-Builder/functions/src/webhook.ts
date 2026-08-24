import { onRequest } from 'firebase-functions/https'
import { createPublicKey, createVerify, verify as cryptoVerify } from 'node:crypto'
import { db, FieldValue, Timestamp } from './lib/db.js'
import { HL_WEBHOOK_PUBKEY_B64, HL_WEBHOOK_RSA_PUBKEY_B64, REGION } from './lib/env.js'
import { log, truncate } from './lib/log.js'

/** Webhook events we surface to the workspace + preview SDK. */
const EVENT_MAP: Record<string, { sdkEvent: string; summarize: (p: Record<string, unknown>) => string }> = {
  ContactCreate: {
    sdkEvent: 'contactCreated',
    summarize: (p) => `New contact: ${name(p)}`,
  },
  ContactUpdate: {
    sdkEvent: 'contactUpdated',
    summarize: (p) => `Contact updated: ${name(p)}`,
  },
  ContactDelete: {
    sdkEvent: 'contactDeleted',
    summarize: (p) => `Contact deleted: ${name(p)}`,
  },
  InboundMessage: {
    sdkEvent: 'inboundMessage',
    summarize: (p) => `New message: ${truncate(String(p.body ?? ''), 60)}`,
  },
  AppointmentCreate: {
    sdkEvent: 'appointmentCreated',
    summarize: (p) => `Appointment booked: ${truncate(String(title(p)), 60)}`,
  },
  AppointmentUpdate: {
    sdkEvent: 'appointmentUpdated',
    summarize: (p) => `Appointment updated: ${truncate(String(title(p)), 60)}`,
  },
}

function name(p: Record<string, unknown>): string {
  const full = [p.firstName, p.lastName].filter(Boolean).join(' ')
  return full || String(p.email ?? p.id ?? 'unknown')
}
function title(p: Record<string, unknown>): unknown {
  const appt = p.appointment as Record<string, unknown> | undefined
  return appt?.title ?? p.title ?? 'appointment'
}

function verifyEd25519(rawBody: Buffer, signatureB64: string): boolean {
  const pem = Buffer.from(HL_WEBHOOK_PUBKEY_B64.value(), 'base64').toString('utf8')
  if (!pem.includes('BEGIN PUBLIC KEY')) return false
  try {
    const key = createPublicKey(pem)
    return cryptoVerify(null, rawBody, key, Buffer.from(signatureB64, 'base64'))
  } catch {
    return false
  }
}

function verifyRsa(rawBody: Buffer, signatureB64: string): boolean {
  const pem = Buffer.from(HL_WEBHOOK_RSA_PUBKEY_B64.value(), 'base64').toString('utf8')
  if (!pem.includes('BEGIN PUBLIC KEY')) return false
  try {
    const verifier = createVerify('SHA256')
    verifier.update(rawBody)
    verifier.end()
    return verifier.verify(pem, Buffer.from(signatureB64, 'base64'))
  } catch {
    return false
  }
}

/**
 * HighLevel webhook receiver. Registered in the marketplace app's Webhooks
 * settings. Verifies x-ghl-signature (Ed25519) when a public key is
 * configured, dedupes on webhookId, fans events out to hl_events docs the
 * workspace listens to, and purges tokens on UNINSTALL. Always answers fast.
 */
export const hlWebhook = onRequest(
  { region: REGION, timeoutSeconds: 30, memory: '256MiB', maxInstances: 3 },
  async (req, res) => {
    try {
      if (req.method !== 'POST') {
        res.status(405).send('method not allowed')
        return
      }
      // Prefer the current Ed25519 header; fall back to the legacy RSA one
      // (HighLevel sends both during the transition period).
      const ghlSig = req.headers['x-ghl-signature']
      const whSig = req.headers['x-wh-signature']
      const edConfigured = HL_WEBHOOK_PUBKEY_B64.value().length > 0
      const rsaConfigured = HL_WEBHOOK_RSA_PUBKEY_B64.value().length > 0
      if (edConfigured || rsaConfigured) {
        const ok =
          (edConfigured && typeof ghlSig === 'string' && verifyEd25519(req.rawBody, ghlSig)) ||
          (rsaConfigured && typeof whSig === 'string' && verifyRsa(req.rawBody, whSig))
        if (!ok) {
          log.warn('webhook signature rejected', {
            hasGhl: typeof ghlSig === 'string',
            hasWh: typeof whSig === 'string',
          })
          res.status(401).send('bad signature')
          return
        }
      } else {
        log.warn('webhook accepted WITHOUT signature verification (no public keys configured)')
      }

      const payload = (req.body ?? {}) as Record<string, unknown>
      const type = String(payload.type ?? '')
      const locationId = String(payload.locationId ?? '')
      const webhookId = String(payload.webhookId ?? '')

      // Dedupe (HighLevel retries any non-2xx up to 12 times).
      if (webhookId) {
        try {
          await db.doc(`webhook_dedupe/${webhookId}`).create({
            expireAt: Timestamp.fromMillis(Date.now() + 24 * 3_600_000),
          })
        } catch {
          res.status(200).send('duplicate')
          return
        }
      }

      if (type === 'UNINSTALL') {
        if (locationId) {
          const conns = await db
            .collection('hl_connections')
            .where('locationId', '==', locationId)
            .get()
          for (const doc of conns.docs) {
            await doc.ref.delete()
            await db.doc(`users/${doc.id}`).update({ hl: { status: 'disconnected' } }).catch(() => {})
          }
          log.info('uninstall processed', { locationId, connections: conns.size })
        }
        res.status(200).send('ok')
        return
      }

      const mapping = EVENT_MAP[type]
      if (mapping && locationId) {
        const conns = await db
          .collection('hl_connections')
          .where('locationId', '==', locationId)
          .get()
        for (const doc of conns.docs) {
          await db.collection('hl_events').add({
            ownerUid: doc.id,
            locationId,
            // Raw HL event name — the SPA maps it to SDK event names itself.
            type,
            summary: mapping.summarize(payload),
            payload: JSON.parse(truncate(JSON.stringify(payload), 10_000).replace(/…$/, '') || '{}'),
            createdAt: FieldValue.serverTimestamp(),
            expireAt: Timestamp.fromMillis(Date.now() + 7 * 86_400_000),
          })
        }
      }
      res.status(200).send('ok')
    } catch (err) {
      log.error('webhook handler failed', { err: err instanceof Error ? err.message : String(err) })
      // 200 anyway — never trigger HighLevel's 12-retry storm for our own bugs.
      res.status(200).send('ok')
    }
  },
)
