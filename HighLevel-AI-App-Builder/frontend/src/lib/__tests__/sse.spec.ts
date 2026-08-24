// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { StreamCallbacks } from '@/lib/sse'
import type { SseEvent } from '@shared/protocol'

vi.mock('@/lib/firebase', () => ({
  FUNCTIONS_BASE: 'http://functions.test',
  idToken: vi.fn<() => Promise<string>>(async () => 'test-token'),
}))

import { streamGeneration } from '@/lib/sse'

const encoder = new TextEncoder()

function recorder() {
  const events: SseEvent[] = []
  const transportErrors: Error[] = []
  const closes: boolean[] = []
  const cb: StreamCallbacks = {
    onEvent: (e) => void events.push(e),
    onTransportError: (e) => void transportErrors.push(e),
    onClose: (sawTerminal) => void closes.push(sawTerminal),
  }
  return { events, transportErrors, closes, cb }
}

/** Mock fetch: a 200 response whose body streams `chunks` and then closes. */
function stubFetchWithChunks(chunks: string[]) {
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
        controller.close()
      },
    })
    return { ok: true, status: 200, body, json: async () => ({}) } as unknown as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/**
 * Mock fetch: a 200 response that stays open until `end()`. Mirrors real fetch
 * abort semantics: aborting the request signal errors the body stream.
 */
function stubFetchOpenStream() {
  let controller!: ReadableStreamDefaultController<Uint8Array>
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c
    },
  })
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async (_url, init) => {
    init?.signal?.addEventListener('abort', () => {
      try {
        controller.error(init.signal?.reason ?? new DOMException('aborted', 'AbortError'))
      } catch {
        /* stream already closed */
      }
    })
    return { ok: true, status: 200, body, json: async () => ({}) } as unknown as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  return {
    push: (s: string) => controller.enqueue(encoder.encode(s)),
    end: () => controller.close(),
  }
}

const doneFrame = 'event: done\ndata: {"stopReason":"end_turn","filesWritten":[]}\n\n'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('streamGeneration', () => {
  it('POSTs to the direct function URL with auth headers and delivers typed events', async () => {
    const fetchMock = stubFetchWithChunks([
      'id: 1\nevent: generation_start\ndata: {"generationId":"g1","mode":"create","model":"m1"}\n\n',
      doneFrame,
    ])
    const rec = recorder()

    await streamGeneration({ projectId: 'p1', prompt: 'hi', model: 'fast' }, rec.cb).finished

    expect(fetchMock).toHaveBeenCalledWith(
      'http://functions.test/generate',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
          Accept: 'text/event-stream',
        }),
        body: JSON.stringify({ projectId: 'p1', prompt: 'hi', model: 'fast' }),
      }),
    )
    // The `type` discriminant comes from the SSE `event:` field, merged over the JSON data.
    expect(rec.events).toEqual([
      { type: 'generation_start', generationId: 'g1', mode: 'create', model: 'm1' },
      { type: 'done', stopReason: 'end_turn', filesWritten: [] },
    ])
    expect(rec.transportErrors).toEqual([])
  })

  it('reassembles frames split across arbitrary chunk boundaries', async () => {
    const stream =
      'event: narration_delta\ndata: {"text":"building"}\n\n' +
      'event: file_start\ndata: {"path":"app.js","index":0,"action":"create"}\n\n' +
      doneFrame
    // Feed the stream 7 bytes at a time, cutting mid-field and mid-JSON.
    const chunks: string[] = []
    for (let i = 0; i < stream.length; i += 7) chunks.push(stream.slice(i, i + 7))
    stubFetchWithChunks(chunks)
    const rec = recorder()

    await streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, rec.cb).finished

    expect(rec.events.map((e) => e.type)).toEqual(['narration_delta', 'file_start', 'done'])
    expect(rec.events[0]).toMatchObject({ text: 'building' })
  })

  it('joins multi-line data fields per the SSE spec before JSON parsing', async () => {
    // Two data: lines join with "\n" — the JSON payload itself spans lines.
    stubFetchWithChunks([
      'event: narration_delta\ndata: {"text":\ndata: "hello"}\n\n',
      doneFrame,
    ])
    const rec = recorder()

    await streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, rec.cb).finished

    expect(rec.events[0]).toEqual({ type: 'narration_delta', text: 'hello' })
  })

  it('survives junk frames: comments, event-less data, and malformed JSON are skipped', async () => {
    stubFetchWithChunks([
      ': ping\n\n', // heartbeat comment
      'data: {"orphan":true}\n\n', // frame with no event: field
      'event: narration_delta\ndata: {not json\n\n', // malformed JSON payload
      'event: narration_delta\ndata: {"text":"still alive"}\n\n',
      doneFrame,
    ])
    const rec = recorder()

    await streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, rec.cb).finished

    expect(rec.events).toEqual([
      { type: 'narration_delta', text: 'still alive' },
      { type: 'done', stopReason: 'end_turn', filesWritten: [] },
    ])
    expect(rec.transportErrors).toEqual([])
    expect(rec.closes).toEqual([true])
  })

  it('onClose reports whether a terminal event was seen', async () => {
    // Terminal `done`: frames after it are never delivered (connection is closed).
    stubFetchWithChunks([doneFrame, 'event: narration_delta\ndata: {"text":"late"}\n\n'])
    const terminal = recorder()
    await streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, terminal.cb).finished
    expect(terminal.events.map((e) => e.type)).toEqual(['done'])
    expect(terminal.closes).toEqual([true])

    // Server closes without a terminal event: clean close, sawTerminal=false, no error.
    stubFetchWithChunks(['event: narration_delta\ndata: {"text":"partial"}\n\n'])
    const dropped = recorder()
    await streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, dropped.cb).finished
    expect(dropped.events.map((e) => e.type)).toEqual(['narration_delta'])
    expect(dropped.closes).toEqual([false])
    expect(dropped.transportErrors).toEqual([])
  })

  it('surfaces HTTP failures as transport errors, preferring the server error code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<() => Promise<Response>>(
        async () =>
          ({
            ok: false,
            status: 429,
            body: null,
            json: async () => ({ error: 'rate_limited' }),
          }) as unknown as Response,
      ),
    )
    const coded = recorder()
    await streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, coded.cb).finished
    expect(coded.transportErrors.map((e) => e.message)).toEqual(['rate_limited'])
    expect(coded.closes).toEqual([false])

    vi.stubGlobal(
      'fetch',
      vi.fn<() => Promise<Response>>(
        async () =>
          ({
            ok: false,
            status: 500,
            body: null,
            json: async () => {
              throw new Error('not json')
            },
          }) as unknown as Response,
      ),
    )
    const plain = recorder()
    await streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, plain.cb).finished
    expect(plain.transportErrors.map((e) => e.message)).toEqual(['HTTP 500'])
  })

  it('cancel() closes the stream without reporting a transport error', async () => {
    const server = stubFetchOpenStream()
    const rec = recorder()
    const handle = streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, rec.cb)

    await vi.waitFor(() => expect(rec.events).toHaveLength(0)) // connection established
    server.push('event: narration_delta\ndata: {"text":"partial"}\n\n')
    await vi.waitFor(() => expect(rec.events).toHaveLength(1))

    handle.cancel()
    await handle.finished

    expect(rec.transportErrors).toEqual([])
    expect(rec.closes).toEqual([false])
  })

  it('aborts with a stall error after 30s of total silence', async () => {
    vi.useFakeTimers()
    stubFetchOpenStream()
    const rec = recorder()
    const handle = streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, rec.cb)

    await vi.advanceTimersByTimeAsync(29_999)
    expect(rec.transportErrors).toEqual([])

    await vi.advanceTimersByTimeAsync(1)
    await handle.finished

    expect(rec.transportErrors.map((e) => e.message)).toEqual([
      'Connection stalled. No data for 30 seconds.',
    ])
    expect(rec.closes).toEqual([false])
  })

  it('heartbeat comments reset the stall watchdog even though the parser swallows them', async () => {
    vi.useFakeTimers()
    const server = stubFetchOpenStream()
    const rec = recorder()
    const handle = streamGeneration({ projectId: 'p1', prompt: 'x', model: 'fast' }, rec.cb)
    await vi.advanceTimersByTimeAsync(0) // connect; watchdog armed at t=0

    // Heartbeats at t=20s and t=40s keep a silent stream alive well past 30s.
    await vi.advanceTimersByTimeAsync(20_000)
    server.push(': ping\n\n')
    await vi.advanceTimersByTimeAsync(20_000) // t=40s — would have stalled at t=30s without the ping
    expect(rec.transportErrors).toEqual([])
    server.push(': ping\n\n')
    await vi.advanceTimersByTimeAsync(25_000) // t=65s, last heartbeat t=40s
    expect(rec.transportErrors).toEqual([])

    // Silence from t=40s finally exceeds the 30s budget.
    await vi.advanceTimersByTimeAsync(5_001)
    await handle.finished
    expect(rec.transportErrors.map((e) => e.message)).toEqual([
      'Connection stalled. No data for 30 seconds.',
    ])
    expect(rec.events).toEqual([]) // comments never surface as events
  })
})
