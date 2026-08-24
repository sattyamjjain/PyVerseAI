import { describe, expect, it } from 'vitest'
import { FirebaseError } from 'firebase/app'
import { authErrorMessage } from '@/lib/authErrors'

const GENERIC = 'Something went wrong. Please try again.'

function fb(code: string): FirebaseError {
  return new FirebaseError(code, `Firebase: Error (${code}).`)
}

describe('authErrorMessage', () => {
  it('collapses all credential-probe codes into one non-enumerating message', () => {
    // Distinguishing "wrong password" from "no such user" would let an attacker
    // enumerate accounts — all three must produce the identical message.
    const messages = ['auth/invalid-credential', 'auth/wrong-password', 'auth/user-not-found'].map(
      (code) => authErrorMessage(fb(code)),
    )
    expect(new Set(messages).size).toBe(1)
    expect(messages[0]).toBe('Incorrect email or password.')
  })

  it('maps known auth codes to actionable messages', () => {
    expect(authErrorMessage(fb('auth/email-already-in-use'))).toBe(
      'An account with this email already exists. Try signing in.',
    )
    expect(authErrorMessage(fb('auth/invalid-email'))).toBe('That email address doesn’t look valid.')
    expect(authErrorMessage(fb('auth/weak-password'))).toBe('Password must be at least 6 characters.')
    expect(authErrorMessage(fb('auth/too-many-requests'))).toBe(
      'Too many attempts. Wait a minute and try again.',
    )
    expect(authErrorMessage(fb('auth/network-request-failed'))).toBe(
      'Network error. Check your connection and try again.',
    )
  })

  it('falls back to a generic message for unmapped codes and non-Firebase values', () => {
    expect(authErrorMessage(fb('auth/popup-closed-by-user'))).toBe(GENERIC)
    expect(authErrorMessage(fb('firestore/permission-denied'))).toBe(GENERIC)
    expect(authErrorMessage(new Error('boom'))).toBe(GENERIC)
    expect(authErrorMessage('boom')).toBe(GENERIC)
    expect(authErrorMessage(undefined)).toBe(GENERIC)
    expect(authErrorMessage(null)).toBe(GENERIC)
  })
})
