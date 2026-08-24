import { callFn } from '@/lib/api'

/**
 * HighLevel OAuth popup flow. Opens the chooselocation page in a popup; the
 * server-rendered callback page postMessages {type:'genesis:oauth', ok} back
 * and closes itself. Resolution also occurs if the user closes the popup.
 */
export async function connectHighLevel(): Promise<{ ok: boolean; reason?: string }> {
  const { url } = await callFn<{ url: string }>('hlAuthStart', {})
  const w = 520
  const h = 720
  const left = Math.max(0, (window.screen.width - w) / 2)
  const top = Math.max(0, (window.screen.height - h) / 2)
  const popup = window.open(
    url,
    'genesis-hl-oauth',
    `width=${w},height=${h},left=${left},top=${top},noopener=no`,
  )
  if (!popup) return { ok: false, reason: 'Popup was blocked. Allow popups and try again.' }

  return new Promise((resolve) => {
    let settled = false
    const settle = (result: { ok: boolean; reason?: string }) => {
      if (settled) return
      settled = true
      window.removeEventListener('message', onMessage)
      clearInterval(closePoll)
      resolve(result)
    }
    const onMessage = (event: MessageEvent) => {
      const data = event.data as { type?: string; ok?: boolean; reason?: string } | null
      if (!data || data.type !== 'genesis:oauth') return
      // The callback page is served from the functions origin; identify by
      // source + payload shape rather than pinning a functions hostname here.
      if (event.source !== popup) return
      settle({ ok: data.ok === true, reason: data.reason })
      popup.close()
    }
    const closePoll = setInterval(() => {
      if (popup.closed) settle({ ok: false, reason: 'Connection window was closed.' })
    }, 500)
    window.addEventListener('message', onMessage)
  })
}
