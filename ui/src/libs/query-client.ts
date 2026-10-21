import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/services/apiClient';

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // 401/403 là trạng thái quyền, thử lại không đổi được kết quả.
        retry: (count, error) => !(error instanceof ApiError && [401, 403].includes(error.status)) && count < 2,
      },
    },
  });
}

export const queryClient = createQueryClient();
