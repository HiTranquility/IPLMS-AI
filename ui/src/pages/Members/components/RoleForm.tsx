import { ShieldCheck, UserCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { queryKeys } from '@/constants/queryKeys';
import { useI18n } from '@/i18n/I18nProvider';
import { grantRole, revokeRole } from '@/services/apiEndpoints/member.endpoint';
import { ROLES } from '@/types/auth';
import type { Member } from '@/types/member';
import { RoleBadge } from './RoleBadge';
import { RoleSelectorGroup } from './RoleSelectorGroup';
import styles from '../MembersPage.module.css';

export interface RoleFormProps {
  members: Member[];
  selfId: string;
  selectedMemberId?: string;
  onMemberSelect?: (id: string) => void;
}

export function RoleForm({
  members,
  selfId,
  selectedMemberId,
  onMemberSelect,
}: RoleFormProps) {
  const { t } = useI18n();
  const queryClient = useQueryClient();

  const [activeId, setActiveId] = useState<string>(selectedMemberId || '');
  const [selectedNewRoles, setSelectedNewRoles] = useState<string[]>([]);
  const [grantReason, setGrantReason] = useState('');
  const [isGranting, setIsGranting] = useState(false);
  const [revokingRoleKey, setRevokingRoleKey] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<Error | null>(null);

  // Đồng bộ khi prop selectedMemberId thay đổi
  useEffect(() => {
    if (selectedMemberId && selectedMemberId !== activeId) {
      setActiveId(selectedMemberId);
      setSelectedNewRoles([]);
      setActionNotice(null);
      setActionError(null);
    }
  }, [selectedMemberId]);

  const activeMember = useMemo(
    () => members.find((m) => m.id === activeId),
    [members, activeId],
  );

  const unassignedRoles = useMemo(() => {
    if (!activeMember) return [];
    return ROLES.filter((r) => !activeMember.roles.includes(r as any));
  }, [activeMember]);

  const handleMemberChange = (id: string) => {
    setActiveId(id);
    setSelectedNewRoles([]);
    setActionNotice(null);
    setActionError(null);
    onMemberSelect?.(id);
  };

  // Thu hồi trực tiếp 1 vai trò
  const handleQuickRevoke = async (role: string) => {
    if (!activeMember) return;
    const cleanRoleName = role.replace(/^ai_/, '');
    setActionError(null);
    setActionNotice(null);
    setRevokingRoleKey(role);

    try {
      await revokeRole(activeMember.id, role, t.members.quickRevokeReason);
      void queryClient.invalidateQueries({ queryKey: queryKeys.members.list() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.audit.list() });
      setActionNotice(t.members.revokeSuccess(cleanRoleName));
    } catch (err) {
      setActionError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setRevokingRoleKey(null);
    }
  };

  // Cấp đồng thời các vai trò đã chọn
  const handleGrantSelected = async (e: { preventDefault: () => void }) => {
    e.preventDefault();
    if (!activeMember || selectedNewRoles.length === 0) return;
    const reasonText = grantReason.trim();
    if (reasonText.length < 3) return;

    setActionError(null);
    setActionNotice(null);
    setIsGranting(true);

    try {
      for (const role of selectedNewRoles) {
        await grantRole(activeMember.id, role, reasonText);
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.members.list() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.audit.list() });
      setActionNotice(t.members.grantSuccess(selectedNewRoles.length));
      setSelectedNewRoles([]);
      setGrantReason('');
    } catch (err) {
      setActionError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsGranting(false);
    }
  };

  const isSelf = activeId === selfId;

  return (
    <div className={styles.form} aria-labelledby="role-title">
      <h2 id="role-title" className={styles.formTitle}>
        <ShieldCheck size={18} className={styles.titleIcon} aria-hidden />
        {t.members.roleTitle}
      </h2>

      <SelectField
        label={t.members.member}
        required
        value={activeId}
        onChange={(e) => handleMemberChange(e.target.value)}
      >
        <option value="">{t.members.pickMember}</option>
        {members.map((m) => (
          <option key={m.id} value={m.id} disabled={m.id === selfId}>
            {m.display_name} · {m.email}
            {m.id === selfId ? t.members.selfSuffix : ''}
          </option>
        ))}
      </SelectField>

      {activeMember && (
        <div className={styles.memberBox}>
          <div className={styles.memberBoxHeader}>
            <div className={styles.memberAvatar}>
              {activeMember.display_name.slice(0, 2).toUpperCase()}
            </div>
            <div className={styles.memberMeta}>
              <div className={styles.memberName}>{activeMember.display_name}</div>
              <div className={styles.memberEmail}>{activeMember.email}</div>
            </div>
            <div className={styles.memberStatus}>
              <span className={`${styles.statusDot} ${styles[`status_${activeMember.status}`]}`} />
              {t.members.status[activeMember.status]}
            </div>
          </div>

          {/* Section: Vai trò hiện tại */}
          <div className={styles.sectionBlock}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>{t.members.currentRoles}</span>
              <span className={styles.countBadge}>{activeMember.roles.length}</span>
            </div>

            {activeMember.roles.length > 0 ? (
              <div className={styles.roleChipsWrap}>
                {activeMember.roles.map((r) => (
                  <RoleBadge
                    key={r}
                    role={r}
                    showDesc
                    onRemove={isSelf ? undefined : () => void handleQuickRevoke(r)}
                  />
                ))}
              </div>
            ) : (
              <p className={styles.emptyNotice}>{t.members.noRolesYet}</p>
            )}

            {revokingRoleKey && (
              <p className={styles.statusProgress}>
                {t.members.revokingRole}
              </p>
            )}
          </div>

          {/* Section: Cấp thêm vai trò (nếu còn vai trò chưa cấp và không phải tài khoản chính mình) */}
          {!isSelf && (
            <div className={styles.sectionBlock}>
              <div className={styles.sectionHeader}>
                <span className={styles.sectionTitle}>{t.members.grantMoreRoles}</span>
                <span className={styles.countBadge}>{t.members.availableCount(unassignedRoles.length)}</span>
              </div>

              {unassignedRoles.length > 0 ? (
                <form onSubmit={handleGrantSelected} className={styles.grantForm}>
                  <RoleSelectorGroup
                    roles={unassignedRoles}
                    selectedRoles={selectedNewRoles}
                    onChange={setSelectedNewRoles}
                    disabled={isGranting}
                  />

                  {selectedNewRoles.length > 0 && (
                    <>
                      <TextField
                        label={t.common.reason}
                        hint={t.members.roleReasonHint}
                        required
                        minLength={3}
                        maxLength={500}
                        value={grantReason}
                        onChange={(e) => setGrantReason(e.target.value)}
                        disabled={isGranting}
                      />

                      <Button
                        type="submit"
                        disabled={grantReason.trim().length < 3 || isGranting}
                        loading={isGranting}
                      >
                        <UserCheck size={16} aria-hidden />
                        {t.members.grantSelected(selectedNewRoles.length)}
                      </Button>
                    </>
                  )}
                </form>
              ) : (
                <p className={styles.allRolesGrantedNotice}>
                  ✓ {t.members.allRolesGranted}
                </p>
              )}
            </div>
          )}

          {isSelf && (
            <p className={styles.selfNotice}>
              {t.members.selfNotice}
            </p>
          )}

          {actionError ? <ErrorBlock error={actionError} /> : null}
          {actionNotice && <p className={styles.ok} role="status">{actionNotice}</p>}
        </div>
      )}
    </div>
  );
}

export default RoleForm;
