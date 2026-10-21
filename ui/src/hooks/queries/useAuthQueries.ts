import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { ApiError } from '@/services/apiClient';
import { getMe } from '@/services/apiEndpoints/auth.endpoint';

export function useMeQuery() {
  return useQuery({
    queryKey: queryKeys.auth.me(),
    queryFn: getMe,
    // 401 = chưa đăng nhập, là trạng thái chứ không phải lỗi cần thử lại.
    retry: (count, error) => !(error instanceof ApiError && error.status === 401) && count < 2,
  });
}

export const useMe = useMeQuery;
