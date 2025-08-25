import { useEffect } from 'react';
import * as firebaseui from 'firebaseui';
import 'firebaseui/dist/firebaseui.css';
import { GoogleAuthProvider } from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { useAuth } from '@/contexts/useAuth';

export default function Auth() {
  const { signInAnonymously } = useAuth();

  useEffect(() => {
    signInAnonymously().catch(error => {
        console.error("Anonymous sign-in failed:", error);
    });
  }, [signInAnonymously]);

  // Render a loading indicator or null while sign-in happens
  return <div>Loading...</div>;
}
