import { useEffect } from 'react';
import { useAuth } from '@/contexts/useAuth';

export default function NotAuthorised() {
  const { signOut } = useAuth();

  useEffect(() => {
    const timer = setTimeout(() => {
      signOut();
    }, 5000); // Sign out after 5 seconds

    return () => clearTimeout(timer);
  }, [signOut]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <h1>401 Not Authorised</h1>
      <p>You are not authorised to access this application. You will be signed out automatically in 5 seconds.</p>
    </div>
  );
}
