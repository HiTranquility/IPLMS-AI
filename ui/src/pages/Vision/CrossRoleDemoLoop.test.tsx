import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { ModelVersion, ReviewItem, VisionSample, VisionSnapshot } from '@/api/types';
import { App } from '@/App';
import { fail, me, mockApi, ok, renderWithProviders } from '@/test/utils';
import { DatasetsPage } from './DatasetsPage';
import { LabelPage } from './LabelPage';
import { ModelsPage } from './ModelsPage';
import { ReviewPage } from './ReviewPage';

const sample: VisionSample = {
  capture_id: '3f1c2a64-5b7d-4e8f-9a01-23456789abcd',
  image_sha256: 'a'.repeat(64),
  machine_plate: '51A-123.46',
  machine_confidence: 0.71,
  confirmed_plate: '51A-123.45',
  human_corrected: true,
  selection_reasons: ['human_correction'],
  source_status: 'PENDING',
  purpose: 'train',
  source_final_plate: '',
  group_ref: 'b'.repeat(64),
  area_ref: 'c'.repeat(64),
  captured_at: null,
  source_updated_at: null,
  imported_at: null,
};

const reviewItem: ReviewItem = {
  ...sample,
  label: {
    id: 'lbl-001',
    verdict: 'CORRECTED',
    plate_text: '51A-123.45',
    labeler: 'Annotator An',
    created_at: '2026-10-24T08:00:00+00:00',
    quality_flags: ['glare'],
  },
};

const goldenSnapshot: VisionSnapshot = {
  id: 'snap-golden-1',
  kind: 'golden',
  name: 'golden-oct-2026',
  samples_sha256: 'd'.repeat(64),
  sample_count: 50,
  created_by: 'Data Engineer Dũng',
  created_at: '2026-10-24T09:00:00+00:00',
  frozen_by: '',
  frozen_at: null,
};

const candidateModel: ModelVersion = {
  id: 'mdl-2',
  name: 'anpr-yolo',
  version: '2.0',
  artifact_key: 'models/anpr-yolo/2.0/best.pt',
  sha256: 'e'.repeat(64),
  train_snapshot_id: 'snap-train-1',
  stage: 'candidate',
  note: 'fine-tuned night plates',
  registered_by: 'ML Engineer Minh',
  registered_at: '2026-10-24T10:00:00+00:00',
  proposed_by_id: '',
  proposed_by: '',
  proposed_at: null,
  approved_by: '',
  approved_at: null,
};

const bodyOf = (calls: { url: string; init?: RequestInit }[], suffix: string) =>
  JSON.parse(String(calls.find((c) => c.url.endsWith(suffix))?.init?.body));

describe('I-3 Cross-Role Demo Loop (5 vai trò AI Console)', () => {
  it('Bước 1 — Annotator (ai_annotator): gán nhãn được nhưng bị chặn khi mở trang Duyệt nhãn (/vision/review)', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/me')) {
        return ok(me({ member_id: 'm-ann', roles: ['ai_annotator'], permissions: ['ai:task:label'] }));
      }
      if (url.endsWith('/vision/queue?limit=20')) return ok(sample);
      if (url.endsWith('/labels')) return ok({ id: 'lbl-001' });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<LabelPage />);
    await screen.findByRole('img', { name: 'Ảnh cắt biển số' });
    await user.keyboard('1');
    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/labels'))).toBe(true));

    // Khi Annotator cố vào thẳng /vision/review (cần quyền ai:label:approve)
    renderWithProviders(<App />, '/vision/review');
    expect(await screen.findByText('Vai trò của bạn không mở được mục này')).toBeTruthy();
  });

  it('Bước 2 — Reviewer (ai_reviewer): duyệt nhãn của Annotator; nếu vi phạm luật bốn mắt (403 FORBIDDEN) thì hiện cảnh báo', async () => {
    let shouldFailFourEyes = false;
    const calls = mockApi((url) => {
      if (url.endsWith('/me')) {
        return ok(
          me({
            member_id: 'm-rev',
            roles: ['ai_reviewer'],
            permissions: ['ai:metrics:read', 'ai:task:label', 'ai:label:approve', 'ai:chatlog:read'],
          }),
        );
      }
      if (url.includes('/vision/reviews')) return ok(reviewItem);
      if (url.endsWith('/decision')) {
        return shouldFailFourEyes
          ? fail(403, 'FORBIDDEN', 'Thao tác này phải do một người khác thực hiện.')
          : ok({ id: 'lbl-001', status: 'APPROVED' });
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<ReviewPage />);

    expect(await screen.findByText(/Annotator An/)).toBeTruthy();
    // Ca 1: Duyệt hợp lệ (khác người gán)
    await user.click(screen.getByRole('button', { name: 'Duyệt' }));
    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/decision'))).toBe(true));
    expect(bodyOf(calls, '/decision')).toEqual({ decision: 'APPROVED', note: '' });

    // Ca 2: Giả lập vi phạm bốn mắt (cố tự duyệt nhãn chính mình -> 403 FORBIDDEN)
    shouldFailFourEyes = true;
    await user.click(screen.getByRole('button', { name: 'Duyệt' }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Thao tác này phải do một người khác thực hiện.');
    expect(alert.textContent).toContain('Mã: FORBIDDEN');
  });

  it('Bước 3 — Data Engineer (ai_data_engineer): xem và tạo được Snapshot nhưng không có quyền Khoá golden', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) {
        return ok(
          me({
            member_id: 'm-de',
            roles: ['ai_data_engineer'],
            permissions: ['ai:metrics:read', 'ai:pii:reveal', 'ai:pipeline:manage', 'ai:dataset:snapshot'],
          }),
        );
      }
      if (url.endsWith('/vision/snapshots')) return ok(goldenSnapshot);
      return undefined;
    });
    renderWithProviders(<DatasetsPage />);

    expect(await screen.findByText('golden-oct-2026')).toBeTruthy();
    // Data Engineer không có quyền ai:golden:freeze nên không thấy nút Khoá golden
    expect(screen.queryByRole('button', { name: 'Khoá golden' })).toBeNull();
  });

  it('Bước 4 — ML Engineer (ai_ml_engineer): đề xuất được model ứng viên nhưng không có nút Đưa lên production', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/me')) {
        return ok(
          me({
            member_id: 'm-mle',
            roles: ['ai_ml_engineer'],
            permissions: [
              'ai:metrics:read',
              'ai:chatlog:read',
              'ai:dataset:snapshot',
              'ai:model:evaluate',
              'ai:model:propose',
              'ai:prompt:edit',
            ],
          }),
        );
      }
      if (url.endsWith('/vision/models')) return ok(candidateModel);
      if (url.endsWith('/vision/evals')) return ok();
      if (url.endsWith('/propose')) return ok({ ...candidateModel, stage: 'proposed', proposed_by_id: 'm-mle' });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<ModelsPage />);

    const proposeBtn = await screen.findByRole('button', { name: 'Đề xuất' });
    expect(screen.queryByRole('button', { name: 'Đưa lên production' })).toBeNull();

    await user.click(proposeBtn);
    await user.type(screen.getByLabelText('Lý do'), 'CER giảm xuống 0.018 trên golden');
    await user.click(screen.getByRole('button', { name: 'Đề xuất' }));

    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/propose'))).toBe(true));
    expect(bodyOf(calls, '/propose')).toEqual({ reason: 'CER giảm xuống 0.018 trên golden' });
  });

  it('Bước 5 — AI Lead (ai_lead): duyệt Đưa lên production cho model do ML Engineer đề xuất kèm xác thực TOTP step-up', async () => {
    let promoteAttempts = 0;
    const proposedModel: ModelVersion = {
      ...candidateModel,
      stage: 'proposed',
      proposed_by_id: 'm-mle',
      proposed_by: 'ML Engineer Minh',
      proposed_at: '2026-10-24T11:00:00+00:00',
    };
    const calls = mockApi((url) => {
      if (url.endsWith('/me')) {
        return ok(
          me({
            member_id: 'm-lead',
            roles: ['ai_lead'],
            permissions: ['ai:metrics:read', 'ai:model:propose', 'ai:model:promote', 'ai:golden:freeze'],
          }),
        );
      }
      if (url.endsWith('/vision/models')) return ok(proposedModel);
      if (url.endsWith('/vision/evals')) return ok();
      if (url.endsWith('/promote')) {
        promoteAttempts += 1;
        return promoteAttempts === 1
          ? fail(401, 'STEP_UP_REQUIRED', 'Thao tác này cần nhập lại mã TOTP kèm lý do.')
          : ok({ ...proposedModel, stage: 'production', approved_by: 'AI Lead Long' });
      }
      if (url.endsWith('/auth/step-up')) return ok({ mfa_required: false });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<ModelsPage />);

    await user.click(await screen.findByRole('button', { name: 'Đưa lên production' }));
    await user.type(screen.getByLabelText('Lý do'), 'Duyệt phát hành model v2.0');
    await user.click(screen.getByRole('button', { name: 'Đưa lên production' }));

    const totpInput = await screen.findByLabelText('Mã 6 số');
    await user.type(totpInput, '654321');
    await user.click(screen.getByRole('button', { name: 'Xác thực và làm tiếp' }));

    await waitFor(() => expect(promoteAttempts).toBe(2));
    expect(bodyOf(calls, '/auth/step-up')).toEqual({ code: '654321', reason: 'Duyệt phát hành model v2.0' });
    expect(bodyOf(calls, '/promote')).toEqual({ reason: 'Duyệt phát hành model v2.0' });
  });
});
