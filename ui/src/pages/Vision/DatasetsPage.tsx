import { Database, FileCheck, Images, Lock } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
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

  // 4 Top Metric Cards: Total Snapshots, Locked Golden Sets, Training Sets, Total Samples
  const stats = useMemo(() => {
    const total = rawList.length;
    const golden = rawList.filter((s) => s.kind === 'golden').length;
    const train = rawList.filter((s) => s.kind === 'train').length;
    const frozen = rawList.filter((s) => Boolean(s.frozen_at || (s as { locked_at?: string | null }).locked_at)).length;
    const totalSamples = rawList.reduce((acc, s) => acc + s.sample_count, 0);
    return { total, golden, train, frozen, totalSamples };
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
          label={t.datasets.statTotal}
          value={stats.total}
          tone="primary"
          subtext={t.datasets.statTotalSub}
        />
        <MemberStatCard
          icon={<Lock size={22} />}
          label={t.datasets.statFrozen}
          value={stats.frozen}
          tone="warning"
          subtext={t.datasets.statGoldenSub(stats.golden)}
        />
        <MemberStatCard
          icon={<FileCheck size={22} />}
          label={t.datasets.statTrain}
          value={stats.train}
          tone="accent"
          subtext={t.datasets.statTrainSub}
        />
        <MemberStatCard
          icon={<Images size={22} />}
          label={t.datasets.statSamples}
          value={fmtInt(stats.totalSamples)}
          tone="success"
          subtext={t.datasets.statSamplesSub}
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
              <div className={styles.filterGroup}>
                <div className={styles.filterTabs} role="group" aria-label={t.datasets.filterLabel}>
                  <button
                    type="button"
                    className={`${styles.filterTab} ${kindFilter === 'all' ? styles.filterTabActive : ''}`}
                    onClick={() => setKindFilter('all')}
                  >
                    {t.datasets.tabAll(stats.total)}
                  </button>
                  <button
                    type="button"
                    className={`${styles.filterTab} ${kindFilter === 'golden' ? styles.filterTabActive : ''}`}
                    onClick={() => setKindFilter('golden')}
                  >
                    {t.datasets.tabGolden(stats.golden)}
                  </button>
                  <button
                    type="button"
                    className={`${styles.filterTab} ${kindFilter === 'train' ? styles.filterTabActive : ''}`}
                    onClick={() => setKindFilter('train')}
                  >
                    {t.datasets.tabTrain(stats.train)}
                  </button>
                </div>

                <select
                  className={styles.filterSelect}
                  value={kindFilter}
                  onChange={(e) => setKindFilter(e.target.value as 'all' | 'golden' | 'train')}
                  aria-label={t.datasets.filterLabel}
                >
                  <option value="all">{t.datasets.filterAll}</option>
                  <option value="golden">{t.datasets.filterGolden}</option>
                  <option value="train">{t.datasets.filterTrain}</option>
                </select>
              </div>

              <span className={styles.tableCount}>
                {t.datasets.showing(filteredSnapshots.length, rawList.length)}
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
                    <th scope="col" className={styles.colRight}>{t.datasets.frozenCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSnapshots.map((s) => {
                    const snapId = (s as { snapshot_id?: string }).snapshot_id || s.id;
                    const lockedAt = s.frozen_at || (s as { locked_at?: string | null }).locked_at;
                    return (
                      <tr key={snapId}>
                        <td className={styles.boldCell}>{s.name}</td>
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
                        <td className={styles.colRight}>
                          {lockedAt ? (
                            <div className={styles.actionCellGroup}>
                              <span className={`${table.mono} ${styles.lockedMeta}`}>
                                <Lock size={12} aria-hidden />
                                {s.frozen_by ? `${s.frozen_by} · ${fmtDateTime(lockedAt)}` : t.datasets.lockedBadge}
                              </span>
                              <Link to={`/vision/models?golden=${snapId}`} className={styles.quickActionLink}>
                                {t.datasets.evalNowLink}
                              </Link>
                            </div>
                          ) : s.kind === 'golden' && canFreeze ? (
                            <ReasonAction
                              label={t.datasets.freeze}
                              variant="accent"
                              onStepUp={handleStepUp}
                              onSubmit={(reason) => freeze.mutateAsync({ id: s.id, reason })}
                            />
                          ) : s.kind === 'golden' ? (
                            <Badge tone="warning">{t.datasets.awaitingLeadFreeze}</Badge>
                          ) : (
                            <div className={styles.actionCellGroup}>
                              <Badge tone="neutral">{t.datasets.trainBadge}</Badge>
                              <Link to={`/vision/models?train=${snapId}`} className={styles.quickActionLink}>
                                {t.datasets.registerModelLink}
                              </Link>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
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
