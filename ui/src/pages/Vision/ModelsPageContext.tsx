import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useCan } from '@/hooks/common/useCan';
import { useStepUpMutation } from '@/hooks/mutations/useAuthMutations';
import { usePromoteModel, useProposeModel } from '@/hooks/mutations/useVisionMutations';
import { useMe } from '@/hooks/queries/useAuthQueries';
import { useEvals, useModels } from '@/hooks/queries/useVisionQueries';

export interface ModelsPageContextValue {
  me: ReturnType<typeof useMe>;
  models: ReturnType<typeof useModels>;
  evals: ReturnType<typeof useEvals>;
  propose: ReturnType<typeof useProposeModel>;
  promote: ReturnType<typeof usePromoteModel>;
  stepUp: ReturnType<typeof useStepUpMutation>;
  canEvaluate: boolean;
  canPropose: boolean;
  canPromote: boolean;
}

const ModelsPageContext = createContext<ModelsPageContextValue | null>(null);

export function ModelsPageProvider({ children }: { children: ReactNode }) {
  const me = useMe();
  const models = useModels();
  const evals = useEvals();
  const propose = useProposeModel();
  const promote = usePromoteModel();
  const stepUp = useStepUpMutation();
  const canEvaluate = useCan('ai:model:evaluate');
  const canPropose = useCan('ai:model:propose');
  const canPromote = useCan('ai:model:promote');

  const value = useMemo<ModelsPageContextValue>(
    () => ({ me, models, evals, propose, promote, stepUp, canEvaluate, canPropose, canPromote }),
    [me, models, evals, propose, promote, stepUp, canEvaluate, canPropose, canPromote],
  );

  return <ModelsPageContext.Provider value={value}>{children}</ModelsPageContext.Provider>;
}

export function useModelsPageContext(): ModelsPageContextValue {
  const ctx = useContext(ModelsPageContext);
  if (!ctx) throw new Error('useModelsPageContext must be used within ModelsPageProvider');
  return ctx;
}
