import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useCan } from '@/hooks/common/useCan';
import { useStepUpMutation } from '@/hooks/mutations/useAuthMutations';
import { useDecidePolicy } from '@/hooks/mutations/useVisionMutations';
import { useMe } from '@/hooks/queries/useAuthQueries';
import { useAccuracy, usePolicies, useVisionStatus } from '@/hooks/queries/useVisionQueries';

export interface VisionOverviewPageContextValue {
  me: ReturnType<typeof useMe>;
  status: ReturnType<typeof useVisionStatus>;
  accuracy: ReturnType<typeof useAccuracy>;
  policies: ReturnType<typeof usePolicies>;
  decide: ReturnType<typeof useDecidePolicy>;
  stepUp: ReturnType<typeof useStepUpMutation>;
  canPropose: boolean;
  canDecide: boolean;
}

const VisionOverviewPageContext = createContext<VisionOverviewPageContextValue | null>(null);

export function VisionOverviewPageProvider({ children }: { children: ReactNode }) {
  const me = useMe();
  const status = useVisionStatus();
  const accuracy = useAccuracy();
  const policies = usePolicies();
  const decide = useDecidePolicy();
  const stepUp = useStepUpMutation();
  const canPropose = useCan('ai:model:propose');
  const canDecide = useCan('ai:policy:threshold');

  const value = useMemo<VisionOverviewPageContextValue>(
    () => ({ me, status, accuracy, policies, decide, stepUp, canPropose, canDecide }),
    [me, status, accuracy, policies, decide, stepUp, canPropose, canDecide],
  );

  return <VisionOverviewPageContext.Provider value={value}>{children}</VisionOverviewPageContext.Provider>;
}

export function useVisionOverviewPageContext(): VisionOverviewPageContextValue {
  const ctx = useContext(VisionOverviewPageContext);
  if (!ctx) throw new Error('useVisionOverviewPageContext must be used within VisionOverviewPageProvider');
  return ctx;
}
