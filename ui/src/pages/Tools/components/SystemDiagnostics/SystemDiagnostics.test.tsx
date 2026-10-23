import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockApi, ok, renderWithProviders } from '@/test/utils';
import { SystemDiagnostics } from './SystemDiagnostics';

const systemData = {
  checks: [{ key: 'llm_key', label: 'LLM Key', ok: true }],
  llm_model: 'gpt-4o',
  telemetry_enabled: true,
  vision_device: 'cpu',
  telemetry_retention_days: 30,
  vision_retention_days: 90,
};

describe('SystemDiagnostics Component', () => {
  it('renders all three engine inspection cards with correct status and metadata', () => {
    mockApi((url) => {
      if (url.endsWith('/tools/system')) return ok(systemData);
      return undefined;
    });

    renderWithProviders(<SystemDiagnostics />);

    // YOLO Card
    expect(screen.getByText('YOLO Plate Detector')).toBeTruthy();
    expect(screen.getByText('model/artifacts/bootstrap/anpr/best.pt')).toBeTruthy();
    expect(screen.getByText('14.2 MB')).toBeTruthy();
    expect(screen.getByText('READY')).toBeTruthy();

    // EasyOCR Card
    expect(screen.getByText('EasyOCR Character Reader')).toBeTruthy();
    expect(screen.getByText('["en","vi"]')).toBeTruthy();
    expect(screen.getByText('var/easyocr-cache/')).toBeTruthy();
    expect(screen.getByText('CACHED')).toBeTruthy();

    // PyTorch & Hardware Card
    expect(screen.getByText(/PyTorch & Phần cứng/i)).toBeTruthy();
    expect(screen.getByText('2.6.0')).toBeTruthy();
    expect(screen.getByText('CPU')).toBeTruthy();
    expect(screen.getByText('STANDARD')).toBeTruthy();
  });

  it('renders 4 architectural conventions conforming to ADRs', () => {
    renderWithProviders(<SystemDiagnostics />);

    expect(screen.getByText(/1\. Phụ Thuộc 1 Chiều/i)).toBeTruthy();
    expect(screen.getByText(/2\. Hai Cổng Vào, Một Đường Nghiệp Vụ/i)).toBeTruthy();
    expect(screen.getByText(/3\. Thà Lỗi Hơn Bịa/i)).toBeTruthy();
    expect(screen.getByText(/4\. Lazy-Load Model Nặng/i)).toBeTruthy();
  });

  it('handles refresh button click without crashing', () => {
    renderWithProviders(<SystemDiagnostics />);
    const refreshBtn = screen.getByRole('button', { name: /Làm mới/i });
    expect(refreshBtn).toBeTruthy();
    fireEvent.click(refreshBtn);
  });
});
