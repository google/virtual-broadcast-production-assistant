import { useContext } from 'react';
import { RundownContext } from './RundownContext';

export function useRundown() {
  return useContext(RundownContext);
}
