import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { ModelVersion, VisionSample } from '@/api/types';
import { fail, me, mockApi, ok, renderWithProviders } from '@/test/utils';
import { LabelPage } from './LabelPage';
import { ModelsPage } from './ModelsPage';
import { DatasetsPage } from './DatasetsPage';

const sample: VisionSample = {
  capture_id: '3f1c2a64-5b7d-4e8f-9a01-23456789abcd', image_sha256: 'a'.repeat(64), machine_plate: '51A12346',
  machine_confidence: 0.62, confirmed_plate: '51A12345', human_corrected: true, selection_reasons: ['human_correction'],
  source_status: 'PENDING', purpose: 'train', source_final_plate: '', group_ref: 'b'.repeat(64), area_ref: 'c'.repeat(64),
  captured_at: null, source_updated_at: null, imported_at: null,
};

const bodyOf = (calls: { url: string; init?: RequestInit }[], suffix: string) =>
  JSON.parse(String(calls.find((c) => c.url.endsWith(suffix))?.init?.body));

describe('LabelPage', () => {
  it('phím 1 gán "đúng" cho mẫu đang hiện; ảnh lấy từ API console', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/vision/queue?limit=20')) return ok(sample);
      if (url.endsWith('/labels')) return ok({ id: 'l1' });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<LabelPage />);
    const img = await screen.findByRole('img', { name: 'Ảnh cắt biển số' });
    expect(img.getAttribute('src')).toBe(`/api/vision/samples/${sample.capture_id}/crop`);
    await user.keyboard('1');
    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/labels'))).toBe(true));
    expect(bodyOf(calls, '/labels')).toEqual({ verdict: 'CORRECT', plate_text: '', quality_flags: [] });
  });

  it('sửa biển gửi biển đã viết hoa', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/vision/queue?limit=20')) return ok(sample);
      if (url.endsWith('/labels')) return ok({ id: 'l1' });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<LabelPage />);
    await user.click(await screen.findByRole('button', { name: /Sửa biển/ }));
    await user.type(screen.getByLabelText('Biển đúng'), '51a-123.46');
    await user.click(screen.getByRole('button', { name: 'Lưu biển sửa' }));
    await waitFor(() =>
      expect(bodyOf(calls, '/labels')).toEqual({ verdict: 'CORRECTED', plate_text: '51A-123.46', quality_flags: [] }),
    );
  });

  it('cờ ảnh đã chọn được gửi cùng nhãn (bug-022)', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/vision/queue?limit=20')) return ok(sample);
      if (url.endsWith('/labels')) return ok({ id: 'l1' });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<LabelPage />);
    await user.click(await screen.findByRole('button', { name: /Biển 2 dòng/ }));
    await user.click(screen.getByRole('button', { name: /Chói sáng đèn pha/ }));
    await user.keyboard('1');
    await waitFor(() =>
      expect(bodyOf(calls, '/labels')).toEqual({ verdict: 'CORRECT', plate_text: '', quality_flags: ['two_line', 'glare'] }),
    );
  });
});

describe('DatasetsPage — khoá golden cần step-up tại chỗ', () => {
  it('server đòi STEP_UP_REQUIRED → hiện ô mã → xác thực rồi làm tiếp', async () => {
    let freezeCalls = 0;
    const calls = mockApi((url) => {
      if (url.endsWith('/me')) return ok(me({ permissions: ['ai:metrics:read', 'ai:dataset:snapshot', 'ai:golden:freeze'] }));
      if (url.endsWith('/vision/snapshots')) {
        return ok({ id: 's1', kind: 'golden', name: 'golden v1', samples_sha256: 'd'.repeat(64), sample_count: 30,
          created_by: 'E', created_at: '2026-10-16T01:00:00+00:00', frozen_by: '', frozen_at: null });
      }
      if (url.endsWith('/freeze')) {
        freezeCalls += 1;
        return freezeCalls === 1 ? fail(401, 'STEP_UP_REQUIRED', 'Thao tác này cần nhập lại mã TOTP kèm lý do.') : ok({ ok: true });
      }
      if (url.endsWith('/auth/step-up')) return ok({ mfa_required: false });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<DatasetsPage />);
    await user.click(await screen.findByRole('button', { name: 'Khoá golden' }));
    await user.type(screen.getByLabelText('Lý do'), 'chốt bộ test');
    await user.click(screen.getByRole('button', { name: 'Khoá golden' }));
    const code = await screen.findByLabelText('Mã 6 số');
    await user.type(code, '123456');
    await user.click(screen.getByRole('button', { name: 'Xác thực và làm tiếp' }));
    await waitFor(() => expect(freezeCalls).toBe(2));
    expect(bodyOf(calls, '/auth/step-up')).toEqual({ code: '123456', reason: 'chốt bộ test' });
  });

  it('cờ ảnh đã chọn được gửi cùng nhãn (bug-022)', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/vision/queue?limit=20')) return ok(sample);
      if (url.endsWith('/labels')) return ok({ id: 'l1' });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<LabelPage />);
    await user.click(await screen.findByRole('button', { name: /Biển 2 dòng/ }));
    await user.click(screen.getByRole('button', { name: /Chói sáng đèn pha/ }));
    await user.keyboard('1');
    await waitFor(() =>
      expect(bodyOf(calls, '/labels')).toEqual({ verdict: 'CORRECT', plate_text: '', quality_flags: ['two_line', 'glare'] }),
    );
  });
});

describe('ModelsPage', () => {
  it('AI Lead không promote được model chính mình đề xuất', async () => {
    const model: ModelVersion = {
      id: 'm1', name: 'anpr-yolo', version: '1', artifact_key: 'models/anpr-yolo/1/best.pt', sha256: 'e'.repeat(64),
      train_snapshot_id: '', stage: 'proposed', note: '', registered_by: 'E', registered_at: '2026-10-16T01:00:00+00:00',
      proposed_by_id: 'm-1', proposed_by: 'Tôi', proposed_at: '2026-10-16T02:00:00+00:00', approved_by: '', approved_at: null,
    };
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me({ member_id: 'm-1', permissions: ['ai:metrics:read', 'ai:model:promote'] }));
      if (url.endsWith('/vision/models')) return ok(model);
      if (url.endsWith('/vision/evals')) return ok();
      return undefined;
    });
    renderWithProviders(<ModelsPage />);
    const promote = await screen.findByRole('button', { name: 'Đưa lên production' });
    await waitFor(() => expect(promote).toHaveProperty('disabled', true));
    expect(screen.getByText('Bạn đề xuất model này — cần AI Lead khác.')).toBeTruthy();
  });

  it('cờ ảnh đã chọn được gửi cùng nhãn (bug-022)', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/vision/queue?limit=20')) return ok(sample);
      if (url.endsWith('/labels')) return ok({ id: 'l1' });
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<LabelPage />);
    await user.click(await screen.findByRole('button', { name: /Biển 2 dòng/ }));
    await user.click(screen.getByRole('button', { name: /Chói sáng đèn pha/ }));
    await user.keyboard('1');
    await waitFor(() =>
      expect(bodyOf(calls, '/labels')).toEqual({ verdict: 'CORRECT', plate_text: '', quality_flags: ['two_line', 'glare'] }),
    );
  });
});
