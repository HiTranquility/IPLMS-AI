import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ApiError } from '@/api/client';
import { App } from './App';
import { applyTheme, initialTheme } from './utils/theme';
import './index.css';

applyTheme(initialTheme());

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // 401/403 là trạng thái quyền, thử lại không đổi được kết quả.
      retry: (count, error) => !(error instanceof ApiError && [401, 403].includes(error.status)) && count < 2,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/console">
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
