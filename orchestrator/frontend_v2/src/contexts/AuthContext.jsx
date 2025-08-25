import { createContext, useEffect, useState } from 'react';
import { onAuthStateChanged, signInAnonymously, signOut, GoogleAuthProvider, linkWithPopup } from 'firebase/auth';
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

    return unsubscribe;
  }, []);

  const linkGoogleAccount = async () => {
    try {
      const provider = new GoogleAuthProvider();
      await linkWithPopup(auth.currentUser, provider);
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
