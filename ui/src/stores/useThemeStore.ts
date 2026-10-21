import { useSyncExternalStore } from 'react';
import { applyTheme, initialTheme, type Theme } from '@/utils/theme';

let currentTheme: Theme = initialTheme();
const listeners = new Set<() => void>();

function setThemeState(next: Theme) {
  currentTheme = next;
  applyTheme(next);
  listeners.forEach((listener) => listener());
}

export function useThemeStore() {
  const theme = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => currentTheme,
    () => 'light' as Theme,
  );

  return {
    theme,
    setTheme: setThemeState,
    toggleTheme: () => setThemeState(currentTheme === 'dark' ? 'light' : 'dark'),
  };
}
