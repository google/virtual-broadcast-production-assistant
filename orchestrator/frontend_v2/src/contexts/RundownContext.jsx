import { createContext, useContext, useEffect, useState } from 'react';
import { doc, getDoc, setDoc } from 'firebase/firestore';
import { useAuth } from './AuthContext';
import { useSocket } from './SocketContext';
import { db } from '@/lib/firebase';

const RundownContext = createContext();

export function useRundown() {
  return useContext(RundownContext);
}

export function RundownProvider({ children }) {
  const { currentUser } = useAuth();
  const { reconnect } = useSocket();
  const [rundownSystem, setRundownSystem] = useState('cuez');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentUser) {
      setLoading(false);
      return;
    }

    const userDocRef = doc(db, 'user_preferences', currentUser.uid);
    const getRundownSystem = async () => {
      setLoading(true);
      try {
        const docSnap = await getDoc(userDocRef);
        if (docSnap.exists()) {
          setRundownSystem(docSnap.data().rundown_system || 'cuez');
        } else {
          // If no preference exists, set the default in Firestore
          await setDoc(userDocRef, { rundown_system: 'cuez' });
          setRundownSystem('cuez');
        }
      } catch (error) {
        console.error('Error getting rundown system preference:', error);
        setRundownSystem('cuez'); // Default on error
      } finally {
        setLoading(false);
      }
    };

    getRundownSystem();
  }, [currentUser]);

  const updateRundownSystem = async (system) => {
    if (!currentUser) return;
    setRundownSystem(system);
    const userDocRef = doc(db, 'user_preferences', currentUser.uid);
    try {
      await setDoc(userDocRef, { rundown_system: system }, { merge: true });
      if (reconnect) {
        reconnect();
      }
    } catch (error) {
      console.error('Error setting rundown system preference:', error);
    }
  };

  const value = {
    rundownSystem,
    updateRundownSystem,
    loading,
  };

  return (
    <RundownContext.Provider value={value}>
      {children}
    </RundownContext.Provider>
  );
}
