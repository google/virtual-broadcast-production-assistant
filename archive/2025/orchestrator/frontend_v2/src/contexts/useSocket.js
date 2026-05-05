import { useContext } from 'react';
import { SocketContext } from './SocketContext';

export function useSocket() {
  return useContext(SocketContext);
}
