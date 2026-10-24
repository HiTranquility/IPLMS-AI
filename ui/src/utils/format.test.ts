import { afterEach, describe, expect, it } from 'vitest';
import { fmtDayMonth } from './format';
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
