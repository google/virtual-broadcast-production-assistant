import { createClient } from '@base44/sdk';
// import { getAccessToken } from '@base44/sdk/utils/auth-utils';

// Create a client with authentication required
export const base44 = createClient({
  appId: "6894fefa49f49a5e1841e98c", 
  requiresAuth: true // Ensure authentication is required for all operations
});
