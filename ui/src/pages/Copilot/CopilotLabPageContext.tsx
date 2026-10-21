import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { useCan } from '@/hooks/common/useCan';
import { useTurns } from '@/hooks/queries/useCopilotQueries';
import type { Turn, TurnFilter, TurnStatus } from '@/types/copilot';

export type StatusOption = TurnStatus | 'all';
export type FeedbackOption = 'all' | 'down' | 'up';

function toFilter(status: StatusOption, feedback: FeedbackOption): TurnFilter {
  return {
    status: status === 'all' ? undefined : status,
    feedback: feedback === 'all' ? undefined : feedback === 'up' ? 1 : -1,
  };
}

export interface CopilotLabPageContextValue {
  status: StatusOption;
  setStatus: (value: StatusOption) => void;
  feedback: FeedbackOption;
  setFeedback: (value: FeedbackOption) => void;
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
  turns: ReturnType<typeof useTurns>;
  rows: Turn[];
  selected: Turn | null;
  canReview: boolean;
}

const CopilotLabPageContext = createContext<CopilotLabPageContextValue | null>(null);

export function CopilotLabPageProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<StatusOption>('all');
  const [feedback, setFeedback] = useState<FeedbackOption>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const turns = useTurns(toFilter(status, feedback));
  const canReview = useCan('ai:label:approve');
  const rows = useMemo(() => turns.data?.pages.flat() ?? [], [turns.data]);
  const selected = useMemo(() => rows.find((t) => t.turn_id === selectedId) ?? null, [rows, selectedId]);

  const contextValue = useMemo<CopilotLabPageContextValue>(
    () => ({
      status,
      setStatus,
      feedback,
      setFeedback,
      selectedId,
      setSelectedId,
      turns,
      rows,
      selected,
      canReview,
    }),
    [status, feedback, selectedId, turns, rows, selected, canReview],
  );

  return <CopilotLabPageContext.Provider value={contextValue}>{children}</CopilotLabPageContext.Provider>;
}

export function useCopilotLabPageContext(): CopilotLabPageContextValue {
  const ctx = useContext(CopilotLabPageContext);
  if (!ctx) throw new Error('useCopilotLabPageContext must be used within CopilotLabPageProvider');
  return ctx;
}
