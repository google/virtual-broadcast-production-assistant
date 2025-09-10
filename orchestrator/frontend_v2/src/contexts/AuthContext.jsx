import { createContext, useEffect, useState } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { doc, getDoc } from 'firebase/firestore';
import { auth, db } from '@/lib/firebase';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthorised, setIsAuthorised] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        if (user.email) {
          const userRef = doc(db, "users", user.email);
          const userSnap = await getDoc(userRef);
          if (userSnap.exists()) {
            setCurrentUser(user);
            setIsAuthorised(true);
          } else {
            setCurrentUser(user);
            setIsAuthorised(false);
          }
        } else {
          // User exists but has no email. Treat as unauthorized.
          setCurrentUser(user);
          setIsAuthorised(false);
        }
      } else {
        // No user is signed in.
        setCurrentUser(null);
        setIsAuthorised(null);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const value = {
    currentUser,
    loading,
    isAuthorised,
    signOut: () => signOut(auth),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
