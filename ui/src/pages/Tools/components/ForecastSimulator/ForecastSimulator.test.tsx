import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { mockApi, ok, renderWithProviders } from '@/test/utils';
import { ForecastSimulator } from './ForecastSimulator';

describe('ForecastSimulator Component', () => {
  afterEach(() => vi.restoreAllMocks());

  it('lists lots from the Gold lake and runs the pipeline on that area_key (ai bug-028)', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/tools/forecast/areas')) {
        return ok({ source_path: 'gold/occupancy', areas: [{ area_id: 'area-zone-a', records: 24 }] });
      }
      return undefined;
    });
    renderWithProviders(<ForecastSimulator />);

    const select = (await screen.findByRole('option', { name: 'area-zone-a · 24 bản ghi' })).closest('select');
    expect(select).toBeTruthy();
    expect((select as HTMLSelectElement).value).toBe('area-zone-a');
    expect(screen.queryByRole('option', { name: /Landmark 81/i })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /Chạy Pipeline 3/i }));
    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/tools/forecast/simulate'))).toBe(true));
    const sim = calls.find((c) => c.url.endsWith('/tools/forecast/simulate'));
    expect(JSON.parse(String(sim?.init?.body)).area_id).toBe('area-zone-a');
  });

  it('cannot run the pipeline while the lake has no lot', async () => {
    mockApi((url) =>
      url.endsWith('/tools/forecast/areas') ? ok({ source_path: 'gold/occupancy', areas: [] }) : undefined,
    );
    renderWithProviders(<ForecastSimulator />);
    expect(await screen.findByRole('option', { name: 'Gold lake chưa có bãi nào' })).toBeTruthy();
    expect((screen.getByRole('button', { name: /Chạy Pipeline 3/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('renders simulation parameters and initial KPI values', () => {
    renderWithProviders(<ForecastSimulator />);

    // Controls
    expect(screen.getByText('Tham Số Mô Phỏng Bãi Đỗ')).toBeTruthy();
    expect(screen.getByLabelText('Chọn Bãi Xe')).toBeTruthy();
    expect(screen.getByText(/250 chỗ/i)).toBeTruthy();
    expect(screen.getByText(/35.000 đ\/h/i)).toBeTruthy();
    expect(screen.getAllByText('85%').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('1.30x')).toBeTruthy();

    // KPIs
    expect(screen.getByText('Khung Giờ Cao Điểm (> ngưỡng)')).toBeTruthy();
    expect(screen.getByText('Mức Giá Cao Điểm Đề Xuất')).toBeTruthy();
    expect(screen.getByText('Ước Tính Biến Động Doanh Thu')).toBeTruthy();
    expect(screen.getByText(/45[.,]500/)).toBeTruthy();
  });

  it('renders 24h occupancy SVG chart without CDN Chart.js dependency', () => {
    const { container } = renderWithProviders(<ForecastSimulator />);

    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    expect(screen.getByText('Kịch bản minh hoạ')).toBeTruthy();
    expect(screen.getByText('0h')).toBeTruthy();
    expect(screen.getByText('12h')).toBeTruthy();
    expect(screen.getByText('23h')).toBeTruthy();
  });

  it('opens and closes the API safety gate modal on button click', () => {
    renderWithProviders(<ForecastSimulator />);

    const testApiBtn = screen.getByRole('button', { name: /Kiểm Tra API Thực/i });
    expect(testApiBtn).toBeTruthy();

    // Modal is initially closed
    expect(screen.queryByText(/HTTP 501 \/ FeatureNotImplementedError/i)).toBeNull();

    // Open modal
    fireEvent.click(testApiBtn);
    expect(screen.getByText(/HTTP 501 \/ FeatureNotImplementedError/i)).toBeTruthy();
    expect(screen.getByText(/Kiểm tra Gate An Toàn API/i)).toBeTruthy();

    // Close modal
    const closeBtn = screen.getByRole('button', { name: /Đóng/i });
    fireEvent.click(closeBtn);
    expect(screen.queryByText(/HTTP 501 \/ FeatureNotImplementedError/i)).toBeNull();
  });

  it('updates slider values and recalculates KPIs dynamically', () => {
    renderWithProviders(<ForecastSimulator />);

    const thresholdInput = screen.getByLabelText('Ngưỡng quá tải (Surge Threshold)');
    fireEvent.change(thresholdInput, { target: { value: '90' } });

    expect(screen.getAllByText('90%').length).toBeGreaterThanOrEqual(1);
  });

  // ai bug-018: không có model doanh thu → "—", không dùng hệ số 2.28 tự đặt; nhãn MÔ PHỎNG luôn hiện.
  it('gắn nhãn MÔ PHỎNG và không bịa biến động doanh thu', () => {
    renderWithProviders(<ForecastSimulator />);
    expect(screen.getByText('MÔ PHỎNG')).toBeTruthy();
    expect(screen.getByText('chưa có mô hình doanh thu')).toBeTruthy();
    expect(screen.queryByText(/^\+\d+[.,]\d%$/)).toBeNull();
  });
});
