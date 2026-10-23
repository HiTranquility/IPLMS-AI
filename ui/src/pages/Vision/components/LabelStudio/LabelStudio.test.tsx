import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/utils';
import {
  LabelEmptyStudio,
  LabelHistoryDrawer,
  LabelMetricsStrip,
  LabelShortcutsBar,
  type HistoryItem,
} from './index';

describe('LabelMetricsStrip', () => {
  it('renders queue count, session count and velocity accurately', () => {
    renderWithProviders(
      <LabelMetricsStrip
        queueCount={5}
        sessionCount={2}
        avgVelocitySeconds={12}
        onRefresh={() => {}}
        isRefreshing={false}
      />,
    );

    expect(screen.getByText('5')).toBeTruthy();
    expect(screen.getByText('2')).toBeTruthy();
    expect(screen.getByText('~12s')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Nạp 5 mẫu thực hành/i })).toBeTruthy();
  });
});

describe('LabelEmptyStudio', () => {
  it('renders all 5 demo plate previews and guidelines', () => {
    renderWithProviders(<LabelEmptyStudio onSeeded={() => {}} />);

    expect(screen.getByText('51A-888.88')).toBeTruthy();
    expect(screen.getAllByText('29-B1 999.99').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('30E-123.45')).toBeTruthy();
    expect(screen.getByText('60-A 888.88')).toBeTruthy();
    expect(screen.getByText('43A-567.89')).toBeTruthy();
    expect(screen.getByText(/Quy chuẩn gán nhãn biển số/i)).toBeTruthy();
  });
});

describe('LabelShortcutsBar', () => {
  it('renders keyboard shortcuts legend bar', () => {
    renderWithProviders(<LabelShortcutsBar />);

    expect(screen.getByText('Xác nhận đúng')).toBeTruthy();
    expect(screen.getByText('Sửa biển số')).toBeTruthy();
    expect(screen.getByText('Ảnh hỏng')).toBeTruthy();
  });
});

describe('LabelHistoryDrawer', () => {
  it('renders empty history message when items array is empty', () => {
    renderWithProviders(<LabelHistoryDrawer items={[]} />);
    expect(screen.getByText(/Chưa có mẫu nào được gán nhãn trong phiên/i)).toBeTruthy();
  });

  it('renders history items with plate and verdict badges', () => {
    const items: HistoryItem[] = [
      {
        captureId: 'sample-1',
        plateText: '51A-888.88',
        verdict: 'CORRECT',
        timestamp: new Date(),
      },
      {
        captureId: 'sample-2',
        plateText: '29-B1 999.99',
        verdict: 'CORRECTED',
        timestamp: new Date(),
      },
    ];

    renderWithProviders(<LabelHistoryDrawer items={items} />);
    expect(screen.getByText('51A-888.88')).toBeTruthy();
    expect(screen.getByText('29-B1 999.99')).toBeTruthy();
    expect(screen.getByText('Đúng 100%')).toBeTruthy();
    expect(screen.getByText('Đã sửa')).toBeTruthy();
  });
});
