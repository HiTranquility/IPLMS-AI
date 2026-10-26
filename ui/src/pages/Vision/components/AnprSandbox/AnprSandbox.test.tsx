import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockApi, ok, renderWithProviders } from '@/test/utils';
import { AnprSandbox } from './AnprSandbox';

describe('AnprSandbox Component', () => {
  it('renders introduction banner, presets, dropzone and anti-fraud matcher', () => {
    renderWithProviders(<AnprSandbox />);

    expect(screen.getByText('Computer Vision Studio · Pipeline 1')).toBeTruthy();
    expect(screen.getByText(/Automatic Number Plate Recognition/)).toBeTruthy();
    expect(screen.getByText('Mẫu Ô Tô (51A-888.88)')).toBeTruthy();
    expect(screen.getByText('Mẫu Xe Máy (29-B1 999.99)')).toBeTruthy();
    expect(screen.getByText('Tải ảnh xe vào bãi')).toBeTruthy();
    expect(screen.getByText(/Đối Chiếu Loại Xe Check-in vs Check-out/)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Thực Hiện Nhận Diện/ })).toHaveProperty('disabled', true);
  });

  it('clicking car sample preset button loads plate and enables Run ANPR button', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);

    const carPresetBtn = screen.getByText('Mẫu Ô Tô (51A-888.88)');
    await user.click(carPresetBtn);

    await waitFor(() => {
      const runBtn = screen.getByRole('button', { name: /Thực Hiện Nhận Diện/ });
      expect(runBtn).toHaveProperty('disabled', false);
    });
  });

  // ai bug-018: route thật /tools/anpr/recognize, /tools/vision/verify-match; lỗi thì báo lỗi, không bịa.
  it('Run ANPR: API 404 thì báo lỗi, không hiện biển của preset hay confidence 98.5%', async () => {
    mockApi(() => undefined);
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);

    await user.click(screen.getByText('Mẫu Ô Tô (51A-888.88)'));
    await user.click(screen.getByRole('button', { name: /Thực Hiện Nhận Diện/ }));

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByText('Độ tin cậy:')).toBeNull();
    expect(screen.queryByText(/98[.,]5%|97[.,]8%/)).toBeNull();
    expect(screen.queryByText('Sedan')).toBeNull();
  });

  it('Run ANPR: hiện đúng kết quả server, trường thiếu thì "—"', async () => {
    const calls = mockApi((url) => (url.endsWith('/tools/anpr/recognize') ? ok({ plate_number: '30K-111.22' }) : undefined));
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);
    await user.click(screen.getByText('Mẫu Ô Tô (51A-888.88)'));
    await user.click(screen.getByRole('button', { name: /Thực Hiện Nhận Diện/ }));

    await waitFor(() => expect(screen.getByText('30K-111.22')).toBeTruthy());
    expect(calls.some((c) => c.url === '/api/tools/anpr/recognize')).toBe(true);
    expect(screen.getByText('Độ tin cậy:').nextElementSibling?.textContent).toBe('—');
  });

  it('Đối chiếu loại xe: API 404 thì báo lỗi, không tự kết luận gian lận hay độ tương đồng', async () => {
    mockApi(() => undefined);
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);
    await user.click(screen.getByRole('button', { name: 'Thực Hiện Đối Chiếu Loại Xe' }));

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByText(/CẢNH BÁO GIAN LẬN/)).toBeNull();
    expect(screen.queryByText(/12[.,]4%|98[.,]5%/)).toBeNull();
  });

  it('Đối chiếu loại xe: hiện kết luận server trả', async () => {
    mockApi((url) =>
      url.endsWith('/tools/vision/verify-match')
        ? ok({ is_matched: false, similarity_score: 0.31, mismatch_reason: 'TYPE_MISMATCH' })
        : undefined,
    );
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);
    await user.click(screen.getByRole('button', { name: 'Thực Hiện Đối Chiếu Loại Xe' }));

    await waitFor(() => expect(screen.getByText(/CẢNH BÁO GIAN LẬN: LỆCH LOẠI PHƯƠNG TIỆN \(TYPE_MISMATCH\)/)).toBeTruthy());
    expect(screen.getByText(/Độ tương đồng: 31[.,]0%/)).toBeTruthy();
  });

  it('Đối chiếu loại xe: chỉ gửi hai loại xe, server chưa so ảnh thì độ tương đồng là "—"', async () => {
    const calls = mockApi((url) =>
      url.endsWith('/tools/vision/verify-match')
        ? ok({ is_matched: true, similarity_score: null, mismatch_reason: 'OK' })
        : undefined,
    );
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);
    await user.click(screen.getByRole('button', { name: 'Thực Hiện Đối Chiếu Loại Xe' }));

    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/tools/vision/verify-match'))).toBe(true));
    const body = JSON.parse(String(calls.find((c) => c.url.endsWith('/verify-match'))?.init?.body));
    expect(Object.keys(body).sort()).toEqual(['current_vehicle_type', 'expected_vehicle_type']);
    expect(screen.queryByText(/Độ tương đồng: \d/)).toBeNull();
  });
});
