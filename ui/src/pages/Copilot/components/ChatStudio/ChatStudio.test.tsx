import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/utils';
import { ChatStudio } from './ChatStudio';

describe('ChatStudio Component', () => {
  it('renders welcome hero and preset questions on initial load', () => {
    renderWithProviders(<ChatStudio />);

    expect(screen.getByText('Copilot Chat Studio')).toBeTruthy();
    expect(screen.getByText('Câu hỏi mẫu quy chế')).toBeTruthy();
    expect(screen.getAllByText('Biểu phí giữ xe máy qua đêm và ngày lễ').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('button', { name: 'Gửi' })).toHaveProperty('disabled', true);
  });

  it('clicking a preset card fills the question into chat textarea and enables send button', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);

    const presetBtns = screen.getAllByText('Biểu phí giữ xe máy qua đêm và ngày lễ');
    await user.click(presetBtns[0]);

    const textarea = screen.getByRole('textbox', { name: /Nhập câu hỏi quy chế/ });
    expect((textarea as HTMLTextAreaElement).value).toContain('Biểu phí gửi xe máy');
    expect(screen.getByRole('button', { name: 'Gửi' })).toHaveProperty('disabled', false);
  });

  it('toggles inspector drawer when clicking header toggle button', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);

    const inspectorToggle = screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' });
    await user.click(inspectorToggle);

    expect(screen.getByText('Chỉ số thực thi')).toBeTruthy();
    expect(screen.getByText('Tham số thử nghiệm')).toBeTruthy();
  });
});
