import { type FormEvent, useState } from 'react';
import {
  ArrowRight,
  Check,
  CheckCircle2,
  Code2,
  Copy,
  GitBranch,
  HelpCircle,
  MessageSquare,
  Play,
  RotateCcw,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { SimulatedBanner } from '@/components/common/Ui/feedback/SimulatedBanner';
import { useI18n } from '@/i18n/I18nProvider';
import { simulateDispute } from '@/services/apiEndpoints/studio.endpoint';
import { fmtInt } from '@/utils/format';
import type { DisputeStep } from './types';
import styles from './ChatStudio.module.css';

export interface DisputeSimulatorProps {
  onAskAboutDispute?: (summary: string) => void;
}

interface ScenarioPreset {
  id: string;
  name: string;
  disputeId: string;
  amount: number;
  reason: string;
}

export function DisputeSimulator({ onAskAboutDispute }: DisputeSimulatorProps) {
  const { t } = useI18n();
  const d = t.copilot.dispute;
  const presetScenarios: ScenarioPreset[] = [
    { id: 'sc1', name: d.sc1Name, disputeId: 'DSP-9821', amount: 35000, reason: d.sc1Reason },
    { id: 'sc2', name: d.sc2Name, disputeId: 'DSP-1044', amount: 250000, reason: d.sc2Reason },
    { id: 'sc3', name: d.sc3Name, disputeId: 'DSP-2091', amount: 50000, reason: d.sc3Reason },
  ];
  const [disputeId, setDisputeId] = useState('DSP-9821');
  const [claimedAmount, setClaimedAmount] = useState<number>(35000);
  const [claimReason, setClaimReason] = useState(d.defaultReason);
  const [hasCheckinSnapshot, setHasCheckinSnapshot] = useState(true);
  const [hasCheckoutSnapshot, setHasCheckoutSnapshot] = useState(true);

  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<unknown>(null);
  const [steps, setSteps] = useState<DisputeStep[] | null>(null);
  const [expandedJsonIdx, setExpandedJsonIdx] = useState<number | null>(null);
  const [copiedStepIdx, setCopiedStepIdx] = useState<number | null>(null);

  const applyPreset = (sc: ScenarioPreset) => {
    setDisputeId(sc.disputeId);
    setClaimedAmount(sc.amount);
    setClaimReason(sc.reason);
    setSteps(null);
  };

  const runSimulation = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!disputeId.trim() || isRunning) return;

    setIsRunning(true);
    setSteps(null);
    setRunError(null);
    // Chỉ hiện bước server trả về; lỗi hoặc rỗng thì báo, không dựng hành trình mẫu (ai bug-018).
    try {
      const result = await simulateDispute({
        dispute_id: disputeId,
        claimed_amount: claimedAmount,
        claim_reason: claimReason,
        has_checkin_snapshot: hasCheckinSnapshot,
        has_checkout_snapshot: hasCheckoutSnapshot,
      });
      if (!Array.isArray(result.steps) || result.steps.length === 0) {
        setRunError(new Error(t.studio.disputeNoSteps));
      } else {
        setSteps(result.steps);
      }
    } catch (err) {
      setRunError(err);
    } finally {
      setIsRunning(false);
    }
  };

  const handleCopyStepJson = (idx: number, data: Record<string, any>) => {
    navigator.clipboard?.writeText(JSON.stringify(data, null, 2));
    setCopiedStepIdx(idx);
    setTimeout(() => setCopiedStepIdx(null), 2000);
  };

  const handleSendToChat = () => {
    if (!steps) return;
    // Không gài sẵn kết luận nào; chỉ chuyển dữ kiện khách khai sang khung chat.
    const summary = d.askSummary(disputeId, fmtInt(claimedAmount), claimReason);
    onAskAboutDispute?.(summary);
  };

  return (
    <div className={styles.disputeSimulatorWrapper}>
      {/* 1. Header */}
      <div className={styles.dsHeader}>
        <div className={styles.dsTitleGroup}>
          <div className={styles.dsIconBox}>
            <GitBranch size={16} />
          </div>
          <div>
            <h4 className={styles.dsTitle}>{d.title}</h4>
            <span className={styles.dsSub}>
              {d.sub} • <code>ai ADR-0003: Bounded Workflow</code>
            </span>
          </div>
        </div>

        <span className={styles.dsBoundedBadge}>Human-in-the-loop</span>
      </div>

      <SimulatedBanner />

      {/* 2. Scenario Presets */}
      <div className={styles.scenarioBar}>
        <span className={styles.scenarioLabel}>{d.scenarios}</span>
        <div className={styles.scenarioBtnList}>
          {presetScenarios.map((sc) => (
            <button
              key={sc.id}
              type="button"
              className={`${styles.scenarioBtn} ${disputeId === sc.disputeId ? styles.scenarioBtnActive : ''}`}
              onClick={() => applyPreset(sc)}
            >
              {sc.name}
            </button>
          ))}
        </div>
      </div>

      {/* 3. Input Controls Form */}
      <form onSubmit={runSimulation} className={styles.dsForm}>
        <div className={styles.dsInputGrid}>
          <div className={styles.dsField}>
            <label htmlFor="disp-id" className={styles.dsLabel}>
              {d.ticketId}
            </label>
            <input
              id="disp-id"
              type="text"
              className={`${styles.dsTextInput} num`}
              value={disputeId}
              onChange={(e) => setDisputeId(e.target.value)}
              placeholder={d.ticketPlaceholder}
              required
            />
          </div>

          <div className={styles.dsField}>
            <label htmlFor="disp-amount" className={styles.dsLabel}>
              {d.amount}
            </label>
            <input
              id="disp-amount"
              type="number"
              step="5000"
              className={`${styles.dsTextInput} num`}
              value={claimedAmount}
              onChange={(e) => setClaimedAmount(parseFloat(e.target.value) || 0)}
              required
            />
          </div>
        </div>

        <div className={styles.dsField}>
          <label htmlFor="disp-reason" className={styles.dsLabel}>
            {d.reason}
          </label>
          <input
            id="disp-reason"
            type="text"
            className={styles.dsTextInput}
            value={claimReason}
            onChange={(e) => setClaimReason(e.target.value)}
            placeholder={d.reasonPlaceholder}
            required
          />
        </div>

        <div className={styles.dsCheckboxesRow}>
          <label className={styles.dsCheckboxLabel}>
            <input
              type="checkbox"
              checked={hasCheckinSnapshot}
              onChange={(e) => setHasCheckinSnapshot(e.target.checked)}
            />
            <span>{d.checkinPhoto}</span>
          </label>

          <label className={styles.dsCheckboxLabel}>
            <input
              type="checkbox"
              checked={hasCheckoutSnapshot}
              onChange={(e) => setHasCheckoutSnapshot(e.target.checked)}
            />
            <span>{d.checkoutPhoto}</span>
          </label>
        </div>

        <div className={styles.dsSubmitRow}>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={isRunning}
            className={styles.dsRunBtn}
          >
            <Play size={13} className={isRunning ? styles.spin : ''} />
            <span>{isRunning ? d.running : d.run}</span>
          </Button>

          {steps && (
            <button
              type="button"
              className={styles.dsResetBtn}
              onClick={() => setSteps(null)}
              title={d.reset}
              aria-label={d.resetAria}
            >
              <RotateCcw size={13} />
            </button>
          )}
        </div>
      </form>

      {/* 4. Đang chờ server */}
      {isRunning && (
        <div className={styles.runningProgressBox}>
          <div className={styles.runningNodePill}>
            <Sparkles size={13} className={styles.spin} />
            <span>{t.feedback.loading}</span>
          </div>
        </div>
      )}

      {runError !== null && !isRunning && <ErrorBlock error={runError} />}

      {/* 5. Các node server trả về */}
      {steps && (
        <div className={styles.workflowJourney}>
          <div className={styles.journeyHeader}>
            <span className={styles.journeyTitle}>
              <CheckCircle2 size={14} className={styles.successColor} /> {t.studio.disputeJourney(steps.length)}
            </span>
            <span className={`${styles.journeyNodesBadge} num`}>{t.studio.disputeNodes(steps.length)}</span>
          </div>

          <div className={styles.nodeTimeline}>
            {steps.map((st, idx) => {
              const isJsonExpanded = expandedJsonIdx === idx;
              const isCopied = copiedStepIdx === idx;
              const isPendingApproval = st.status === 'AWAITING_STAFF_SIGN_OFF';

              return (
                <div key={st.node} className={styles.nodeCardWrapper}>
                  {idx > 0 && (
                    <div className={styles.nodeConnector}>
                      <span className={styles.connectorLine} />
                      <ArrowRight size={12} className={styles.connectorArrow} />
                    </div>
                  )}

                  <div
                    className={`${styles.nodeCard} ${
                      isPendingApproval ? styles.nodeCardWarning : styles.nodeCardSuccess
                    }`}
                  >
                    <div className={styles.nodeCardHeader}>
                      <div className={styles.nodeNameGroup}>
                        <span className={`${styles.nodeStepNum} num`}>Node {st.step}</span>
                        <code className={styles.nodeName}>[{st.node}]</code>
                      </div>

                      <span
                        className={`${styles.nodeStatusPill} ${
                          isPendingApproval ? styles.statusPillWarning : styles.statusPillSuccess
                        } num`}
                      >
                        {st.status}
                      </span>
                    </div>

                    <p className={styles.nodeDescription}>{st.description}</p>

                    <div className={styles.nodeCardFooter}>
                      <button
                        type="button"
                        className={styles.toggleJsonBtn}
                        onClick={() => setExpandedJsonIdx(isJsonExpanded ? null : idx)}
                      >
                        <Code2 size={12} />
                        <span>{isJsonExpanded ? d.hideJson : d.showJson}</span>
                      </button>

                      {isJsonExpanded && (
                        <button
                          type="button"
                          className={styles.copyJsonBtn}
                          onClick={() => handleCopyStepJson(idx, st.data)}
                          title={d.copyNodeTitle}
                        >
                          {isCopied ? <Check size={11} className={styles.successColor} /> : <Copy size={11} />}
                          <span>{isCopied ? d.copied : d.copyJson}</span>
                        </button>
                      )}
                    </div>

                    {isJsonExpanded && (
                      <pre className={`${styles.jsonPre} num`}>
                        {JSON.stringify(st.data, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 6. Human Approval & Safety Rule Notice */}
          <div className={styles.safetyNoticeBox}>
            <div className={styles.safetyNoticeHeader}>
              <ShieldAlert size={14} className={styles.warningColor} />
              <span className={styles.safetyNoticeTitle}>{d.safetyTitle}</span>
            </div>
            <p className={styles.safetyNoticeText}>
              {d.safetyText} <strong>{d.safetySignoff}</strong>
              {d.safetyTail}
            </p>
          </div>

          {/* 7. Action: Send to chat */}
          {onAskAboutDispute && (
            <div className={styles.sendToChatRow}>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handleSendToChat}
                className={styles.sendToChatBtn}
              >
                <MessageSquare size={13} />
                <span>{d.askCopilot}</span>
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Empty state when not run yet */}
      {!steps && !isRunning && runError === null && (
        <div className={styles.emptySimulatorState}>
          <HelpCircle size={22} className={styles.emptyIcon} />
          <p className={styles.emptyText}>
            {d.emptyBefore} <strong>{d.run}</strong> {d.emptyAfter}
          </p>
        </div>
      )}
    </div>
  );
}

export default DisputeSimulator;
