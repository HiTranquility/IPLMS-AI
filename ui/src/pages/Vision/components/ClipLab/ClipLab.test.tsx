import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, describe, expect, it } from 'vitest';
import { fail, mockApi, ok, renderWithProviders } from '@/test/utils';
import { ClipLab } from './ClipLab';

const clip = () => new File([new Uint8Array([0, 0, 0, 24])], 'gate.mp4', { type: 'video/mp4' });

const EVENTS = [
  { plate_number: '51A-888.88', confidence: 0.96, best_time_s: 1, start_time_s: 0, end_time_s: 2.5, frame_count: 6, crop_image: 'data:image/jpeg;base64,AA==' },
  { plate_number: '30E-123.45', confidence: 0.88, best_time_s: 5.5, start_time_s: 5, end_time_s: 7.5, frame_count: 6, crop_image: null },
  { plate_number: '15A-345.67', confidence: 0.93, best_time_s: 10, start_time_s: 10, end_time_s: 12.5, frame_count: 6, crop_image: null },
];

beforeAll(() => {
  // jsdom không có object URL.
  URL.createObjectURL = () => 'blob:clip';
  URL.revokeObjectURL = () => undefined;
});

describe('ClipLab (REQ-021 A)', () => {
  it('chưa chọn clip thì không cho chạy; file không phải video bị chặn ở trình duyệt', async () => {
    const calls = mockApi(() => undefined);
    const user = userEvent.setup({ applyAccept: false });
    renderWithProviders(<ClipLab />);
    expect(screen.getByRole('button', { name: /Đọc clip/ })).toHaveProperty('disabled', true);

    await user.upload(screen.getByLabelText('Chọn clip'), new File(['x'], 'a.png', { type: 'image/png' }));
    expect(screen.getByRole('alert').textContent).toContain('Chỉ nhận clip MP4 hoặc WebM.');
    expect(calls).toHaveLength(0);
  });

  it('gửi clip + chế độ, hiện dòng thời gian và từng sự kiện', async () => {
    const calls = mockApi((url) =>
      url.endsWith('/tools/anpr/recognize-clip') ? ok({ sampled_frames: 21, plate_reads: 18, latency_ms: 36600, events: EVENTS }) : undefined,
    );
    const user = userEvent.setup();
    renderWithProviders(<ClipLab />);
    await user.upload(screen.getByLabelText('Chọn clip'), clip());
    await user.click(screen.getByRole('button', { name: 'Theo chuyển động' }));
    await user.click(screen.getByRole('button', { name: /Đọc clip/ }));

    await waitFor(() => expect(screen.getByText('51A-888.88')).toBeTruthy());
    const form = calls.find((c) => c.url.endsWith('/recognize-clip'))?.init?.body as FormData;
    expect(form.get('mode')).toBe('motion');
    expect((form.get('file') as File).name).toBe('gate.mp4');

    const timeline = screen.getByRole('group', { name: 'Dòng thời gian' });
    expect(timeline.querySelectorAll('button')).toHaveLength(3);
    expect(screen.getByRole('button', { name: 'Tua tới 30E-123.45 lúc 5.5 s' })).toBeTruthy();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
    expect(screen.getByAltText('Ảnh biển 51A-888.88 ở frame tốt nhất')).toBeTruthy();
    expect(screen.getByText('36.6 s')).toBeTruthy();
  });

  it('server từ chối (quá giới hạn) thì hiện đúng thông điệp, không có sự kiện', async () => {
    mockApi((url) => (url.endsWith('/recognize-clip') ? fail(400, 'INVALID_INPUT', 'Clip vượt 50 MB.') : undefined));
    const user = userEvent.setup();
    renderWithProviders(<ClipLab />);
    await user.upload(screen.getByLabelText('Chọn clip'), clip());
    await user.click(screen.getByRole('button', { name: /Đọc clip/ }));

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByRole('alert').textContent).toContain('Clip vượt 50 MB.');
    expect(screen.queryByRole('group', { name: 'Dòng thời gian' })).toBeNull();
  });
});
