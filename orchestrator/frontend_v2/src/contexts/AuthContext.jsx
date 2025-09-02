import { createContext, useEffect, useState } from 'react';
import { onAuthStateChanged, signInAnonymously, signOut } from 'firebase/auth';
import { auth } from '@/lib/firebase';

export const AuthContext = createContext();



export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isUpgrading, setIsUpgrading] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        // User is signed in.
        setCurrentUser(user);
        setLoading(false);
      } else {
        // User is signed out.
        // Try to sign in anonymously.
        signInAnonymously(auth).catch((error) => {
          console.error('Anonymous sign-in failed:', error);
          // Still set loading to false so the app doesn't hang.
          setLoading(false);
        });
      }
    });

    return unsubscribe;
  }, []);

  const value = {
    currentUser,
    loading,
    isUpgrading,
    setIsUpgrading,
    signInAnonymously: () => signInAnonymously(auth),
    signOut: () => signOut(auth),
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
