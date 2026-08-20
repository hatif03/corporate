import { onAuthStateChanged, signInWithPopup, signOut, type User } from 'firebase/auth'
import { auth, googleProvider } from './firebase'

export function watchAuthState(onChange: (user: User | null) => void): () => void {
  return onAuthStateChanged(auth, onChange)
}

export function signInWithGoogle(): Promise<unknown> {
  return signInWithPopup(auth, googleProvider)
}

export function signOutUser(): Promise<void> {
  return signOut(auth)
}

export async function getIdToken(): Promise<string | null> {
  const user = auth.currentUser
  if (!user) return null
  return user.getIdToken()
}
