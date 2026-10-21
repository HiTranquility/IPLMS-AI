import { Database, FileCheck, Images, Lock } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan } from '@/hooks/common/useCan';
import { useStepUpMutation } from '@/hooks/mutations/useAuthMutations';
import { useFreezeSnapshot } from '@/hooks/mutations/useVisionMutations';
import { useSnapshots } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { MemberStatCard } from '@/pages/Members/components/MemberStatCard';
import type { VisionSnapshot } from '@/types/vision';
import { fmtDateTime, fmtInt } from '@/utils/format';
import { CreateSnapshotForm } from './components/CreateSnapshotForm';
import styles from './DatasetsPage.module.css';

export function DatasetsPage() {
  const { t } = useI18n();
  const snapshots = useSnapshots();
  const freeze = useFreezeSnapshot();
  const stepUp = useStepUpMutation();
  const canCreate = useCan('ai:dataset:snapshot');
  const canFreeze = useCan('ai:golden:freeze');
  const handleStepUp = (code: string, reason: string) => stepUp.mutateAsync({ code, reason });

  const [kindFilter, setKindFilter] = useState<'all' | 'golden' | 'train'>('all');

  const rawList: VisionSnapshot[] = snapshots.data || [];

  // 4 Top Metric Cards
  const stats = useMemo(() => {
    const total = rawList.length;
    const golden = rawList.filter((s) => s.kind === 'golden').length;
    const frozen = rawList.filter((s) => s.frozen_at !== null).length;
    const totalSamples = rawList.reduce((acc, s) => acc + s.sample_count, 0);
    return { total, golden, frozen, totalSamples };
  }, [rawList]);

  const filteredSnapshots = useMemo(() => {
    if (kindFilter === 'all') return rawList;
    return rawList.filter((s) => s.kind === kindFilter);
  }, [rawList, kindFilter]);

  return (
    <>
      <PageHeader
        title={t.datasets.title}
        description={t.datasets.desc}
      />

      {/* 4 Thẻ chỉ số tổng quan Datasets */}
      <div className={styles.statsGrid}>
        <MemberStatCard
          icon={<Database size={22} />}
          label="Tổng số Dataset"
          value={stats.total}
          tone="primary"
          subtext="Các mốc snapshot dữ liệu"
        />
        <MemberStatCard
          icon={<FileCheck size={22} />}
          label="Tập Golden Benchmark"
          value={stats.golden}
          tone="accent"
          subtext={`${stats.frozen} tập đã đóng băng`}
        />
        <MemberStatCard
          icon={<Lock size={22} />}
          label="Đóng băng bất biến"
          value={stats.frozen}
          tone="warning"
          subtext="Có khoá SHA-256 an toàn"
        />
        <MemberStatCard
          icon={<Images size={22} />}
          label="Tổng mẫu lưu trữ"
          value={fmtInt(stats.totalSamples)}
          tone="success"
          subtext="Ảnh biển số đã gom cụm"
        />
      </div>

      {canCreate && (
        <section className={styles.section}>
          <CreateSnapshotForm />
        </section>
      )}

      <section className={styles.section} aria-labelledby="snapshots-title">
        <h2 id="snapshots-title" className={styles.sectionTitle}>{t.datasets.listTitle}</h2>
        {snapshots.isPending && <Loading />}
        {snapshots.error && <ErrorBlock error={snapshots.error} onRetry={() => void snapshots.refetch()} />}
        {snapshots.data?.length === 0 && (
          <EmptyState icon={<Database size={28} />} title={t.datasets.emptyTitle} description={t.datasets.emptyDesc} />
        )}
        {snapshots.data && snapshots.data.length > 0 && (
          <div className={styles.tableCard}>
            <div className={styles.tableToolbar}>
              <select
                className={styles.filterSelect}
                value={kindFilter}
                onChange={(e) => setKindFilter(e.target.value as any)}
                aria-label="Lọc theo loại dataset"
              >
                <option value="all">Tất cả loại dataset</option>
                <option value="golden">Chỉ tập Golden Benchmark</option>
                <option value="train">Chỉ tập Huấn luyện (Train)</option>
              </select>

              <span className={styles.tableCount}>
                Hiển thị {filteredSnapshots.length} / {rawList.length} snapshot
              </span>
            </div>

            <div className={table.wrap}>
              <table className={table.table}>
                <thead>
                  <tr>
                    <th scope="col">{t.common.name}</th>
                    <th scope="col">{t.datasets.kind}</th>
                    <th scope="col" className={table.num}>{t.common.sample}</th>
                    <th scope="col">sha256</th>
                    <th scope="col">{t.datasets.createdCol}</th>
                    <th scope="col" style={{ textAlign: 'right' }}>{t.datasets.frozenCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSnapshots.map((s) => (
                    <tr key={s.id}>
                      <td style={{ fontWeight: 600 }}>{s.name}</td>
                      <td>
                        <Badge tone={s.kind === 'golden' ? 'accent' : 'neutral'}>{s.kind}</Badge>
                      </td>
                      <td className={table.num}>{fmtInt(s.sample_count)}</td>
                      <td className={table.mono} title={s.samples_sha256}>
                        {s.samples_sha256.slice(0, 14)}...
                      </td>
                      <td className={table.muted}>
                        {s.created_by} · {fmtDateTime(s.created_at)}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {s.frozen_at ? (
                          <span
                            className={table.mono}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 4,
                              color: 'var(--color-warning)',
                              fontWeight: 600,
                            }}
                          >
                            <Lock size={12} aria-hidden />
                            {s.frozen_by} · {fmtDateTime(s.frozen_at)}
                          </span>
                        ) : s.kind === 'golden' && canFreeze ? (
                          <ReasonAction
                            label={t.datasets.freeze}
                            variant="accent"
                            onStepUp={handleStepUp}
                            onSubmit={(reason) => freeze.mutateAsync({ id: s.id, reason })}
                          />
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

export default DatasetsPage;
