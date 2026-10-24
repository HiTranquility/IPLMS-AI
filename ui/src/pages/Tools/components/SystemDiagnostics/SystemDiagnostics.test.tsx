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
  // ai bug-018: server không gửi engines (bản cũ) → mọi ô engine là "—", không hằng số.
  it('chỉ hiện thiết bị server báo, các ô engine chưa báo là "—", không còn hằng số', async () => {
    mockApi((url) => (url.endsWith('/tools/system') ? ok(systemData) : undefined));
    renderWithProviders(<SystemDiagnostics />);

    expect(screen.getByText('YOLO Plate Detector')).toBeTruthy();
    expect(screen.getByText('EasyOCR Character Reader')).toBeTruthy();
    expect(await screen.findByText('CPU')).toBeTruthy();
    for (const fake of ['model/artifacts/bootstrap/anpr/best.pt', '14.2 MB', 'READY', 'CACHED', '2.6.0', 'STANDARD', '["en","vi"]']) {
      expect(screen.queryByText(fake)).toBeNull();
    }
    expect(screen.getAllByText('Máy chủ chưa báo').length).toBe(4); // 3 thẻ + trạng thái EasyOCR
  });

  it('hiện đúng trạng thái engine server báo (ai bug-018: số liệu thật)', async () => {
    const engines = {
      yolo_weights_path: 'model/x/best.pt', yolo_weights_bytes: 3 * 1024 * 1024, yolo_version: 'v9',
      yolo_loaded: true, ocr_languages: ['en', 'vi'], ocr_cache_dir: null, ocr_loaded: false,
      onnx_enabled: true, torch_version: '2.14.1', cuda_available: null,
    };
    mockApi((url) => (url.endsWith('/tools/system') ? ok({ ...systemData, engines }) : undefined));
    renderWithProviders(<SystemDiagnostics />);

    expect(await screen.findByText('model/x/best.pt')).toBeTruthy();
    expect(screen.getByText(/^3[.,]0 MB$/)).toBeTruthy();
    expect(screen.getByText('v9')).toBeTruthy();
    expect(screen.getByText('en, vi')).toBeTruthy();
    expect(screen.getByText('2.14.1')).toBeTruthy();
    expect(screen.getAllByText('Chưa nạp').length).toBeGreaterThan(0); // EasyOCR
    expect(screen.queryByText('Có')).toBeNull(); // CUDA không rõ → "—", không đoán
  });

  it('API lỗi thì báo lỗi và thiết bị là "—"', async () => {
    mockApi(() => ({ status: 500, body: { success: false, message: 'Hỏng', data: [], code: 'ERR' } }));
    renderWithProviders(<SystemDiagnostics />);
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.queryByText('CPU')).toBeNull();
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
