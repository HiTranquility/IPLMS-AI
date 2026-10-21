import { useSyncExternalStore } from 'react';
import type { WorkspacePersona } from '@/types/workspace';

const STORAGE_KEY = 'iplms_active_workspace';

function getInitialPersona(): WorkspacePersona {
  if (typeof window === 'undefined') return 'all';
  const saved = localStorage.getItem(STORAGE_KEY) as WorkspacePersona | null;
  if (saved && ['all', 'admin', 'ml', 'labeling', 'analytics'].includes(saved)) {
    return saved;
  }
  return 'all';
}

let activePersona: WorkspacePersona = getInitialPersona();
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((listener) => listener());
}

export function setPersona(next: WorkspacePersona) {
  activePersona = next;
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, next);
  }
  notify();
}

export function useWorkspaceStore() {
  const persona = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => activePersona,
    () => 'all' as WorkspacePersona,
  );

  return {
    persona,
    setPersona,
  };
}
