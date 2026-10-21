import type { TurnStatus, Verdict } from '../shares/copilot.item';

export interface TurnFilter {
  status?: TurnStatus;
  feedback?: 1 | -1;
}

export type ReviewTurnRequest = {
  turnId: string;
  verdict: Verdict;
  note: string;
};
