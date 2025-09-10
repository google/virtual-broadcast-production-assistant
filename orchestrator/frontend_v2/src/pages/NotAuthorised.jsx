import { useAuth } from '@/contexts/useAuth';
import { Button } from '@/components/ui/button';

export default function NotAuthorised() {
  const { signOut } = useAuth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <h1>401 Not Authorised</h1>
      <p>You are not authorised to access this application.</p>
      <Button onClick={signOut}>Sign Out</Button>
    </div>
  );
}
