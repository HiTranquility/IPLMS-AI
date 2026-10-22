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

// Hỗ trợ truy cập trực tiếp tại root / hoặc /console (ADR-0048 & Clean URL)
const basename = window.location.pathname.startsWith('/console') ? '/console' : undefined;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryProvider>
      <ThemeProvider>
        <I18nProvider>
          <BrowserRouter basename={basename}>
            <App />
          </BrowserRouter>
        </I18nProvider>
      </ThemeProvider>
    </QueryProvider>
  </StrictMode>,
);
