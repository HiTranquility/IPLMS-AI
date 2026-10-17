import { UserPlus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { ROLES, type Member } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/table.module.css';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { PageHeader } from '@/components/layout/PageHeader';
import { useInvite, useMe, useMembers, useRoleChange } from '@/hooks/useConsole';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtDateTime } from '@/utils/format';
import styles from './MembersPage.module.css';

function InviteForm() {
  const { t } = useI18n();
  const invite = useInvite();
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [reason, setReason] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    invite.mutate(
      { email: email.trim(), displayName: displayName.trim(), reason: reason.trim() },
      { onSuccess: () => { setEmail(''); setDisplayName(''); setReason(''); } },
    );
  };

  return (
    <form className={styles.form} onSubmit={submit} aria-labelledby="invite-title">
      <h2 id="invite-title" className={styles.formTitle}>{t.members.inviteTitle}</h2>
      <TextField label={t.members.googleEmail} type="email" required maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} />
      <TextField label={t.members.displayName} required maxLength={120} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
      <TextField label={t.common.reason} hint={t.members.inviteReasonHint} required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
      {invite.error && <ErrorBlock error={invite.error} />}
      {invite.isSuccess && <p className={styles.ok} role="status">{t.members.invited}</p>}
      <Button type="submit" loading={invite.isPending}>
        <UserPlus size={16} aria-hidden />
        {t.members.invite}
      </Button>
    </form>
  );
}

function RoleForm({ members, selfId }: { members: Member[]; selfId: string }) {
  const { t } = useI18n();
  const change = useRoleChange();
  const [memberId, setMemberId] = useState('');
  const [role, setRole] = useState<string>(ROLES[0]);
  const [reason, setReason] = useState('');
  const [result, setResult] = useState<string | null>(null);

  const run = (grant: boolean) => (event: { preventDefault: () => void }) => {
    event.preventDefault();
    setResult(null);
    change.mutate(
      { memberId, role, reason: reason.trim(), grant },
      {
        onSuccess: (res) => {
          const changed = (res as { changed: boolean }).changed;
          setResult(changed ? (grant ? t.members.granted : t.members.revoked) : grant ? t.members.alreadyHas : t.members.doesNotHave);
          setReason('');
        },
      },
    );
  };

  const ready = memberId !== '' && reason.trim().length >= 3;
  return (
    <form className={styles.form} onSubmit={run(true)} aria-labelledby="role-title">
      <h2 id="role-title" className={styles.formTitle}>{t.members.roleTitle}</h2>
      <SelectField label={t.members.member} required value={memberId} onChange={(e) => setMemberId(e.target.value)}>
        <option value="">{t.members.pickMember}</option>
        {members.map((m) => (
          <option key={m.id} value={m.id} disabled={m.id === selfId}>
            {m.display_name} · {m.email}{m.id === selfId ? t.members.selfSuffix : ''}
          </option>
        ))}
      </SelectField>
      <SelectField label={t.members.role} value={role} onChange={(e) => setRole(e.target.value)}>
        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
      </SelectField>
      <TextField label={t.common.reason} hint={t.members.roleReasonHint} required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
      {change.error && <ErrorBlock error={change.error} />}
      {result && <p className={styles.ok} role="status">{result}</p>}
      <div className={styles.actions}>
        <Button type="submit" disabled={!ready} loading={change.isPending && change.variables?.grant}>{t.members.grant}</Button>
        <Button variant="danger" disabled={!ready} loading={change.isPending && !change.variables?.grant} onClick={run(false)}>{t.members.revoke}</Button>
      </div>
    </form>
  );
}

export function MembersPage() {
  const { t } = useI18n();
  const me = useMe();
  const members = useMembers();

  return (
    <>
      <PageHeader title={t.members.title} description={t.members.desc} />
      <div className={styles.layout}>
        <section aria-label={t.members.listLabel}>
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
                  </tr>
                </thead>
                <tbody>
                  {members.data.map((m) => (
                    <tr key={m.id}>
                      <td>
                        <div>{m.display_name}</div>
                        <div className={table.muted}>{m.email}</div>
                      </td>
                      <td className={table.mono}>{m.roles.length ? m.roles.join(', ') : '—'}</td>
                      <td><Badge tone={m.status === 'ACTIVE' ? 'success' : m.status === 'DISABLED' ? 'danger' : 'neutral'}>{t.members.status[m.status]}</Badge></td>
                      <td className={table.num}>{fmtDateTime(m.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <aside className={styles.side}>
          <InviteForm />
          {members.data && me.data && <RoleForm members={members.data} selfId={me.data.member_id} />}
        </aside>
      </div>
    </>
  );
}
