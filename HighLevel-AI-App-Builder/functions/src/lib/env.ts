import { defineSecret, defineString } from 'firebase-functions/params'

// Secrets — Cloud Secret Manager in prod (firebase functions:secrets:set …),
// functions/.secret.local for the emulator. Read via .value() at runtime only.
export const ANTHROPIC_API_KEY = defineSecret('ANTHROPIC_API_KEY')
export const HL_CLIENT_SECRET = defineSecret('HL_CLIENT_SECRET')

// Non-secret config — functions/.env (committed defaults are emulator-safe).
export const HL_CLIENT_ID = defineString('HL_CLIENT_ID', { default: '' })
export const HL_REDIRECT_URI = defineString('HL_REDIRECT_URI', { default: '' })
export const APP_ORIGINS = defineString('APP_ORIGINS', {
  default: 'http://localhost:5173,http://127.0.0.1:5173',
})
export const HL_MOCK_MODE = defineString('HL_MOCK_MODE', { default: 'false' })
// HighLevel webhook public keys (PEM, base64-encoded to survive env formats).
export const HL_WEBHOOK_PUBKEY_B64 = defineString('HL_WEBHOOK_PUBKEY_B64', { default: '' })

export function allowedOrigins(): string[] {
  return APP_ORIGINS.value()
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}

export function isMockMode(): boolean {
  return HL_MOCK_MODE.value() === 'true'
}

export const REGION = 'us-central1'
