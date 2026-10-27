import { useSyncExternalStore } from 'react';
import type { WorkspacePersona } from '@/types/workspace';

// Lưu theo từng tài khoản: dùng chung một khoá thì tài khoản sau thừa hưởng không gian
// của tài khoản trước trên cùng trình duyệt và bị ẩn menu (ai bug-041).
const STORAGE_KEY = 'iplms_active_workspace';
const PERSONAS: WorkspacePersona[] = ['all', 'admin', 'ml', 'labeling', 'analytics'];

const byMember = new Map<string, WorkspacePersona | null>();
const listeners = new Set<() => void>();

const keyFor = (memberId: string) => `${STORAGE_KEY}:${memberId}`;

function read(memberId: string): WorkspacePersona | null {
  if (byMember.has(memberId)) return byMember.get(memberId) ?? null;
  let saved: WorkspacePersona | null = null;
  try {
    const raw = localStorage.getItem(keyFor(memberId)) as WorkspacePersona | null;
    saved = raw && PERSONAS.includes(raw) ? raw : null;
  } catch {
    saved = null;
  }
  byMember.set(memberId, saved);
  return saved;
}

export function setPersona(next: WorkspacePersona, memberId: string) {
  byMember.set(memberId, next);
  try {
    localStorage.setItem(keyFor(memberId), next);
  } catch {
    // Không lưu được (chế độ riêng tư…) thì vẫn đổi trong phiên này.
  }
  listeners.forEach((listener) => listener());
}

/** Không gian đã chọn của tài khoản này; `null` khi chưa chọn lần nào. */
export function useWorkspaceStore(memberId: string) {
  const persona = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => read(memberId),
    () => null,
  );

  return {
    persona,
    setPersona: (next: WorkspacePersona) => setPersona(next, memberId),
  };
}
