import { onRequest } from 'firebase-functions/https'
import { z } from 'zod'
import { HL_CLIENT_SECRET, isMockMode, REGION } from './lib/env.js'
import { applyCors, HttpError, parseBody, requireAuth, sendError } from './lib/http.js'
import { checkRateLimit } from './lib/rateLimit.js'
import { log, sanitizeUpstreamError } from './lib/log.js'
import { getConnection, hlFetch } from './hl/client.js'
import { HL_API_BASE } from './shared/allowlist.js'

const SEED_CONTACTS = [
  { firstName: 'Priya', lastName: 'Sharma', email: 'priya.sharma@seedmail.dev', phone: '+15555100001', tags: ['lead', 'webinar'] },
  { firstName: 'Marcus', lastName: 'Webb', email: 'marcus.webb@seedmail.dev', phone: '+15555100002', tags: ['customer', 'vip'] },
  { firstName: 'Elena', lastName: 'Rodrigues', email: 'elena.rodrigues@seedmail.dev', phone: '+15555100003', tags: ['lead'] },
  { firstName: 'Tom', lastName: 'Akana', email: 'tom.akana@seedmail.dev', phone: '+15555100004', tags: ['customer'] },
  { firstName: 'Sofia', lastName: 'Marino', email: 'sofia.marino@seedmail.dev', phone: '+15555100005', tags: ['lead', 'referral'] },
  { firstName: 'David', lastName: 'Osei', email: 'david.osei@seedmail.dev', phone: '+15555100006', tags: ['cold'] },
  { firstName: 'Hana', lastName: 'Kim', email: 'hana.kim@seedmail.dev', phone: '+15555100007', tags: ['customer', 'onboarding'] },
  { firstName: 'Lucas', lastName: 'Ferreira', email: 'lucas.ferreira@seedmail.dev', phone: '+15555100008', tags: ['lead'] },
  { firstName: 'Amara', lastName: 'Diallo', email: 'amara.diallo@seedmail.dev', phone: '+15555100009', tags: ['vip'] },
  { firstName: 'Jonas', lastName: 'Berg', email: 'jonas.berg@seedmail.dev', phone: '+15555100010', tags: ['customer'] },
]

const INBOUND_SNIPPETS = [
  'Hi! Saw your ad — do you have any openings this week?',
  'Can you send over the pricing sheet when you get a chance?',
  'Thanks for the call earlier. Ready to move forward!',
  'Is the Thursday 3pm slot still available?',
  'Just filled out the form on your site — looking forward to hearing back.',
]

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/**
 * Populate the connected HighLevel sandbox location with demo data so the
 * generated apps have something real to show: contacts, inbound SMS threads
 * (sandboxes can't SEND, but /messages/inbound injects received messages),
 * and appointments on the first available calendar.
 */
export const seedSandbox = onRequest(
  { region: REGION, timeoutSeconds: 300, memory: '256MiB', maxInstances: 1, secrets: [HL_CLIENT_SECRET] },
  async (req, res) => {
    if (applyCors(req, res)) return
    let uid: string | undefined
    try {
      if (req.method !== 'POST') throw new HttpError(405, 'method_not_allowed')
      ;({ uid } = await requireAuth(req))
      await checkRateLimit(uid, [{ scope: 'seed_h', limit: 3, windowSec: 3600 }])
      parseBody(req, z.looseObject({}))

      const conn = await getConnection(uid)
      if (!conn || conn.status !== 'connected') throw new HttpError(403, 'hl_not_connected')

      if (isMockMode()) {
        res.json({
          ok: true,
          seeded: { contacts: 12, conversations: 6, appointments: 6 },
          notes: ['Mock mode: the simulated location already contains demo data.'],
        })
        return
      }

      const notes: string[] = []
      const url = (path: string) => new URL(path, HL_API_BASE)

      // Skip contact creation when the location already has data.
      const existing = await hlFetch(uid, 'GET', url(`/contacts/?locationId=${conn.locationId}&limit=1`))
      const existingCount = (existing.data as { count?: number }).count ?? 0

      const contactIds: string[] = []
      let contactsCreated = 0
      if (existingCount >= 10) {
        notes.push(`Location already has ${existingCount} contacts — skipped contact creation.`)
        const page = await hlFetch(uid, 'GET', url(`/contacts/?locationId=${conn.locationId}&limit=10`))
        for (const c of (page.data as { contacts?: Array<{ id: string }> }).contacts ?? []) {
          contactIds.push(c.id)
        }
      } else {
        for (const seed of SEED_CONTACTS) {
          try {
            const created = await hlFetch(uid, 'POST', url('/contacts/'), {
              ...seed,
              locationId: conn.locationId,
              source: 'genesis seed',
            })
            const id = (created.data as { contact?: { id?: string } }).contact?.id
            if (id) {
              contactIds.push(id)
              contactsCreated++
            }
            await sleep(150)
          } catch (err) {
            log.warn('seed contact failed', sanitizeUpstreamError(err, '/contacts/'))
          }
        }
      }

      // Inbound message threads (received messages work in sandboxes).
      let conversationsSeeded = 0
      for (let i = 0; i < Math.min(INBOUND_SNIPPETS.length, contactIds.length); i++) {
        try {
          await hlFetch(uid, 'POST', url('/conversations/messages/inbound'), {
            type: 'SMS',
            contactId: contactIds[i],
            message: INBOUND_SNIPPETS[i],
          })
          conversationsSeeded++
          await sleep(150)
        } catch (err) {
          log.warn('seed inbound message failed', sanitizeUpstreamError(err, '/conversations/messages/inbound'))
        }
      }
      if (conversationsSeeded === 0 && contactIds.length > 0) {
        notes.push('Could not inject inbound messages — check conversations/message.write scope.')
      }

      // Appointments need an existing calendar (create one in the HL UI once)
      // AND an assigned team member — HighLevel 422s without assignedUserId.
      let appointmentsCreated = 0
      const calendars = await hlFetch(uid, 'GET', url(`/calendars/?locationId=${conn.locationId}`))
      const calendarList = (calendars.data as { calendars?: Array<{ id: string; isActive?: boolean }> }).calendars ?? []
      const calendar = calendarList.find((c) => c.isActive !== false) ?? calendarList[0]

      let assignedUserId: string | undefined
      try {
        const users = await hlFetch(uid, 'GET', url(`/users/?locationId=${conn.locationId}`))
        assignedUserId = ((users.data as { users?: Array<{ id?: string }> }).users ?? []).find(
          (u) => u.id,
        )?.id
      } catch (err) {
        log.warn('seed users lookup failed', sanitizeUpstreamError(err, '/users/'))
      }

      if (!calendar) {
        notes.push('No calendar found — create one calendar in HighLevel (Settings → Calendars), then seed again for appointments.')
      } else if (!assignedUserId) {
        notes.push('No team member found on the location — appointments need an assigned user; check the users.readonly scope.')
      } else {
        for (let i = 0; i < Math.min(4, contactIds.length); i++) {
          try {
            const start = new Date(Date.now() + (i + 1) * 26 * 3_600_000)
            start.setMinutes(0, 0, 0)
            await hlFetch(uid, 'POST', url('/calendars/events/appointments'), {
              calendarId: calendar.id,
              locationId: conn.locationId,
              contactId: contactIds[i],
              assignedUserId,
              startTime: start.toISOString(),
              title: ['Discovery call', 'Onboarding session', 'Proposal review', 'Strategy check-in'][i],
              appointmentStatus: 'confirmed',
              ignoreFreeSlotValidation: true,
              toNotify: false,
            })
            appointmentsCreated++
            await sleep(200)
          } catch (err) {
            log.warn('seed appointment failed', sanitizeUpstreamError(err, '/calendars/events/appointments'))
          }
        }
        if (appointmentsCreated === 0) {
          notes.push('Appointments could not be created — verify calendars/events.write scope and calendar setup.')
        }
      }

      log.info('sandbox seeded', { uid, contactsCreated, conversationsSeeded, appointmentsCreated })
      res.json({
        ok: true,
        seeded: {
          contacts: contactsCreated,
          conversations: conversationsSeeded,
          appointments: appointmentsCreated,
        },
        ...(notes.length ? { notes } : {}),
      })
    } catch (err) {
      sendError(res, err, 'seedSandbox', uid)
    }
  },
)
