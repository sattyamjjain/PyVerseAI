import { FUNCTIONS_BASE, idToken } from '@/lib/firebase'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly cid?: string,
    readonly retryAfter?: number,
  ) {
    super(message)
  }
}

/** POST JSON to a named Cloud Function at its direct URL. */
export async function callFn<T>(name: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const token = await idToken()
  let res: Response
  try {
    res = await fetch(`${FUNCTIONS_BASE}/${name}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body ?? {}),
      signal: signal ?? null,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'network', 'Network error. Check your connection.')
  }
  let data: Record<string, unknown> = {}
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text) as Record<string, unknown>
    } catch {
      data = { error: 'invalid_response' }
    }
  }
  if (!res.ok) {
    const code = typeof data.error === 'string' ? data.error : 'request_failed'
    throw new ApiError(
      res.status,
      code,
      friendlyApiMessage(res.status, code),
      typeof data.cid === 'string' ? data.cid : undefined,
      typeof data.retryAfter === 'number' ? data.retryAfter : undefined,
    )
  }
  return data as T
}

function friendlyApiMessage(status: number, code: string): string {
  switch (code) {
    case 'hl_not_connected':
      return 'HighLevel is not connected.'
    case 'rate_limited':
      return 'Rate limit reached. Wait a moment and try again.'
    case 'user_denied':
      return 'Request was denied.'
    case 'upstream_error':
      return 'HighLevel returned an error.'
    case 'network':
      return 'Network error. Check your connection.'
  }
  if (status === 401) return 'Your session expired. Sign in again.'
  if (status === 403) return 'You don’t have access to that.'
  if (status === 429) return 'Rate limit reached. Wait a moment and try again.'
  return 'Something went wrong. Please try again.'
}
