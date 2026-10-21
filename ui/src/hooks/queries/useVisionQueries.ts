import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import {
  getAccuracy,
  getEvals,
  getLabelQueue,
  getModels,
  getPolicies,
  getReviewQueue,
  getSnapshots,
  getVisionStatus,
} from '@/services/apiEndpoints/vision.endpoint';

export const useVisionStatusQuery = () =>
  useQuery({ queryKey: queryKeys.vision.status(), queryFn: getVisionStatus });

export const useLabelQueueQuery = () =>
  useQuery({ queryKey: queryKeys.vision.labelQueue(), queryFn: getLabelQueue });

export const useReviewQueueQuery = () =>
  useQuery({ queryKey: queryKeys.vision.reviewQueue(), queryFn: getReviewQueue });

export const useSnapshotsQuery = () =>
  useQuery({ queryKey: queryKeys.vision.snapshots(), queryFn: getSnapshots });

export const useModelsQuery = () =>
  useQuery({ queryKey: queryKeys.vision.models(), queryFn: getModels });

export const useAccuracyQuery = () =>
  useQuery({ queryKey: queryKeys.vision.accuracy(), queryFn: getAccuracy });

export const usePoliciesQuery = () =>
  useQuery({ queryKey: queryKeys.vision.policies(), queryFn: getPolicies });

export function useEvalsQuery() {
  return useQuery({
    queryKey: queryKeys.vision.evals(),
    queryFn: getEvals,
    // Lượt đo chạy nền: còn lượt RUNNING thì hỏi lại mỗi 3 giây.
    refetchInterval: (query) => (query.state.data?.some((e) => e.status === 'RUNNING') ? 3000 : false),
  });
}

export const useVisionStatus = useVisionStatusQuery;
export const useLabelQueue = useLabelQueueQuery;
export const useReviewQueue = useReviewQueueQuery;
export const useSnapshots = useSnapshotsQuery;
export const useModels = useModelsQuery;
export const useAccuracy = useAccuracyQuery;
export const usePolicies = usePoliciesQuery;
export const useEvals = useEvalsQuery;
