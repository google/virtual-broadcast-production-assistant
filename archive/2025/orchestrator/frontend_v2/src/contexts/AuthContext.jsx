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
    console.log("AuthContext: Subscribing to onAuthStateChanged.");
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      console.log("AuthContext: onAuthStateChanged triggered.", { email: user?.email });
      try {
        if (user) {
          if (user.email) {
            console.log(`AuthContext: User found. Checking allow list for ${user.email}`);
            const userRef = doc(db, "users", user.email);
            const userSnap = await getDoc(userRef);
            
            if (userSnap.exists()) {
              console.log("AuthContext: User is in allow list. Setting as authorized.");
              setCurrentUser(user);
              setIsAuthorised(true);
            } else {
              console.log("AuthContext: User is NOT in allow list. Setting as unauthorized.");
              setCurrentUser(user);
              setIsAuthorised(false);
            }
          } else {
            console.log("AuthContext: User has no email. Setting as unauthorized.");
            setCurrentUser(user);
            setIsAuthorised(false);
          }
        } else {
          console.log("AuthContext: No user signed in.");
          setCurrentUser(null);
          setIsAuthorised(null);
        }
      } catch (error) {
        console.error("AuthContext: Authorization check failed:", error);
        // If there's an error, treat the user as unauthorized
        setCurrentUser(user);
        setIsAuthorised(false);
      } finally {
        console.log("AuthContext: Setting loading to false.");
        setLoading(false);
      }
    });

    return () => {
      console.log("AuthContext: Unsubscribing from onAuthStateChanged.");
      unsubscribe();
    };
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
