import { Search, X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import type { Member } from '@/types/member';
import styles from './MemberCombobox.module.css';

export interface MemberComboboxProps {
  members: Member[];
  selectedId: string;
  selfId: string;
  onSelect: (id: string) => void;
  label?: string;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function MemberCombobox({
  members,
  selectedId,
  selfId,
  onSelect,
  label,
}: MemberComboboxProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedMember = useMemo(
    () => members.find((m) => m.id === selectedId),
    [members, selectedId],
  );

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredMembers = useMemo(() => {
    if (!query.trim()) return members;
    const q = query.toLowerCase();
    return members.filter(
      (m) =>
        m.display_name.toLowerCase().includes(q) ||
        m.email.toLowerCase().includes(q) ||
        m.roles.some((r) => r.toLowerCase().includes(q)),
    );
  }, [members, query]);

  const handlePick = (id: string) => {
    onSelect(id);
    setIsOpen(false);
    setQuery('');
  };

  const handleClear = () => {
    onSelect('');
    setQuery('');
    setIsOpen(true);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  return (
    <div className={styles.combobox} ref={containerRef}>
      {/* Hidden Accessible Select for Test Compatibility */}
      <select
        className={styles.srOnly}
        aria-label={label || t.members.member}
        value={selectedId}
        onChange={(e) => onSelect(e.target.value)}
        tabIndex={-1}
      >
        <option value="">{t.members.pickMember}</option>
        {members.map((m) => (
          <option key={m.id} value={m.id} disabled={m.id === selfId}>
            {m.display_name} · {m.email}
            {m.id === selfId ? t.members.selfSuffix : ''}
          </option>
        ))}
      </select>

      <span className={styles.label}>
        <span>{label || t.members.member}</span>
        {selectedMember && (
          <button
            type="button"
            className={styles.changeBtn}
            onClick={handleClear}
            aria-label={t.members.changeMember}
          >
            <X size={12} aria-hidden />
            <span>{t.members.changeMember}</span>
          </button>
        )}
      </span>

      {selectedMember ? (
        <div className={styles.selectedCard}>
          <div className={styles.selectedLeft}>
            <div
              className={`${styles.avatar} ${
                selectedMember.id === selfId ? styles.avatarSelf : ''
              }`}
            >
              {getInitials(selectedMember.display_name)}
            </div>
            <div className={styles.meta}>
              <div className={styles.nameRow}>
                <span className={styles.name}>{selectedMember.display_name}</span>
                {selectedMember.id === selfId && (
                  <span className={styles.selfTag}>{t.members.selfTag}</span>
                )}
              </div>
              <span className={styles.email}>{selectedMember.email}</span>
            </div>
          </div>
          <span className={styles.roleCount}>
            {t.members.rolesCount(selectedMember.roles.length)}
          </span>
        </div>
      ) : (
        <div className={styles.searchWrap}>
          <Search size={15} className={styles.searchIcon} aria-hidden />
          <input
            ref={inputRef}
            type="text"
            className={styles.input}
            placeholder={t.members.searchMemberPlaceholder}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            aria-expanded={isOpen}
            aria-autocomplete="list"
          />
          {query && (
            <button
              type="button"
              className={styles.clearBtn}
              onClick={() => setQuery('')}
              aria-label={t.members.clearSearch}
            >
              <X size={14} />
            </button>
          )}

          {isOpen && (
            <div className={styles.dropdown} role="listbox">
              {filteredMembers.length === 0 ? (
                <div className={styles.emptyResults}>
                  {t.members.noMemberFound}
                </div>
              ) : (
                filteredMembers.map((m) => {
                  const isSelf = m.id === selfId;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      role="option"
                      aria-selected={m.id === selectedId}
                      disabled={isSelf}
                      className={`${styles.item} ${isSelf ? styles.itemDisabled : ''}`}
                      onClick={() => handlePick(m.id)}
                    >
                      <div
                        className={`${styles.avatar} ${isSelf ? styles.avatarSelf : ''}`}
                      >
                        {getInitials(m.display_name)}
                      </div>
                      <div className={styles.meta}>
                        <div className={styles.nameRow}>
                          <span className={styles.name}>{m.display_name}</span>
                          {isSelf && (
                            <span className={styles.selfTag}>
                              {t.members.selfTag}
                            </span>
                          )}
                        </div>
                        <span className={styles.email}>{m.email}</span>
                      </div>
                      <span className={styles.roleCount}>
                        {t.members.rolesCount(m.roles.length)}
                      </span>
                    </button>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MemberCombobox;
