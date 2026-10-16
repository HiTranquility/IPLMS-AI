import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { consoleApi, type ModelInput } from '@/api/console';
import { QUERY_KEYS } from '@/api/queryKeys';
import type { Decision, LabelVerdict } from '@/api/types';

/** Mọi thao tác vision làm cũ hàng đợi/số đếm/nhật ký → làm mới cả nhóm `vision`. */
function useVisionMutation<A, R>(fn: (args: A) => Promise<R>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: QUERY_KEYS.VISION });
      void client.invalidateQueries({ queryKey: QUERY_KEYS.AUDIT });
    },
  });
}

export const useVisionStatus = () => useQuery({ queryKey: QUERY_KEYS.VISION_STATUS, queryFn: consoleApi.visionStatus });
export const useLabelQueue = () => useQuery({ queryKey: QUERY_KEYS.LABEL_QUEUE, queryFn: consoleApi.labelQueue });
export const useReviewQueue = () => useQuery({ queryKey: QUERY_KEYS.REVIEW_QUEUE, queryFn: consoleApi.reviewQueue });
export const useSnapshots = () => useQuery({ queryKey: QUERY_KEYS.SNAPSHOTS, queryFn: consoleApi.snapshots });
export const useModels = () => useQuery({ queryKey: QUERY_KEYS.MODELS, queryFn: consoleApi.models });
export const useAccuracy = () => useQuery({ queryKey: QUERY_KEYS.ACCURACY, queryFn: consoleApi.accuracy });
export const usePolicies = () => useQuery({ queryKey: QUERY_KEYS.POLICIES, queryFn: consoleApi.policies });

export function useEvals() {
  return useQuery({
    queryKey: QUERY_KEYS.EVALS,
    queryFn: consoleApi.evals,
    // Lượt đo chạy nền: còn lượt RUNNING thì hỏi lại mỗi 3 giây.
    refetchInterval: (query) => (query.state.data?.some((e) => e.status === 'RUNNING') ? 3000 : false),
  });
}

export const useAddLabel = () =>
  useVisionMutation((a: { captureId: string; verdict: LabelVerdict; plateText: string }) =>
    consoleApi.addLabel(a.captureId, a.verdict, a.plateText),
  );
export const useDecideLabel = () =>
  useVisionMutation((a: { labelId: string; decision: Decision; note: string }) =>
    consoleApi.decideLabel(a.labelId, a.decision, a.note),
  );
export const useCreateSnapshot = () =>
  useVisionMutation((a: { kind: 'train' | 'golden'; name: string }) => consoleApi.createSnapshot(a.kind, a.name));
export const useFreezeSnapshot = () =>
  useVisionMutation((a: { id: string; reason: string }) => consoleApi.freezeSnapshot(a.id, a.reason));
export const useRegisterModel = () => useVisionMutation((input: ModelInput) => consoleApi.registerModel(input));
export const useProposeModel = () =>
  useVisionMutation((a: { id: string; reason: string }) => consoleApi.proposeModel(a.id, a.reason));
export const usePromoteModel = () =>
  useVisionMutation((a: { id: string; reason: string }) => consoleApi.promoteModel(a.id, a.reason));
export const useStartEval = () => useVisionMutation((snapshotId: string) => consoleApi.startEval(snapshotId));
export const useProposePolicy = () =>
  useVisionMutation((a: { threshold: number; auditRate: number; reason: string }) =>
    consoleApi.proposePolicy(a.threshold, a.auditRate, a.reason),
  );
export const useDecidePolicy = () =>
  useVisionMutation((a: { id: string; decision: Decision; note: string }) =>
    consoleApi.decidePolicy(a.id, a.decision, a.note),
  );

export function useStepUpMutation() {
  return useMutation({ mutationFn: (a: { code: string; reason: string }) => consoleApi.stepUp(a.code, a.reason) });
}
