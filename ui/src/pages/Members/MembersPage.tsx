import { Mail, Search, Shield, ShieldCheck, UserCheck, Users } from 'lucide-react';
import { useMemo, useState } from 'react';
import table from '@/components/common/Ui/data-display/table.module.css';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useMe } from '@/hooks/queries/useAuthQueries';
import { useMembers } from '@/hooks/queries/useMemberQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { ROLES } from '@/types/auth';
import type { Member } from '@/types/member';
import { fmtDateTime } from '@/utils/format';
import { InviteForm } from './components/InviteForm';
import { MemberStatCard } from './components/MemberStatCard';
import { RoleBadge } from './components/RoleBadge';
import { RoleForm } from './components/RoleForm';
import styles from './MembersPage.module.css';

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function MembersPage() {
  const { t } = useI18n();
  const me = useMe();
  const members = useMembers();

  const [selectedMemberId, setSelectedMemberId] = useState<string | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');

  const memberList: Member[] = members.data || [];

  // 4 Top Metric Stats
  const stats = useMemo(() => {
    const total = memberList.length;
    const active = memberList.filter((m) => m.status === 'ACTIVE').length;
    const invited = memberList.filter((m) => m.status === 'INVITED').length;
    const totalRoles = memberList.reduce((acc, m) => acc + m.roles.length, 0);
    return { total, active, invited, totalRoles };
  }, [memberList]);

  // Bộ lọc tìm kiếm & vai trò
  const filteredMembers = useMemo(() => {
    return memberList.filter((m) => {
      const matchSearch =
        searchQuery === '' ||
        m.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.roles.some((r) => r.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchRole =
        roleFilter === 'all' ||
        m.roles.includes(roleFilter as any) ||
        m.roles.includes(`ai_${roleFilter}` as any);

      return matchSearch && matchRole;
    });
  }, [memberList, searchQuery, roleFilter]);

  const handlePickForRole = (memberId: string) => {
    setSelectedMemberId(memberId);
    // Cuộn nhẹ tới form phân vai trò nếu màn hình hẹp
    const roleElem = document.getElementById('role-title');
    if (roleElem && window.innerWidth <= 1180) {
      roleElem.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className={styles.pageContainer}>
      <PageHeader title={t.members.title} description={t.members.desc} />

      {/* 4 Thẻ chỉ số tổng quan */}
      <div className={styles.statsGrid}>
        <MemberStatCard
          icon={<Users size={22} />}
          label={t.members.statsTotal}
          value={stats.total}
          tone="primary"
          subtext="Tài khoản trong DB Console"
        />
        <MemberStatCard
          icon={<UserCheck size={22} />}
          label={t.members.statsActive}
          value={stats.active}
          tone="success"
          subtext="Đã kích hoạt & có phiên"
        />
        <MemberStatCard
          icon={<Mail size={22} />}
          label={t.members.statsInvited}
          value={stats.invited}
          tone="warning"
          subtext="Chờ đăng nhập Google"
        />
        <MemberStatCard
          icon={<ShieldCheck size={22} />}
          label={t.members.statsRoles}
          value={stats.totalRoles}
          tone="accent"
          subtext="Lượt phân quyền RBAC"
        />
      </div>

      <div className={styles.layout}>
        <section aria-label={t.members.listLabel} className={styles.tableContainer}>
          {/* Thanh công cụ tìm kiếm & lọc */}
          <div className={styles.tableToolbar}>
            <div className={styles.searchWrap}>
              <Search size={15} className={styles.searchIcon} aria-hidden />
              <input
                type="search"
                className={styles.searchInput}
                placeholder={t.members.searchPlaceholder}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label={t.members.searchPlaceholder}
              />
            </div>

            <select
              className={styles.filterSelect}
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              aria-label="Lọc theo vai trò"
            >
              <option value="all">{t.members.filterRoleAll}</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r.replace(/^ai_/, '')}
                </option>
              ))}
            </select>

            <span className={styles.tableCount}>
              Hiển thị {filteredMembers.length} / {memberList.length} thành viên
            </span>
          </div>

          {members.isPending && <Loading />}
          {members.error && <ErrorBlock error={members.error} onRetry={() => void members.refetch()} />}

          {members.data && (
            <div className={table.wrap}>
              <table className={table.table}>
                <thead>
                  <tr>
                    <th scope="col">{t.members.member}</th>
                    <th scope="col">{t.members.role}</th>
                    <th scope="col">{t.common.status}</th>
                    <th scope="col">{t.members.invitedAt}</th>
                    <th scope="col" style={{ textAlign: 'right' }}>{t.common.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMembers.map((m) => {
                    const isSelf = me.data?.member_id === m.id;
                    const cleanRoles = m.roles.map((r) => r.replace(/^ai_/, ''));
                    const maxDisplayRoles = 3;
                    const visibleRoles = m.roles.slice(0, maxDisplayRoles);
                    const remainingCount = m.roles.length - maxDisplayRoles;

                    return (
                      <tr key={m.id}>
                        <td>
                          <div className={styles.memberCell}>
                            <div className={`${styles.avatar} ${isSelf ? styles.avatarSelf : ''}`}>
                              {getInitials(m.display_name)}
                            </div>
                            <div className={styles.meta}>
                              <div className={styles.nameRow}>
                                <span className={styles.memberName}>{m.display_name}</span>
                                {isSelf && <span className={styles.selfTag}>Bạn</span>}
                              </div>
                              <div className={styles.memberEmail}>{m.email}</div>
                            </div>
                          </div>
                        </td>

                        <td>
                          {m.roles.length > 0 ? (
                            <div className={styles.rolesCell}>
                              {visibleRoles.map((r) => (
                                <RoleBadge key={r} role={r} />
                              ))}
                              {remainingCount > 0 && (
                                <span
                                  className={styles.moreRolesTag}
                                  title={cleanRoles.slice(maxDisplayRoles).join(', ')}
                                >
                                  +{remainingCount} khác
                                </span>
                              )}
                            </div>
                          ) : (
                            <span style={{ color: 'var(--color-faded)', fontSize: 'var(--text-xs)' }}>
                              —
                            </span>
                          )}
                        </td>

                        <td>
                          <span className={`${styles.statusBadge} ${styles[`status_${m.status}`]}`}>
                            <span className={styles.statusDot} />
                            {t.members.status[m.status]}
                          </span>
                        </td>

                        <td className={table.num}>{fmtDateTime(m.created_at)}</td>

                        <td style={{ textAlign: 'right' }}>
                          <button
                            type="button"
                            className={styles.manageBtn}
                            onClick={() => handlePickForRole(m.id)}
                            title={`${t.members.manageRolesAction}: ${m.display_name}`}
                          >
                            <Shield size={12} aria-hidden />
                            <span>{t.members.manageRolesAction}</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className={styles.side}>
          <InviteForm />
          {members.data && me.data && (
            <RoleForm
              members={members.data}
              selfId={me.data.member_id}
              selectedMemberId={selectedMemberId}
              onMemberSelect={setSelectedMemberId}
            />
          )}
        </aside>
      </div>
    </div>
  );
}

export default MembersPage;
