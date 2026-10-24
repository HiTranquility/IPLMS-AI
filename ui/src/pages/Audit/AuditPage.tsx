import { Bot, Download, Eye, FileSpreadsheet, Lock, Search, Shield, ShieldCheck, UserCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useAudit } from '@/hooks/queries/useAuditQueries';
import { useMembers } from '@/hooks/queries/useMemberQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { MemberStatCard } from '@/pages/Members/components/MemberStatCard';
import type { AuditEntry } from '@/types/audit';
import type { Member } from '@/types/member';
import { toCsv } from '@/utils/csv';
import { fmtDateTime } from '@/utils/format';
import { actionLabel, AuditActionBadge, getActionMeta, type AuditCategory } from './components/AuditActionBadge';
import { AuditDetailModal } from './components/AuditDetailModal';
import styles from './AuditPage.module.css';

function getRelativeTime(isoString: string, t: any): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t.audit.relativeNow;
  if (mins < 60) return t.audit.relativeMinutesAgo(mins);
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t.audit.relativeHoursAgo(hours);
  const days = Math.floor(hours / 24);
  return t.audit.relativeDaysAgo(days);
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function AuditPage() {
  const { t } = useI18n();
  const audit = useAudit();
  const members = useMembers();

  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | Exclude<AuditCategory, 'other'>>('all');
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);

  const rawList: AuditEntry[] = audit.data || [];
  const memberList: Member[] = members.data || [];

  // Mapped lookups
  const memberMap = useMemo(() => {
    const map = new Map<string, Member>();
    memberList.forEach((m) => map.set(m.id, m));
    return map;
  }, [memberList]);

  // 4 Top Metric Cards
  const stats = useMemo(() => {
    const total = rawList.length;
    const rbac = rawList.filter((e) => {
      const cat = getActionMeta(e.action).category;
      return cat === 'rbac';
    }).length;
    const ml = rawList.filter((e) => {
      const cat = getActionMeta(e.action).category;
      return cat === 'ml';
    }).length;
    const latest = rawList[0] ? getRelativeTime(rawList[0].at, t) : '—';
    return { total, rbac, ml, latest };
  }, [rawList, t]);

  // Bộ lọc dữ liệu
  const filteredEntries = useMemo(() => {
    return rawList.filter((e) => {
      const meta = getActionMeta(e.action);
      const matchCat = categoryFilter === 'all' || meta.category === categoryFilter;

      if (!matchCat) return false;
      if (!searchQuery) return true;

      const q = searchQuery.toLowerCase();
      const actor = memberMap.get(e.actor_id);
      const target = e.target_type === 'console_member' ? memberMap.get(e.target_id) : null;

      const matchReason = e.reason.toLowerCase().includes(q);
      const matchAction = e.action.toLowerCase().includes(q) || actionLabel(e.action, t).toLowerCase().includes(q);
      const matchActor = actor
        ? actor.display_name.toLowerCase().includes(q) || actor.email.toLowerCase().includes(q)
        : e.actor_id.toLowerCase().includes(q);
      const matchTarget = target
        ? target.display_name.toLowerCase().includes(q) || target.email.toLowerCase().includes(q)
        : `${e.target_type}:${e.target_id}`.toLowerCase().includes(q);

      return matchReason || matchAction || matchActor || matchTarget;
    });
  }, [rawList, categoryFilter, searchQuery, memberMap, t]);

  // Xuất file CSV
  const handleExportCsv = () => {
    if (filteredEntries.length === 0) return;
    const rows = filteredEntries.map((e) => {
      const actor = memberMap.get(e.actor_id);
      return [
        e.id,
        fmtDateTime(e.at),
        actionLabel(e.action, t),
        e.action,
        actor ? actor.display_name : (e.actor_id || t.audit.system),
        actor ? actor.email : '',
        e.target_type,
        e.target_id,
        e.reason,
      ];
    });

    // toCsv bọc nháy mọi ô và chặn công thức (bug-019).
    const csvContent = '\uFEFF' + toCsv([t.audit.csvHeaders, ...rows]);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Xuất file JSON
  const handleExportJson = () => {
    if (filteredEntries.length === 0) return;
    const blob = new Blob([JSON.stringify(filteredEntries, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-log-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className={styles.section} aria-label={t.audit.title}>
      <PageHeader title={t.audit.title} description={t.audit.desc} />

      {/* 4 Thẻ chỉ số tổng quan */}
      <div className={styles.statsGrid}>
        <MemberStatCard
          icon={<Shield size={22} />}
          label={t.audit.statsTotalEvents}
          value={stats.total}
          tone="primary"
          subtext="Bản ghi bất biến trong DB"
        />
        <MemberStatCard
          icon={<UserCheck size={22} />}
          label={t.audit.statsRbacEvents}
          value={stats.rbac}
          tone="success"
          subtext="Gán/thu hồi quyền & mời"
        />
        <MemberStatCard
          icon={<Lock size={22} />}
          label={t.audit.statsMlEvents}
          value={stats.ml}
          tone="warning"
          subtext="Model, Golden & Chính sách"
        />
        <MemberStatCard
          icon={<ShieldCheck size={22} />}
          label={t.audit.statsLatestEvent}
          value={stats.latest}
          tone="accent"
          subtext="Ghi nhận gần nhất"
        />
      </div>

      <div className={styles.tableContainer}>
        {/* Thanh công cụ tìm kiếm, lọc danh mục & xuất báo cáo */}
        <div className={styles.toolbar}>
          <div className={styles.searchWrap}>
            <Search size={15} className={styles.searchIcon} aria-hidden />
            <input
              type="search"
              className={styles.searchInput}
              placeholder={t.audit.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label={t.audit.searchPlaceholder}
            />
          </div>

          <select
            className={styles.filterSelect}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as any)}
            aria-label="Lọc danh mục kiểm toán"
          >
            <option value="all">{t.audit.filterCategoryAll}</option>
            <option value="rbac">{t.audit.filterCategoryRbac}</option>
            <option value="ml">{t.audit.filterCategoryMl}</option>
            <option value="auth">{t.audit.filterCategoryAuth}</option>
            <option value="review">{t.audit.filterCategoryReview}</option>
          </select>

          <div className={styles.exportGroup}>
            <Button variant="secondary" size="sm" onClick={handleExportCsv} disabled={filteredEntries.length === 0}>
              <FileSpreadsheet size={13} aria-hidden />
              {t.audit.exportCsv}
            </Button>
            <Button variant="secondary" size="sm" onClick={handleExportJson} disabled={filteredEntries.length === 0}>
              <Download size={13} aria-hidden />
              {t.audit.exportJson}
            </Button>
          </div>

          <span className={styles.tableCount}>
            Hiển thị {filteredEntries.length} / {rawList.length} bản ghi
          </span>
        </div>

        {audit.isPending && <Loading />}
        {audit.error && <ErrorBlock error={audit.error} onRetry={() => void audit.refetch()} />}

        {rawList.length === 0 && !audit.isPending && (
          <EmptyState icon={<Shield size={28} />} title={t.audit.empty} />
        )}

        {filteredEntries.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col">{t.audit.time}</th>
                  <th scope="col">{t.audit.actionCol}</th>
                  <th scope="col">{t.audit.actorCol}</th>
                  <th scope="col">{t.audit.targetCol}</th>
                  <th scope="col">{t.audit.reasonCol}</th>
                  <th scope="col" style={{ textAlign: 'right' }}>{t.common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.map((e) => {
                  const actor = memberMap.get(e.actor_id);
                  const targetMember = e.target_type === 'console_member' ? memberMap.get(e.target_id) : null;
                  const relTime = getRelativeTime(e.at, t);

                  return (
                    <tr key={e.id}>
                      {/* Thời điểm */}
                      <td>
                        <div className={styles.timeCell}>
                          <span className={styles.relativeTime}>{relTime}</span>
                          <span className={styles.absoluteTime}>{fmtDateTime(e.at)}</span>
                        </div>
                      </td>

                      {/* Hành động */}
                      <td>
                        <AuditActionBadge action={e.action} />
                      </td>

                      {/* Người thực hiện (Actor) */}
                      <td>
                        <div className={styles.actorCell}>
                          {actor ? (
                            <>
                              <div className={styles.actorAvatar}>
                                {getInitials(actor.display_name)}
                              </div>
                              <div className={styles.actorInfo}>
                                <span className={styles.actorName}>{actor.display_name}</span>
                                <span className={styles.actorEmail}>{actor.email}</span>
                              </div>
                            </>
                          ) : (
                            <>
                              <div className={`${styles.actorAvatar} ${styles.systemAvatar}`}>
                                <Bot size={15} />
                              </div>
                              <div className={styles.actorInfo}>
                                <span className={styles.actorName}>{t.audit.system}</span>
                                <span className={styles.actorEmail}>{e.actor_id ? e.actor_id.slice(0, 8) : 'internal'}</span>
                              </div>
                            </>
                          )}
                        </div>
                      </td>

                      {/* Đối tượng (Target) */}
                      <td>
                        <div className={styles.targetCell}>
                          <span className={styles.targetType}>{e.target_type}</span>
                          <span className={styles.targetName}>
                            {targetMember ? targetMember.display_name : (e.target_id ? e.target_id.slice(0, 12) : '—')}
                          </span>
                        </div>
                      </td>

                      {/* Lý do */}
                      <td>
                        <div className={styles.reasonCell} title={e.reason}>
                          {e.reason}
                        </div>
                      </td>

                      {/* Thao tác xem chi tiết */}
                      <td style={{ textAlign: 'right' }}>
                        <button
                          type="button"
                          className={styles.inspectBtn}
                          onClick={() => setSelectedEntry(e)}
                          title={`${t.audit.eventDetailTitle}: ${e.id}`}
                          aria-label={`${t.audit.eventDetailTitle}: ${e.id}`}
                        >
                          <Eye size={14} aria-hidden />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal xem chi tiết sự kiện */}
      {selectedEntry && (
        <AuditDetailModal
          entry={selectedEntry}
          members={memberList}
          onClose={() => setSelectedEntry(null)}
        />
      )}
    </section>
  );
}

export default AuditPage;
