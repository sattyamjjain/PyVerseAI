import { FirebaseError } from 'firebase/app'

/** Friendly, non-enumerating messages for Firebase Auth failures. */
export function authErrorMessage(err: unknown): string {
  if (err instanceof FirebaseError) {
    switch (err.code) {
      case 'auth/invalid-credential':
      case 'auth/wrong-password':
      case 'auth/user-not-found':
        return 'Incorrect email or password.'
      case 'auth/email-already-in-use':
        return 'An account with this email already exists. Try signing in.'
      case 'auth/invalid-email':
        return 'That email address doesn’t look valid.'
      case 'auth/weak-password':
        return 'Password must be at least 6 characters.'
      case 'auth/too-many-requests':
        return 'Too many attempts. Wait a minute and try again.'
      case 'auth/network-request-failed':
        return 'Network error. Check your connection and try again.'
      default:
        return 'Something went wrong. Please try again.'
    }
  }
  return 'Something went wrong. Please try again.'
}
