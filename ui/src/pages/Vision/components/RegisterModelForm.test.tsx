import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/utils';
import { RegisterModelForm } from './RegisterModelForm';

// ai bug-018: không còn preset model bịa, "Kiểm tra" chỉ kiểm định dạng và nói rõ như vậy.
describe('RegisterModelForm', () => {
  it('không có preset model bịa (s3:// giả, độ chính xác 99.2%)', () => {
    renderWithProviders(<RegisterModelForm />);
    expect(screen.queryByRole('combobox')).toBeNull();
    expect(screen.queryByText(/99\.2%|12ms|resnet18-ctc/)).toBeNull();
  });

  it('kiểm định dạng cục bộ, không báo "Endpoint phản hồi 16ms"', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RegisterModelForm />);
    const check = screen.getByRole('button', { name: /Kiểm tra định dạng/ });

    await user.click(check);
    expect(screen.getByText('artifact_key không được để trống.')).toBeTruthy();

    fireEvent.change(screen.getByLabelText(/artifact_key/), { target: { value: 'models/anpr/1.2.0.pt' } });
    fireEvent.change(screen.getByLabelText(/sha256 weights/), { target: { value: 'ab'.repeat(32) } });
    await user.click(check);
    expect(screen.getByText(/Định dạng hợp lệ\. Chỉ kiểm cục bộ/)).toBeTruthy();
    expect(screen.queryByText(/16ms/)).toBeNull();
  });
});
