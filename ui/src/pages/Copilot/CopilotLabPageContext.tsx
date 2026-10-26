import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { useCan } from '@/hooks/common/useCan';
import { useTurns } from '@/hooks/queries/useCopilotQueries';
import type { Turn, TurnFilter, TurnStatus } from '@/types/copilot';

export type StatusOption = TurnStatus | 'all';
export type FeedbackOption = 'all' | 'down' | 'up';
export type TimeRangeOption = 'all' | 'today' | '3days' | '7days';

export interface ReviewProgressStats {
  total: number;
  reviewed: number;
  correct: number;
  incorrect: number;
  unsafe: number;
  accuracyPct: number;
  pending: number;
  progressPct: number;
}

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
  timeRange: TimeRangeOption;
  setTimeRange: (value: TimeRangeOption) => void;
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
  turns: ReturnType<typeof useTurns>;
  rows: Turn[];
  selected: Turn | null;
  canReview: boolean;
  stats: ReviewProgressStats;
}

const CopilotLabPageContext = createContext<CopilotLabPageContextValue | null>(null);

export function CopilotLabPageProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<StatusOption>('all');
  const [feedback, setFeedback] = useState<FeedbackOption>('all');
  const [timeRange, setTimeRange] = useState<TimeRangeOption>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const turns = useTurns(toFilter(status, feedback));
  const canReview = useCan('ai:label:approve');

  const rawRows = useMemo(() => turns.data?.pages.flat() ?? [], [turns.data]);

  const rows = useMemo(() => {
    let list = rawRows;

    // Lọc theo khoảng thời gian
    if (timeRange === 'today') {
      const todayStart = new Date();
      todayStart.setHours(0, 0, 0, 0);
      const todayTime = todayStart.getTime();
      list = list.filter((turn) => new Date(turn.at).getTime() >= todayTime);
    } else if (timeRange === '3days') {
      const cutoff = Date.now() - 3 * 24 * 60 * 60 * 1000;
      list = list.filter((turn) => new Date(turn.at).getTime() >= cutoff);
    } else if (timeRange === '7days') {
      const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
      list = list.filter((turn) => new Date(turn.at).getTime() >= cutoff);
    }

    // Lọc theo từ khóa tìm kiếm (câu hỏi, câu trả lời, mã lượt, bãi xe)
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (turn) =>
          turn.query.toLowerCase().includes(q) ||
          (turn.answer && turn.answer.toLowerCase().includes(q)) ||
          turn.turn_id.toLowerCase().includes(q) ||
          (turn.parking_lot_id && turn.parking_lot_id.toLowerCase().includes(q)),
      );
    }

    return list;
  }, [rawRows, timeRange, searchQuery]);

  const stats = useMemo<ReviewProgressStats>(() => {
    const total = rawRows.length;
    const reviewed = rawRows.filter((t) => Boolean(t.review)).length;
    const correct = rawRows.filter((t) => t.review?.verdict === 'CORRECT').length;
    const incorrect = rawRows.filter((t) => t.review?.verdict === 'INCORRECT').length;
    const unsafe = rawRows.filter((t) => t.review?.verdict === 'UNSAFE').length;
    const reviewedForAccuracy = correct + incorrect + unsafe;
    const accuracyPct = reviewedForAccuracy > 0 ? Math.round((correct / reviewedForAccuracy) * 100) : 0;
    const pending = total - reviewed;
    const progressPct = total > 0 ? Math.round((reviewed / total) * 100) : 0;
    return {
      total,
      reviewed,
      correct,
      incorrect,
      unsafe,
      accuracyPct,
      pending,
      progressPct,
    };
  }, [rawRows]);

  const selected = useMemo(() => rows.find((t) => t.turn_id === selectedId) ?? null, [rows, selectedId]);

  const contextValue = useMemo<CopilotLabPageContextValue>(
    () => ({
      status,
      setStatus,
      feedback,
      setFeedback,
      timeRange,
      setTimeRange,
      searchQuery,
      setSearchQuery,
      selectedId,
      setSelectedId,
      turns,
      rows,
      selected,
      canReview,
      stats,
    }),
    [
      status,
      feedback,
      timeRange,
      searchQuery,
      selectedId,
      turns,
      rows,
      selected,
      canReview,
      stats,
    ],
  );

  return <CopilotLabPageContext.Provider value={contextValue}>{children}</CopilotLabPageContext.Provider>;
}

export function useCopilotLabPageContext(): CopilotLabPageContextValue {
  const ctx = useContext(CopilotLabPageContext);
  if (!ctx) throw new Error('useCopilotLabPageContext must be used within CopilotLabPageProvider');
  return ctx;
}
