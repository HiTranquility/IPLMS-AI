import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockApi, ok, renderWithProviders } from '@/test/utils';
import { ASK_BODY_FIELDS } from './askContract';
import { ChatStudio } from './ChatStudio';

/** Giả fetch: /tools/copilot/stream trả `stream` (SSE thô) hoặc lỗi; route khác 404. */
function mockStream(stream: { status: number; body: string }) {
  const calls: { url: string; init?: RequestInit }[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    calls.push({ url, init });
    if (url.endsWith('/tools/copilot/stream')) return new Response(stream.body, { status: stream.status });
    return new Response(JSON.stringify({ success: false, message: 'no mock', data: [] }), { status: 404 });
  });
  return calls;
}

async function ask(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getAllByText('Biểu phí giữ xe máy qua đêm và ngày lễ')[0]);
  await user.click(screen.getByRole('button', { name: 'Gửi' }));
}

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

    expect(screen.getByText('Trích dẫn')).toBeTruthy();
    expect(screen.getByText('Kho tri thức')).toBeTruthy();
    expect(screen.getByText('Phân xử')).toBeTruthy();
    expect(screen.getByText('Chỉ số')).toBeTruthy();
    expect(screen.getByText('Tham số')).toBeTruthy();
  });

  // ai bug-018: danh sách lấy từ route thật /tools/knowledge/documents; lỗi thì báo lỗi, không hiện văn bản mẫu.
  it('Knowledge tab: API 404 thì báo lỗi, không hiện văn bản mẫu', async () => {
    mockApi(() => undefined);
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);
    await user.click(screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' }));
    await user.click(screen.getByText('Kho tri thức'));

    expect(screen.getByText('Kho Tri Thức Quy Chế')).toBeTruthy();
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByText(/Biểu Phí Gửi Xe Ô Tô Bậc Thang/)).toBeNull();
    expect(screen.queryByText(/pgvector: Sẵn sàng/)).toBeNull();
    expect(screen.getByText('0 văn bản')).toBeTruthy();
  });

  it('Knowledge tab: hiện đúng văn bản server trả và lọc theo nhóm', async () => {
    mockApi((url) =>
      url.endsWith('/tools/knowledge/documents')
        ? ok(
            { id: 'd1', category: 'tariff', title: 'Bảng giá thật', source: 'bang-gia.md', chunk_count: 4,
              latest_version_no: 2, latest_status: 'DRAFT', published_version_no: 1 },
            { id: 'd2', category: 'ev_charging', title: 'Trạm sạc thật', source: 'ev.md', chunk_count: 1,
              latest_version_no: 1, latest_status: 'PUBLISHED', published_version_no: 1 },
          )
        : undefined,
    );
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);
    await user.click(screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' }));
    await user.click(screen.getByText('Kho tri thức'));

    await waitFor(() => expect(screen.getByText('Bảng giá thật')).toBeTruthy());
    // Server chỉ trả metadata: thẻ hiện số đoạn/phiên bản thật, không có nội dung bịa.
    expect(screen.getByText(/4 đoạn · bản mới nhất v2 \(DRAFT\) · khách đang thấy v1/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: /Trạm sạc EV/ }));
    expect(screen.getByText('Trạm sạc thật')).toBeTruthy();
    expect(screen.queryByText('Bảng giá thật')).toBeNull();
  });

  it('Dispute tab: API 404 thì báo lỗi, không dựng 5 node, không có mã giao dịch giả', async () => {
    mockApi(() => undefined);
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);
    await user.click(screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' }));
    await user.click(screen.getByText('Phân xử'));

    expect(screen.getByText('Phân Xử Tranh Chấp (LangGraph)')).toBeTruthy();
    expect(screen.getByText('MÔ PHỎNG')).toBeTruthy();
    await user.click(screen.getByRole('button', { name: /Chạy Mô Phỏng LangGraph/ }));

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByText(/validate_ticket/)).toBeNull();
    expect(screen.queryByText(/finalize_dispute/)).toBeNull();
    expect(screen.queryByText(/RESOLVED_REFUNDED|TX-DSP|audit_log_hash/)).toBeNull();
  });

  it('Dispute tab: hiện đúng các bước server trả', async () => {
    mockApi((url) =>
      url.endsWith('/copilot/dispute-workflow/simulate')
        ? ok({
            success: true, dispute_id: 'DSP-9821', workflow: 'dispute', nodes_traversed: 2, final_status: 'REVIEW',
            steps: [
              { step: 1, node: 'load_evidence', status: 'COMPLETED', description: 'Nạp bằng chứng', data: {} },
              { step: 2, node: 'human_review', status: 'AWAITING_STAFF_SIGN_OFF', description: 'Chờ người duyệt', data: {} },
            ],
          })
        : undefined,
    );
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);
    await user.click(screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' }));
    await user.click(screen.getByText('Phân xử'));
    await user.click(screen.getByRole('button', { name: /Chạy Mô Phỏng LangGraph/ }));

    await waitFor(() => expect(screen.getByText(/load_evidence/)).toBeTruthy());
    expect(screen.getByText(/human_review/)).toBeTruthy();
    expect(screen.getByText('2 node đã đi qua')).toBeTruthy();
    expect(screen.queryByText(/validate_ticket/)).toBeNull();
  });

  it('switches to Params tab and applies smart Model Profile presets', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);

    // Mở drawer
    await user.click(screen.getByRole('button', { name: 'Mở ngăn kéo kiểm định' }));

    // Click tab Tham số thử nghiệm
    await user.click(screen.getByText('Tham số'));

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
    // Preset chỉ đổi tham số; tên model ở header vẫn là model server báo, không tự đổi (ai bug-018).
    expect(screen.queryByText(/Llama 3 8B \(llama3:8b\)/)).toBeNull();
  });

  // ai bug-017: body phải khớp AskIn (extra="forbid"); test Python cùng tên đối chiếu phía server.
  it('gửi đúng các trường của hợp đồng AskIn và hiện token SSE thật', async () => {
    const sse =
      'data: {"token": "Phí qua đêm ", "is_finished": false, "sources": []}\n\n' +
      'data: {"token": "30.000đ.", "is_finished": false, "sources": []}\n\n' +
      'data: {"token": "", "is_finished": true, "sources": ["bang-gia.md"], "confidence": 0.8, "refused": false, "prompt_version": "v2", "turn_id": "t-1", "latency_ms": 120}\n\n';
    const calls = mockStream({ status: 200, body: sse });
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);
    await ask(user);

    await waitFor(() => expect(screen.getByText(/Phí qua đêm 30\.000đ\./)).toBeTruthy());
    const call = calls.find((c) => c.url.endsWith('/tools/copilot/stream'))!;
    expect(call.url).toBe('/api/tools/copilot/stream');
    const body = JSON.parse(String(call.init?.body));
    expect(Object.keys(body).sort()).toEqual([...ASK_BODY_FIELDS].sort());
    expect(body.parking_lot_id).toBeNull();
    expect((call.init?.headers as Record<string, string>)['X-Console-Request']).toBe('1');
  });

  it('server trả 422 thì hiện lỗi thật, không có câu trả lời giả', async () => {
    mockStream({ status: 422, body: JSON.stringify({ detail: [{ type: 'extra_forbidden' }] }) });
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);
    await ask(user);

    await waitFor(() => expect(screen.getByText(/Không nhận được câu trả lời: Dữ liệu gửi lên chưa hợp lệ\./)).toBeTruthy());
    expect(screen.queryByText('Đã xử lý yêu cầu thành công.')).toBeNull();
  });

  it('thanh ngữ cảnh bãi xe cập nhật parking_lot_id trong hợp đồng gửi SSE', async () => {
    const sse =
      'data: {"token": "Đã nhận diện", "is_finished": false, "sources": []}\n\n' +
      'data: {"token": "", "is_finished": true, "sources": [], "confidence": 0.9, "turn_id": "t-lot"}\n\n';
    const calls = mockStream({ status: 200, body: sse });
    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);

    const lotSelect = screen.getByLabelText('Ngữ cảnh bãi xe');
    await user.selectOptions(lotSelect, 'lot_central_01');

    await user.click(screen.getAllByText('Biểu phí giữ xe máy qua đêm và ngày lễ')[0]);
    await user.click(screen.getByRole('button', { name: 'Gửi' }));

    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/tools/copilot/stream'))).toBe(true));
    const call = calls.find((c) => c.url.endsWith('/tools/copilot/stream'))!;
    const body = JSON.parse(String(call.init?.body));
    expect(body.parking_lot_id).toBe('lot_central_01');
  });

  it('nút thử lại (regenerate) gọi lại stream với câu hỏi trước đó', async () => {
    let streamCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/tools/copilot/stream')) {
        streamCount += 1;
        const sse = `data: {"token": "Lần ${streamCount}", "is_finished": true, "sources": [], "turn_id": "t-${streamCount}"}\n\n`;
        return new Response(sse, { status: 200 });
      }
      return new Response(JSON.stringify({ success: false }), { status: 404 });
    });

    const user = userEvent.setup();
    renderWithProviders(<ChatStudio />);
    await ask(user);

    await waitFor(() => expect(screen.getByText('Lần 1')).toBeTruthy());

    const regenBtn = screen.getByRole('button', { name: 'Thử lại câu trả lời' });
    await user.click(regenBtn);

    await waitFor(() => expect(screen.getByText('Lần 2')).toBeTruthy());
    expect(streamCount).toBe(2);
  });
});
