import { useEffect, type ReactNode } from 'react';
import { applyTheme, initialTheme } from '@/utils/theme';

export interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  useEffect(() => {
    applyTheme(initialTheme());
  }, []);

  return <>{children}</>;
}

export default ThemeProvider;
