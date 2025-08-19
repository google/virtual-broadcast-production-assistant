import { useEffect } from 'react';
import * as firebaseui from 'firebaseui';
import 'firebaseui/dist/firebaseui.css';
import { GoogleAuthProvider } from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { useAuth } from '@/contexts/useAuth';

export default function Auth() {
  const { isUpgrading, setIsUpgrading, signInAnonymously } = useAuth();

  useEffect(() => {
    if (isUpgrading) {
      const ui = firebaseui.auth.AuthUI.getInstance() || new firebaseui.auth.AuthUI(auth);
      ui.start('#firebaseui-auth-container', {
        signInOptions: [
          GoogleAuthProvider.PROVIDER_ID,
        ],
        callbacks: {
          signInSuccessWithAuthResult: function () {
            setIsUpgrading(false);
            return false;
          },
        },
      });
    } else {
        // If not upgrading, sign in anonymously
        signInAnonymously().catch(error => {
            console.error("Anonymous sign-in failed:", error);
        });
    }
  }, [isUpgrading, signInAnonymously, setIsUpgrading]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <div id="firebaseui-auth-container"></div>
    </div>
  );
}
