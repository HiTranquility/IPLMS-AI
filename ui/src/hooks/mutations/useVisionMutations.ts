import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import {
  addLabel,
  createSnapshot,
  decideLabel,
  decidePolicy,
  freezeSnapshot,
  promoteModel,
  proposeModel,
  proposePolicy,
  registerModel,
  seedDemoBatch,
  startEval,
} from '@/services/apiEndpoints/vision.endpoint';
import type {
  AddLabelRequest,
  CreateSnapshotRequest,
  DecideLabelRequest,
  DecidePolicyRequest,
  ModelInput,
  ProposePolicyRequest,
} from '@/types/vision';

/** Mọi thao tác vision làm cũ hàng đợi/số đếm/nhật ký → làm mới cả nhóm `vision`. */
function useVisionMutation<A, R>(fn: (args: A) => Promise<R>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.vision.all() });
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
    },
  });
}

export const useAddLabelMutation = () =>
  useVisionMutation((a: AddLabelRequest) => addLabel(a.captureId, a.verdict, a.plateText, a.qualityFlags));

export const useDecideLabelMutation = () =>
  useVisionMutation((a: DecideLabelRequest) => decideLabel(a.labelId, a.decision, a.note));

export const useCreateSnapshotMutation = () =>
  useVisionMutation((a: CreateSnapshotRequest) => createSnapshot(a.kind, a.name));

export const useFreezeSnapshotMutation = () =>
  useVisionMutation((a: { id: string; reason: string }) => freezeSnapshot(a.id, a.reason));

export const useRegisterModelMutation = () =>
  useVisionMutation((input: ModelInput) => registerModel(input));

export const useProposeModelMutation = () =>
  useVisionMutation((a: { id: string; reason: string }) => proposeModel(a.id, a.reason));

export const usePromoteModelMutation = () =>
  useVisionMutation((a: { id: string; reason: string }) => promoteModel(a.id, a.reason));

export const useStartEvalMutation = () =>
  useVisionMutation((snapshotId: string) => startEval(snapshotId));

export const useProposePolicyMutation = () =>
  useVisionMutation((a: ProposePolicyRequest) => proposePolicy(a.threshold, a.auditRate, a.reason));

export const useDecidePolicyMutation = () =>
  useVisionMutation((a: DecidePolicyRequest) => decidePolicy(a.id, a.decision, a.note));

export const useAddLabel = useAddLabelMutation;
export const useDecideLabel = useDecideLabelMutation;
export const useCreateSnapshot = useCreateSnapshotMutation;
export const useFreezeSnapshot = useFreezeSnapshotMutation;
export const useRegisterModel = useRegisterModelMutation;
export const useProposeModel = useProposeModelMutation;
export const usePromoteModel = usePromoteModelMutation;
export const useStartEval = useStartEvalMutation;
export const useProposePolicy = useProposePolicyMutation;
export const useDecidePolicy = useDecidePolicyMutation;
export const useSeedDemoBatchMutation = () =>
  useVisionMutation(() => seedDemoBatch());
export const useSeedDemoBatch = useSeedDemoBatchMutation;
