import { createContext, useEffect, useState } from 'react';
import {
  onAuthStateChanged,
  signInAnonymously,
  signOut,
  GoogleAuthProvider,
  linkWithRedirect,
  getRedirectResult
} from 'firebase/auth';
import { auth } from '@/lib/firebase';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setCurrentUser(user);
      setLoading(false);
    });

    // Handle redirect result
    getRedirectResult(auth)
      .then((result) => {
        // If result is not null, the user has just come back from the redirect.
        // onAuthStateChanged will handle the user update.
        if (result) {
            console.log("Redirect result processed.");
        }
      })
      .catch((error) => {
        console.error("Error getting redirect result:", error);
      });

    return unsubscribe;
  }, []);

  const linkGoogleAccount = async () => {
    try {
      const provider = new GoogleAuthProvider();
      await linkWithRedirect(auth.currentUser, provider);
    } catch (error) {
      console.error("Error linking Google account:", error);
    }
  };

  const value = {
    currentUser,
    loading,
    linkGoogleAccount,
    signInAnonymously: () => signInAnonymously(auth),
    signOut: () => signOut(auth),
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
