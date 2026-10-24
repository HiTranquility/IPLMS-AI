import { en } from '@/i18n/en';
import { vi } from '@/i18n/vi';
import { actionLabel, AUDIT_CODES, getActionMeta } from './AuditActionBadge';

describe('AuditActionBadge — từ điển mã hành động (bug-020)', () => {
  it('mọi mã đã khai đều có nhóm thật và nhãn ở cả VI lẫn EN', () => {
    expect(AUDIT_CODES.length).toBeGreaterThan(0);
    for (const code of AUDIT_CODES) {
      expect(getActionMeta(code).category).not.toBe('other');
      expect(vi.audit.actions[code], `vi thiếu ${code}`).toBeTruthy();
      expect(en.audit.actions[code], `en thiếu ${code}`).toBeTruthy();
    }
  });

  it('khớp theo tiền tố trước dấu hai chấm và giữ phần chi tiết', () => {
    const meta = getActionMeta('role.grant:ai_annotator');
    expect(meta.code).toBe('role.grant');
    expect(meta.category).toBe('rbac');
    expect(actionLabel('role.grant:ai_annotator', en)).toBe('Role granted · ai_annotator');
    expect(actionLabel('role.grant:ai_annotator', vi)).toBe('Cấp vai trò · ai_annotator');
  });

  it('khoá golden và tạo snapshot nằm trong nhóm MLOps', () => {
    expect(getActionMeta('snapshot.freeze').category).toBe('ml');
    expect(getActionMeta('snapshot.create:golden').category).toBe('ml');
  });

  it('mã lạ hiện nguyên mã, không bị giấu', () => {
    expect(getActionMeta('unknown.thing').category).toBe('other');
    expect(actionLabel('unknown.thing', vi)).toBe('unknown.thing');
  });
});
