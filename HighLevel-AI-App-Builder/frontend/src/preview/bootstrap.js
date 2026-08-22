/*
 * Genesis preview bootstrap — injected as the FIRST script of every srcdoc
 * preview. Runs inside a sandboxed (opaque-origin) iframe with CSP
 * connect-src 'none': the postMessage bridge to the parent is the ONLY data
 * path. Implements the `genesis` SDK documented in functions/src/shared/
 * sdk-api.ts — keep the two in lockstep.
 *
 * "__GENESIS_PARENT_ORIGIN__" is replaced at assembly time.
 */
;(function () {
  'use strict'
  var PARENT_ORIGIN = '__GENESIS_PARENT_ORIGIN__'
  var V = 1

  // ── storage shims (opaque origins throw on localStorage access) ───────────
  function memoryStorage() {
    var m = new Map()
    return {
      get length() {
        return m.size
      },
      key: function (i) {
        return Array.from(m.keys())[i] || null
      },
      getItem: function (k) {
        return m.has(String(k)) ? m.get(String(k)) : null
      },
      setItem: function (k, v) {
        m.set(String(k), String(v))
      },
      removeItem: function (k) {
        m.delete(String(k))
      },
      clear: function () {
        m.clear()
      },
    }
  }
  try {
    Object.defineProperty(window, 'localStorage', { value: memoryStorage(), configurable: true })
    Object.defineProperty(window, 'sessionStorage', { value: memoryStorage(), configurable: true })
  } catch (e) {
    /* best effort */
  }

  // ── console + error forwarding ────────────────────────────────────────────
  function serialize(arg) {
    try {
      if (typeof arg === 'string') return arg.slice(0, 2048)
      if (arg instanceof Error) return String(arg.stack || arg.message).slice(0, 2048)
      var seen = new WeakSet()
      var s = JSON.stringify(
        arg,
        function (_k, v) {
          if (typeof v === 'object' && v !== null) {
            if (seen.has(v)) return '[circular]'
            seen.add(v)
          }
          if (typeof v === 'function') return '[function]'
          return v
        },
        1,
      )
      return String(s).slice(0, 2048)
    } catch (e) {
      try {
        return String(arg).slice(0, 2048)
      } catch (e2) {
        return '[unserializable]'
      }
    }
  }
  function post(msg) {
    try {
      window.parent.postMessage(msg, PARENT_ORIGIN)
    } catch (e) {
      /* parent gone */
    }
  }
  ;['log', 'info', 'warn', 'error'].forEach(function (level) {
    var original = console[level].bind(console)
    console[level] = function () {
      original.apply(null, arguments)
      post({
        v: V,
        type: 'preview.console',
        level: level,
        args: Array.prototype.slice.call(arguments, 0, 8).map(serialize),
      })
    }
  })
  window.addEventListener('error', function (e) {
    post({
      v: V,
      type: 'preview.error',
      message: String(e.message || 'Script error'),
      source: e.filename ? String(e.filename) : undefined,
      line: typeof e.lineno === 'number' ? e.lineno : undefined,
      col: typeof e.colno === 'number' ? e.colno : undefined,
      stack: e.error && e.error.stack ? String(e.error.stack).slice(0, 4096) : undefined,
    })
  })
  window.addEventListener('unhandledrejection', function (e) {
    var r = e.reason
    post({
      v: V,
      type: 'preview.error',
      message: 'Unhandled promise rejection: ' + (r && r.message ? r.message : serialize(r)),
      stack: r && r.stack ? String(r.stack).slice(0, 4096) : undefined,
    })
  })

  // ── bridge RPC ────────────────────────────────────────────────────────────
  var pending = new Map()
  var listeners = new Map()
  var seq = 0
  function makeId() {
    try {
      return crypto.randomUUID()
    } catch (e) {
      return 'req-' + Date.now() + '-' + seq++
    }
  }
  window.addEventListener('message', function (event) {
    if (event.source !== window.parent) return
    if (event.origin !== PARENT_ORIGIN) return
    var msg = event.data
    if (!msg || msg.v !== V) return
    if (msg.type === 'hl.response' && typeof msg.id === 'string') {
      var entry = pending.get(msg.id)
      if (!entry) return
      pending.delete(msg.id)
      clearTimeout(entry.timer)
      if (msg.ok) entry.resolve(msg.data)
      else {
        var err = new Error(msg.error || 'Request failed')
        err.status = msg.status
        entry.reject(err)
      }
    } else if (msg.type === 'hl.event' && typeof msg.event === 'string') {
      var cbs = listeners.get(msg.event)
      if (cbs)
        cbs.forEach(function (cb) {
          try {
            cb(msg.payload || {})
          } catch (e) {
            console.error(e)
          }
        })
    }
  })

  function request(method, path, params, body) {
    return new Promise(function (resolve, reject) {
      var id = makeId()
      var timer = setTimeout(function () {
        pending.delete(id)
        reject(new Error('Request timed out'))
      }, 15000)
      pending.set(id, { resolve: resolve, reject: reject, timer: timer })
      post({
        v: V,
        type: 'hl.request',
        id: id,
        method: method,
        path: path,
        params: params || undefined,
        body: body || undefined,
      })
    })
  }
  function enc(s) {
    return encodeURIComponent(String(s))
  }

  // ── the genesis SDK (mirror of shared/sdk-api.ts) ─────────────────────────
  window.genesis = {
    contacts: {
      list: function (opts) {
        return request('GET', '/contacts/', opts)
      },
      search: function (body) {
        return request('POST', '/contacts/search', undefined, body || {})
      },
      get: function (contactId) {
        return request('GET', '/contacts/' + enc(contactId))
      },
      create: function (data) {
        return request('POST', '/contacts/', undefined, data || {})
      },
      update: function (contactId, data) {
        return request('PUT', '/contacts/' + enc(contactId), undefined, data || {})
      },
    },
    conversations: {
      list: function (opts) {
        return request('GET', '/conversations/search', opts)
      },
      get: function (conversationId) {
        return request('GET', '/conversations/' + enc(conversationId))
      },
      messages: function (conversationId, opts) {
        return request('GET', '/conversations/' + enc(conversationId) + '/messages', opts)
      },
      send: function (data) {
        return request('POST', '/conversations/messages', undefined, data || {})
      },
    },
    calendars: {
      list: function (opts) {
        return request('GET', '/calendars/', opts)
      },
      events: function (opts) {
        return request('GET', '/calendars/events', opts)
      },
      appointment: function (eventId) {
        return request('GET', '/calendars/events/appointments/' + enc(eventId))
      },
      freeSlots: function (calendarId, opts) {
        return request('GET', '/calendars/' + enc(calendarId) + '/free-slots', opts)
      },
      book: function (data) {
        return request('POST', '/calendars/events/appointments', undefined, data || {})
      },
    },
    location: {
      get: function () {
        return request('GET', '/locations/me')
      },
    },
    on: function (event, cb) {
      if (!listeners.has(event)) listeners.set(event, new Set())
      listeners.get(event).add(cb)
      return function () {
        genesis.off(event, cb)
      }
    },
    off: function (event, cb) {
      var cbs = listeners.get(event)
      if (cbs) cbs.delete(cb)
    },
  }

  // ── ready signal ──────────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      post({ v: V, type: 'preview.ready' })
    })
  } else {
    post({ v: V, type: 'preview.ready' })
  }
})()
