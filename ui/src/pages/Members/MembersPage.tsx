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
import { fmtDateTime } from '@/utils/format';
import styles from './MembersPage.module.css';

const STATUS_LABEL: Record<Member['status'], string> = { INVITED: 'Đã mời', ACTIVE: 'Đang dùng', DISABLED: 'Đã khoá' };

function InviteForm() {
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
      <h2 id="invite-title" className={styles.formTitle}>Mời thành viên</h2>
      <TextField label="Email Google" type="email" required maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} />
      <TextField label="Tên hiển thị" required maxLength={120} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
      <TextField label="Lý do" hint="Ghi vào nhật ký, 3–500 ký tự." required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
      {invite.error && <ErrorBlock error={invite.error} />}
      {invite.isSuccess && <p className={styles.ok} role="status">Đã mời. Người được mời đăng nhập Google bằng đúng email này.</p>}
      <Button type="submit" loading={invite.isPending}>
        <UserPlus size={16} aria-hidden />
        Mời
      </Button>
    </form>
  );
}

function RoleForm({ members, selfId }: { members: Member[]; selfId: string }) {
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
          setResult(changed ? (grant ? 'Đã cấp vai trò.' : 'Đã thu hồi vai trò.') : grant ? 'Thành viên đã có vai trò này.' : 'Thành viên không có vai trò này.');
          setReason('');
        },
      },
    );
  };

  const ready = memberId !== '' && reason.trim().length >= 3;
  return (
    <form className={styles.form} onSubmit={run(true)} aria-labelledby="role-title">
      <h2 id="role-title" className={styles.formTitle}>Cấp / thu hồi vai trò</h2>
      <SelectField label="Thành viên" required value={memberId} onChange={(e) => setMemberId(e.target.value)}>
        <option value="">Chọn thành viên</option>
        {members.map((m) => (
          <option key={m.id} value={m.id} disabled={m.id === selfId}>
            {m.display_name} · {m.email}{m.id === selfId ? ' (bạn — không tự cấp)' : ''}
          </option>
        ))}
      </SelectField>
      <SelectField label="Vai trò" value={role} onChange={(e) => setRole(e.target.value)}>
        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
      </SelectField>
      <TextField label="Lý do" hint="Bắt buộc, ghi vào nhật ký." required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
      {change.error && <ErrorBlock error={change.error} />}
      {result && <p className={styles.ok} role="status">{result}</p>}
      <div className={styles.actions}>
        <Button type="submit" disabled={!ready} loading={change.isPending && change.variables?.grant}>Cấp vai trò</Button>
        <Button variant="danger" disabled={!ready} loading={change.isPending && !change.variables?.grant} onClick={run(false)}>Thu hồi</Button>
      </div>
    </form>
  );
}

export function MembersPage() {
  const me = useMe();
  const members = useMembers();

  return (
    <>
      <PageHeader title="Thành viên & vai trò" description="Quyền console nằm ở DB riêng của console. Admin/Moderator của platform không tự có vai trò nào ở đây." />
      <div className={styles.layout}>
        <section aria-label="Danh sách thành viên">
          {members.isPending && <Loading />}
          {members.error && <ErrorBlock error={members.error} onRetry={() => void members.refetch()} />}
          {members.data && (
            <div className={table.wrap}>
              <table className={table.table}>
                <thead>
                  <tr>
                    <th scope="col">Thành viên</th>
                    <th scope="col">Vai trò</th>
                    <th scope="col">Trạng thái</th>
                    <th scope="col">Ngày mời</th>
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
                      <td><Badge tone={m.status === 'ACTIVE' ? 'success' : m.status === 'DISABLED' ? 'danger' : 'neutral'}>{STATUS_LABEL[m.status]}</Badge></td>
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
