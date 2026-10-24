import { afterEach, describe, expect, it } from 'vitest';
import { fmtDateTime, fmtDayMonth } from './format';
import { applyLang } from './lang';

describe('fmtDayMonth', () => {
  afterEach(() => applyLang('vi'));

  it('chỉ có ngày/tháng, không có thứ (bug-021)', () => {
    applyLang('vi');
    expect(fmtDayMonth('2026-10-11')).toBe('11/10');
    applyLang('en');
    expect(fmtDayMonth('2026-10-11')).toBe('10/11');
  });
});

describe('fmtDateTime', () => {
  afterEach(() => applyLang('vi'));

  it('ngày trước giờ, không có giây, theo giờ Việt Nam (ISSUE-005)', () => {
    applyLang('vi');
    expect(fmtDateTime('2026-10-20T00:15:30Z')).toBe('20/10/26 07:15');
    applyLang('en');
    expect(fmtDateTime('2026-10-20T00:15:30Z')).toBe('10/20/26 07:15');
  });
});
