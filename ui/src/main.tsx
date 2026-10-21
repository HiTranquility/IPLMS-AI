import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { I18nProvider, QueryProvider, ThemeProvider } from './providers';
import { applyLang, initialLang } from './utils/lang';
import { applyTheme, initialTheme } from './utils/theme';
import './index.css';

applyTheme(initialTheme());
applyLang(initialLang());

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryProvider>
      <ThemeProvider>
        <I18nProvider>
          <BrowserRouter basename="/console">
            <App />
          </BrowserRouter>
        </I18nProvider>
      </ThemeProvider>
    </QueryProvider>
  </StrictMode>,
);
