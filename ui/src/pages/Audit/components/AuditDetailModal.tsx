import { Check, Copy, X } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { useI18n } from '@/i18n/I18nProvider';
import type { AuditEntry } from '@/types/audit';
import type { Member } from '@/types/member';
import { fmtDateTime } from '@/utils/format';
import { AuditActionBadge } from './AuditActionBadge';
import styles from './AuditDetailModal.module.css';

export interface AuditDetailModalProps {
  entry: AuditEntry;
  members: Member[];
  onClose: () => void;
}

export function AuditDetailModal({ entry, members, onClose }: AuditDetailModalProps) {
  const { t } = useI18n();
  const [copiedId, setCopiedId] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);

  const actorMember = members.find((m) => m.id === entry.actor_id);
  const targetMember = entry.target_type === 'console_member'
    ? members.find((m) => m.id === entry.target_id)
    : null;

  const handleCopyId = () => {
    void navigator.clipboard.writeText(entry.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const jsonStr = JSON.stringify(entry, null, 2);

  const handleCopyJson = () => {
    void navigator.clipboard.writeText(jsonStr);
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  return (
    <div className={styles.backdrop} onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="detail-title">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h3 id="detail-title" className={styles.title}>{t.audit.eventDetailTitle}</h3>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label={t.audit.close}>
            <X size={16} aria-hidden />
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.grid}>
            <span className={styles.fieldLabel}>{t.audit.eventId}:</span>
            <div className={styles.fieldValue} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <code style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>{entry.id}</code>
              <button
                type="button"
                onClick={handleCopyId}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--color-muted)' }}
                title={t.audit.copyJson}
              >
                {copiedId ? <Check size={13} style={{ color: 'var(--color-success)' }} /> : <Copy size={13} />}
              </button>
            </div>

            <span className={styles.fieldLabel}>{t.audit.time}:</span>
            <span className={styles.fieldValue}>{fmtDateTime(entry.at)}</span>

            <span className={styles.fieldLabel}>{t.audit.actionCol}:</span>
            <div className={styles.fieldValue}>
              <AuditActionBadge action={entry.action} />
              <div style={{ fontSize: '11px', color: 'var(--color-muted)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
                {entry.action}
              </div>
            </div>

            <span className={styles.fieldLabel}>{t.audit.actorCol}:</span>
            <div className={styles.fieldValue}>
              {actorMember ? (
                <div>
                  <strong>{actorMember.display_name}</strong>
                  <div style={{ fontSize: '11px', color: 'var(--color-muted)' }}>{actorMember.email}</div>
                </div>
              ) : (
                <span>{entry.actor_id || t.audit.system}</span>
              )}
            </div>

            <span className={styles.fieldLabel}>{t.audit.targetCol}:</span>
            <div className={styles.fieldValue}>
              {targetMember ? (
                <div>
                  <strong>{targetMember.display_name}</strong> ({entry.target_type})
                  <div style={{ fontSize: '11px', color: 'var(--color-muted)' }}>{targetMember.email}</div>
                </div>
              ) : (
                <span>{entry.target_type}:{entry.target_id || '—'}</span>
              )}
            </div>

            <span className={styles.fieldLabel}>{t.audit.reasonCol}:</span>
            <span className={styles.fieldValue} style={{ fontWeight: 600 }}>{entry.reason}</span>
          </div>

          <div className={styles.jsonBox}>
            <div className={styles.jsonHeader}>
              <span className={styles.jsonTitle}>Raw JSON Payload</span>
              <Button variant="ghost" size="sm" onClick={handleCopyJson}>
                {copiedJson ? <Check size={13} style={{ color: 'var(--color-success)' }} /> : <Copy size={13} />}
                {copiedJson ? t.audit.copied : t.audit.copyJson}
              </Button>
            </div>
            <pre className={styles.jsonCode}>{jsonStr}</pre>
          </div>
        </div>

        <div className={styles.footer}>
          <Button variant="secondary" onClick={onClose}>
            {t.audit.close}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default AuditDetailModal;
