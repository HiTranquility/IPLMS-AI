import { UserPlus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { queryKeys } from '@/constants/queryKeys';
import { useI18n } from '@/i18n/I18nProvider';
import { grantRole, inviteMember } from '@/services/apiEndpoints/member.endpoint';
import { RoleSelectorGroup } from './RoleSelectorGroup';
import styles from '../MembersPage.module.css';

export function InviteForm() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [reason, setReason] = useState('');
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<Error | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsSubmitting(true);

    try {
      const cleanEmail = email.trim();
      const cleanName = displayName.trim();
      const cleanReason = reason.trim();

      // 1. Tạo thành viên mới
      const newMember = await inviteMember(cleanEmail, cleanName, cleanReason);

      // 2. Cấp đồng thời các vai trò đã chọn (nếu có)
      if (selectedRoles.length > 0) {
        for (const role of selectedRoles) {
          await grantRole(newMember.id, role, cleanReason);
        }
      }

      // 3. Làm tươi danh sách thành viên & nhật ký audit
      void queryClient.invalidateQueries({ queryKey: queryKeys.members.list() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.audit.list() });

      setSuccessMessage(
        selectedRoles.length > 0
          ? t.members.invitedWithRoles(selectedRoles.length)
          : t.members.invited,
      );
      setEmail('');
      setDisplayName('');
      setReason('');
      setSelectedRoles([]);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={submit} aria-labelledby="invite-title">
      <h2 id="invite-title" className={styles.formTitle}>
        <UserPlus size={18} className={styles.titleIcon} aria-hidden />
        {t.members.inviteTitle}
      </h2>

      <TextField
        label={t.members.googleEmail}
        type="email"
        required
        maxLength={254}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={isSubmitting}
      />

      <TextField
        label={t.members.displayName}
        required
        maxLength={120}
        value={displayName}
        onChange={(e) => setDisplayName(e.target.value)}
        disabled={isSubmitting}
      />

      <div className={styles.fieldBlock}>
        <label className={styles.fieldLabel}>{t.members.rolesToAssign}</label>
        <span className={styles.fieldHint}>{t.members.selectRolesHint}</span>
        <RoleSelectorGroup
          selectedRoles={selectedRoles}
          onChange={setSelectedRoles}
          disabled={isSubmitting}
        />
      </div>

      <TextField
        label={t.common.reason}
        hint={t.members.inviteReasonHint}
        required
        minLength={3}
        maxLength={500}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        disabled={isSubmitting}
      />

      {errorMessage ? <ErrorBlock error={errorMessage} /> : null}
      {successMessage && <p className={styles.ok} role="status">{successMessage}</p>}

      <Button type="submit" loading={isSubmitting} disabled={isSubmitting || reason.trim().length < 3}>
        <UserPlus size={16} aria-hidden />
        {t.members.invite}
        {selectedRoles.length > 0 ? ` (${selectedRoles.length} vai trò)` : ''}
      </Button>
    </form>
  );
}

export default InviteForm;
