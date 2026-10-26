import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { QualityFlag, ReviewItem } from '@/api/types';
import { me, mockApi, ok, renderWithProviders } from '@/test/utils';
import { ReviewPage } from './ReviewPage';

const base: Omit<ReviewItem, 'label' | 'capture_id' | 'machine_plate'> = {
  image_sha256: 'a'.repeat(64),
  machine_confidence: 0.4,
  confirmed_plate: '',
  human_corrected: false,
  selection_reasons: ['low_confidence'],
  source_status: 'PENDING',
  purpose: 'audit',
  source_final_plate: '',
  group_ref: 'b'.repeat(64),
  area_ref: 'c'.repeat(64),
  captured_at: null,
  source_updated_at: null,
  imported_at: null,
};

const label = (
  id: string,
  verdict: ReviewItem['label']['verdict'],
  plate_text = '',
  quality_flags: QualityFlag[] = [],
) => ({
  id,
  verdict,
  plate_text,
  labeler: 'Annotator An',
  created_at: '2026-10-24T08:00:00+00:00',
  quality_flags,
});

describe('Tên nút theo dòng ở Duyệt nhãn (ISSUE-019 review-1 BUG-05, audit-5 A-64)', () => {
  it('mỗi dòng có tên riêng, kể cả nhãn UNUSABLE không có biển đề xuất', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me({ permissions: ['ai:metrics:read', 'ai:label:approve'] }));
      if (url.includes('/vision/reviews')) {
        return ok(
          { ...base, capture_id: 'cap-1', machine_plate: '30A-111.11', label: label('l1', 'UNUSABLE') },
          { ...base, capture_id: 'cap-2', machine_plate: '30A-222.22', label: label('l2', 'UNUSABLE') },
          { ...base, capture_id: 'cap-3', machine_plate: '51A-000.00', label: label('l3', 'CORRECTED', '51A-123.45') },
        );
      }
      return undefined;
    });
    renderWithProviders(<ReviewPage />);

    expect(await screen.findByRole('button', { name: 'Duyệt nhãn 30A-111.11' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Duyệt nhãn 30A-222.22' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Duyệt nhãn 51A-123.45' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Trả lại nhãn 30A-111.11' })).toBeTruthy();
  });

  it('lọc hàng đợi duyệt 4 mắt theo cờ chất lượng ảnh (ISSUE-020)', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me({ permissions: ['ai:metrics:read', 'ai:label:approve'] }));
      if (url.includes('/vision/reviews')) {
        return ok(
          { ...base, capture_id: 'cap-1', machine_plate: '30A-111.11', label: label('l1', 'CORRECTED', '30A-111.11', ['glare']) },
          { ...base, capture_id: 'cap-2', machine_plate: '59-K1 123.45', label: label('l2', 'CORRECTED', '59-K1 123.45', ['two_line']) },
        );
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<ReviewPage />);

    expect(await screen.findByRole('button', { name: 'Duyệt nhãn 30A-111.11' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Duyệt nhãn 59-K1 123.45' })).toBeTruthy();

    const flagGroup = screen.getByRole('group', { name: 'Thuộc tính ảnh / biển số' });
    const glareBtn = within(flagGroup).getByRole('button', { name: 'Chói sáng đèn pha' });
    expect(glareBtn.getAttribute('aria-pressed')).toBe('false');

    await user.click(glareBtn);
    expect(glareBtn.getAttribute('aria-pressed')).toBe('true');
    expect(screen.queryByRole('button', { name: 'Duyệt nhãn 30A-111.11' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Duyệt nhãn 59-K1 123.45' })).toBeNull();

    await user.click(glareBtn);
    expect(glareBtn.getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByRole('button', { name: 'Duyệt nhãn 59-K1 123.45' })).toBeTruthy();
  });
});
