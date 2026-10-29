import type { Decision, LabelVerdict, QualityFlag } from '../shares/vision.item';

export interface ModelInput {
  name: string;
  version: string;
  artifact_key: string;
  sha256: string;
  note: string;
  train_snapshot_id?: string | null;
}

export type AddLabelRequest = {
  captureId: string;
  verdict: LabelVerdict;
  plateText: string;
  qualityFlags: QualityFlag[];
};

export type DecideLabelRequest = {
  labelId: string;
  decision: Decision;
  note: string;
};

export type CreateSnapshotRequest = {
  kind: 'train' | 'golden';
  name: string;
};

export type ProposePolicyRequest = {
  threshold: number;
  auditRate: number;
  reason: string;
};

export type DecidePolicyRequest = {
  id: string;
  decision: Decision;
  note: string;
};
