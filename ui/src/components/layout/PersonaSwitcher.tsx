import { ChevronDown } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useI18n } from '@/i18n/I18nProvider';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import type { Me } from '@/types/auth';
import type { WorkspacePersona } from '@/types/workspace';
import { allowed, getAvailablePersonas, NAV_ITEMS, PERSONA_LIST } from './navigation';
import styles from './PersonaSwitcher.module.css';

export interface PersonaSwitcherProps {
  me: Me;
  collapsed?: boolean;
}

export function PersonaSwitcher({ me, collapsed = false }: PersonaSwitcherProps) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const { persona, setPersona } = useWorkspaceStore();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const availableIds = useMemo(() => getAvailablePersonas(me), [me]);
  const availableList = useMemo(
    () => PERSONA_LIST.filter((p) => availableIds.includes(p.id)),
    [availableIds],
  );

  const activeId = availableIds.includes(persona) ? persona : availableIds[0];
  const activeMeta = PERSONA_LIST.find((p) => p.id === activeId) || PERSONA_LIST[0];
  const ActiveIcon = activeMeta.icon;

  const handleSelect = (targetId: WorkspacePersona) => {
    setPersona(targetId);
    setOpen(false);
    const targetMeta = PERSONA_LIST.find((p) => p.id === targetId);
    if (!targetMeta) return;

    const currentPath = location.pathname;
    const isCurrentAllowed = NAV_ITEMS.some(
      (item) => item.to === currentPath && allowed(item, me.permissions, targetId),
    );
    if (!isCurrentAllowed && targetId !== 'all') {
      navigate(targetMeta.defaultPath);
    }
  };

  return (
    <div ref={wrapRef} className={`${styles.wrap} ${collapsed ? styles.wrapCollapsed : ''}`}>
      {availableList.length > 1 ? (
        <>
          <button
            type="button"
            className={`${styles.selectorButton} ${collapsed ? styles.selectorButtonCollapsed : ''}`}
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            aria-label={t.workspace.switchPrompt}
            title={`${t.workspace.switchPrompt}: ${t.workspace[activeMeta.titleKey]}`}
          >
            <div className={styles.currentInfo}>
              <ActiveIcon size={15} className={styles.currentIcon} aria-hidden />
              {!collapsed && (
                <div className={styles.currentText}>
                  <span className={styles.currentLabel}>{t.workspace[activeMeta.titleKey]}</span>
                  <span className={styles.currentBadge}>{activeMeta.badge}</span>
                </div>
              )}
            </div>
            {!collapsed && (
              <ChevronDown size={13} className={`${styles.chevron} ${open ? styles.chevronOpen : ''}`} aria-hidden />
            )}
          </button>

          {open && (
            <div className={styles.dropdown} role="menu">
                <div className={styles.dropdownHeader}>{t.workspace.title}</div>
                {availableList.map((item) => {
                  const ItemIcon = item.icon;
                  const isCurrent = item.id === persona;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      role="menuitem"
                      className={`${styles.menuItem} ${isCurrent ? styles.menuItemActive : ''}`}
                      onClick={() => handleSelect(item.id)}
                    >
                      <ItemIcon size={15} className={styles.menuItemIcon} aria-hidden />
                      <div className={styles.menuItemContent}>
                        <span className={styles.menuItemTitle}>
                          {t.workspace[item.titleKey]}
                          {isCurrent && ' ✓'}
                        </span>
                        <span className={styles.menuItemDesc}>{t.workspace[item.descKey]}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
          )}
        </>
      ) : (
        <div
          className={`${styles.singleBadge} ${collapsed ? styles.singleBadgeCollapsed : ''}`}
          title={t.workspace[activeMeta.titleKey]}
        >
          <ActiveIcon size={14} className={styles.singleBadgeIcon} aria-hidden />
          {!collapsed && <span>{t.workspace[activeMeta.titleKey]}</span>}
        </div>
      )}
    </div>
  );
}

export default PersonaSwitcher;
