import { getApps, initializeApp } from 'firebase-admin/app'
import { FieldValue, getFirestore, Timestamp } from 'firebase-admin/firestore'
import { getAuth } from 'firebase-admin/auth'

if (getApps().length === 0) initializeApp()

export const db = getFirestore()
export const adminAuth = getAuth()
export { FieldValue, Timestamp }
