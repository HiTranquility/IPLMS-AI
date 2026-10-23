import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/utils';
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

  it('clicking Run ANPR executes recognition and displays plate result details', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);

    const carPresetBtn = screen.getByText('Mẫu Ô Tô (51A-888.88)');
    await user.click(carPresetBtn);

    const runBtn = screen.getByRole('button', { name: /Thực Hiện Nhận Diện/ });
    await user.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText('51A-888.88')).toBeTruthy();
      expect(screen.getByText('Độ tin cậy:')).toBeTruthy();
      expect(screen.getByText('Trắng (Dân sự)')).toBeTruthy();
      expect(screen.getByText('Sedan')).toBeTruthy();
    });
  });

  it('detects vehicle mismatch and displays red fraud warning alert', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);

    const verifyBtn = screen.getByRole('button', { name: 'Thực Hiện Đối Chiếu Loại Xe' });
    await user.click(verifyBtn);

    await waitFor(() => {
      expect(screen.getByText(/CẢNH BÁO GIAN LẬN: LỆCH LOẠI PHƯƠNG TIỆN/)).toBeTruthy();
      expect(screen.getByText(/KHÓA CHẶT/)).toBeTruthy();
    });
  });

  it('selecting matching vehicle types verifies valid checkout and allows barricade pass', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AnprSandbox />);

    const validScenarioBtn = screen.getByText(/Kịch bản 2: Hợp lệ SUV/);
    await user.click(validScenarioBtn);

    const verifyBtn = screen.getByRole('button', { name: 'Thực Hiện Đối Chiếu Loại Xe' });
    await user.click(verifyBtn);

    await waitFor(() => {
      expect(screen.getByText(/HỢP LỆ — ĐỒNG NHẤT LOẠI XE/)).toBeTruthy();
      expect(screen.getByText(/Barie tự động mở/)).toBeTruthy();
      expect(screen.getByText(/MỞ CHO QUA/)).toBeTruthy();
    });
  });
});
