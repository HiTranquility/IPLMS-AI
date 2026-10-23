import { screen, waitFor } from '@testing-library/react';
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

  it('toggles inspector drawer and renders all 5 tabs', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);

    const inspectorToggle = screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' });
    await user.click(inspectorToggle);

    expect(screen.getByText('Trích dẫn RAG')).toBeTruthy();
    expect(screen.getByText('Kho tri thức')).toBeTruthy();
    expect(screen.getByText('Mô phỏng phân xử')).toBeTruthy();
    expect(screen.getByText('Chỉ số thực thi')).toBeTruthy();
    expect(screen.getByText('Tham số thử nghiệm')).toBeTruthy();
  });

  it('switches to Knowledge tab, displays seed documents, and filters by category', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);

    // Mở drawer
    await user.click(screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' }));

    // Click tab Kho tri thức
    await user.click(screen.getByText('Kho tri thức'));

    expect(screen.getByText('Kho Tri Thức Quy Chế')).toBeTruthy();
    expect(screen.getByPlaceholderText(/Tìm kiếm quy chế/)).toBeTruthy();

    // Verify seed document rendered
    expect(screen.getByText(/Biểu Phí Gửi Xe Ô Tô Bậc Thang/)).toBeTruthy();
    expect(screen.getByText(/Quy Chế Xử Lý Tranh Chấp & Hoàn Tiền Khiếu Nại/)).toBeTruthy();

    // Lọc theo "Trạm sạc EV"
    const evPill = screen.getByRole('button', { name: /Trạm sạc EV/ });
    await user.click(evPill);

    expect(screen.getByText(/Chính Sách Trạm Sạc Xe Điện/)).toBeTruthy();
  });

  it('switches to Dispute Simulator tab and executes LangGraph 5-node journey', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);

    // Mở drawer
    await user.click(screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' }));

    // Click tab Mô phỏng phân xử
    await user.click(screen.getByText('Mô phỏng phân xử'));

    expect(screen.getByText('Phân Xử Tranh Chấp (LangGraph)')).toBeTruthy();
    expect(screen.getByLabelText(/Mã khiếu nại/)).toBeTruthy();

    // Click nút chạy mô phỏng
    const runBtn = screen.getByRole('button', { name: /Chạy Mô Phỏng LangGraph/ });
    await user.click(runBtn);

    // Chờ 5 node xuất hiện
    await waitFor(
      () => {
        expect(screen.getByText(/validate_ticket/)).toBeTruthy();
        expect(screen.getByText(/verify_snapshots/)).toBeTruthy();
        expect(screen.getByText(/assess_claim/)).toBeTruthy();
        expect(screen.getByText(/supervisor_approval/)).toBeTruthy();
        expect(screen.getByText(/finalize_dispute/)).toBeTruthy();
      },
      { timeout: 3500 },
    );

    // Verify Bounded Autonomy rule notice
    expect(screen.getByText(/Nguyên tắc Bounded Autonomy/)).toBeTruthy();
    expect(screen.getByText(/5\/5 Nodes Traversed/)).toBeTruthy();
  });

  it('switches to Params tab and applies smart Model Profile presets', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);

    // Mở drawer
    await user.click(screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' }));

    // Click tab Tham số thử nghiệm
    await user.click(screen.getByText('Tham số thử nghiệm'));

    expect(screen.getByText(/Gợi ý cấu hình Model/)).toBeTruthy();
    expect(screen.getByText('Gemma 2B')).toBeTruthy();
    expect(screen.getByText('Llama 3 8B')).toBeTruthy();
    expect(screen.getByText('Qwen 2.5 7B')).toBeTruthy();

    // Click profile Llama 3 8B
    const llamaBtn = screen.getByText('Llama 3 8B').closest('button');
    expect(llamaBtn).toBeTruthy();
    await user.click(llamaBtn!);

    // Temperature slider updates to 0.20
    expect(screen.getByText('0.20')).toBeTruthy();
    // Header model badge updates
    expect(screen.getByText(/Llama 3 8B \(llama3:8b\)/)).toBeTruthy();
  });
});
