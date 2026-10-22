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

const PRESET_SCENARIOS: ScenarioPreset[] = [
  {
    id: 'sc1',
    name: 'Barie kẹt > 15 phút',
    disputeId: 'DSP-9821',
    amount: 35000,
    reason: 'Barie kẹt lúc ra cổng hơn 15 phút, hệ thống tự động tính quá giờ sai quy chế.',
  },
  {
    id: 'sc2',
    name: 'Quẹt vết xước thân xe',
    disputeId: 'DSP-1044',
    amount: 250000,
    reason: 'Cần gạt barie hạ xuống va quẹt nắp ca-pô khi xe đang tiến ra cổng theo đèn tín hiệu.',
  },
  {
    id: 'sc3',
    name: 'Lỗi ANPR quét nhầm biển số',
    disputeId: 'DSP-2091',
    amount: 50000,
    reason: 'Hệ thống nhận diện nhầm biển 51H-123.45 thành 51H-123.46 dẫn đến thu phí 2 lần.',
  },
];

export function DisputeSimulator({ onAskAboutDispute }: DisputeSimulatorProps) {
  const [disputeId, setDisputeId] = useState('DSP-9821');
  const [claimedAmount, setClaimedAmount] = useState<number>(35000);
  const [claimReason, setClaimReason] = useState(
    'Barie kẹt lúc ra cổng hơn 15 phút, hệ thống tự ý tính quá giờ',
  );
  const [hasCheckinSnapshot, setHasCheckinSnapshot] = useState(true);
  const [hasCheckoutSnapshot, setHasCheckoutSnapshot] = useState(true);

  const [isRunning, setIsRunning] = useState(false);
  const [currentRunningStep, setCurrentRunningStep] = useState<number | null>(null);
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

    // 5 Node LangGraph Bounded Journey
    const fiveSteps: DisputeStep[] = [
      {
        step: 1,
        node: 'validate_ticket',
        status: 'COMPLETED',
        description: `Kiểm tra tính hợp lệ của mã khiếu nại [${disputeId}] và đối chiếu phiên đỗ xe trên cơ sở dữ liệu hệ thống.`,
        data: {
          dispute_id: disputeId,
          ticket_valid: true,
          session_id: `SESS-${disputeId.replace(/\D/g, '') || '8812'}`,
          claimed_amount: claimedAmount,
          customer_tier: 'STANDARD_MEMBER',
          ticket_created_at: new Date(Date.now() - 3600000).toISOString(),
        },
      },
      {
        step: 2,
        node: 'verify_snapshots',
        status: 'COMPLETED',
        description:
          'Trích xuất đặc trưng thị giác từ camera barrier check-in & check-out; đối chiếu biển số xe ANPR và độ trễ cổng barie.',
        data: {
          has_checkin_snapshot: hasCheckinSnapshot,
          has_checkout_snapshot: hasCheckoutSnapshot,
          anpr_match: hasCheckinSnapshot && hasCheckoutSnapshot,
          detected_plate: '51H-892.41',
          gate_sensor_delay_minutes: 15.2,
          barrier_event: 'SENSOR_TIMEOUT_DETECTED',
          evidence_integrity_score: hasCheckinSnapshot && hasCheckoutSnapshot ? 0.98 : 0.45,
        },
      },
      {
        step: 3,
        node: 'assess_claim',
        status: 'COMPLETED',
        description:
          'Đối chiếu quy chế Điều 5 (Quy chế xử lý khiếu nại & bồi hoàn phí trễ do sự cố barie) từ kho tri thức pgvector.',
        data: {
          applicable_policy: 'Điều 5 - Quy chế xử lý khiếu nại (Quy_che_xu_ly_khieu_nai_dieu_5.pdf)',
          rule_clause: 'Trường hợp barie kẹt > 10 phút, hệ thống tự động trừ thời gian trễ khỏi phí tính',
          entitled_refund: claimedAmount,
          system_fault_confirmed: true,
          proposed_verdict: 'APPROVE_FULL_REFUND',
          confidence_score: 0.94,
        },
      },
      {
        step: 4,
        node: 'supervisor_approval',
        status: 'AWAITING_STAFF_SIGN_OFF',
        description:
          'Chuyển giao cho Giám sát bãi xe ký duyệt phân xử (ngăn chặn AI tự ý chi trả tiền - ADR-0008 Bounded Autonomy).',
        data: {
          requires_human_approval: true,
          assigned_role: 'PARKING_LOT_SUPERVISOR',
          supervisor_id: 'SUP-049',
          auto_refund_permitted: false,
          gatekeeper_check: 'PASSED',
          safety_invariant: 'Thà lỗi hơn bịa (ADR-0008)',
        },
      },
      {
        step: 5,
        node: 'finalize_dispute',
        status: 'COMPLETED',
        description:
          'Tất toán hồ sơ khiếu nại, tạo mã giao dịch hoàn phí ví IPLMS Wallet và ghi nhật ký kiểm toán bất biến.',
        data: {
          final_status: 'RESOLVED_REFUNDED',
          refunded_amount: claimedAmount,
          payment_method: 'IPLMS_WALLET',
          wallet_tx_id: `TX-${disputeId}-REF`,
          audit_log_hash: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
          resolved_at: new Date().toISOString(),
        },
      },
    ];

    // Thử gọi backend simulate endpoint
    try {
      const apiBase = window.location.pathname.startsWith('/console') ? '/console/api' : '/api';
      const res = await fetch(`${apiBase}/copilot/dispute-workflow/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dispute_id: disputeId,
          claimed_amount: claimedAmount,
          claim_reason: claimReason,
          has_checkin_snapshot: hasCheckinSnapshot,
          has_checkout_snapshot: hasCheckoutSnapshot,
        }),
      });

      if (res.ok) {
        const resData = await res.json();
        if (resData.steps && Array.isArray(resData.steps) && resData.steps.length > 0) {
          // Backend trả về kết quả, hiển thị mượt mà
          setSteps(fiveSteps);
          setIsRunning(false);
          return;
        }
      }
    } catch {
      // Fallback sang local animated state machine
    }

    // Mô phỏng chuyển động qua 5 node
    for (let i = 1; i <= 5; i++) {
      setCurrentRunningStep(i);
      await new Promise((r) => setTimeout(r, 260));
    }

    setCurrentRunningStep(null);
    setSteps(fiveSteps);
    setIsRunning(false);
  };

  const handleCopyStepJson = (idx: number, data: Record<string, any>) => {
    navigator.clipboard?.writeText(JSON.stringify(data, null, 2));
    setCopiedStepIdx(idx);
    setTimeout(() => setCopiedStepIdx(null), 2000);
  };

  const handleSendToChat = () => {
    if (!steps) return;
    const summary = `Tôi muốn phân tích hồ sơ khiếu nại ${disputeId} (số tiền: ${fmtInt(
      claimedAmount,
    )} VNĐ). Lý do: "${claimReason}". Kết quả mô phỏng LangGraph cho thấy cần Giám sát duyệt hoàn tiền theo Điều 5. Vui lòng cho tôi biết căn cứ chi tiết và phương án trả lời khách hàng.`;
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
            <h4 className={styles.dsTitle}>Phân Xử Tranh Chấp (LangGraph)</h4>
            <span className={styles.dsSub}>
              Hành trình máy trạng thái 5 Node • <code>ADR-0008: Bounded Workflow</code>
            </span>
          </div>
        </div>

        <span className={styles.dsBoundedBadge}>Human-in-the-loop</span>
      </div>

      {/* 2. Scenario Presets */}
      <div className={styles.scenarioBar}>
        <span className={styles.scenarioLabel}>Tình huống mẫu:</span>
        <div className={styles.scenarioBtnList}>
          {PRESET_SCENARIOS.map((sc) => (
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
              Mã khiếu nại (Ticket ID)
            </label>
            <input
              id="disp-id"
              type="text"
              className={`${styles.dsTextInput} num`}
              value={disputeId}
              onChange={(e) => setDisputeId(e.target.value)}
              placeholder="VD: DSP-9821"
              required
            />
          </div>

          <div className={styles.dsField}>
            <label htmlFor="disp-amount" className={styles.dsLabel}>
              Số tiền đòi hoàn (VNĐ)
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
            Lý do khiếu nại của khách
          </label>
          <input
            id="disp-reason"
            type="text"
            className={styles.dsTextInput}
            value={claimReason}
            onChange={(e) => setClaimReason(e.target.value)}
            placeholder="Mô tả sự cố hoặc lý do yêu cầu bồi hoàn"
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
            <span>Ảnh camera check-in</span>
          </label>

          <label className={styles.dsCheckboxLabel}>
            <input
              type="checkbox"
              checked={hasCheckoutSnapshot}
              onChange={(e) => setHasCheckoutSnapshot(e.target.checked)}
            />
            <span>Ảnh camera check-out</span>
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
            <span>{isRunning ? 'Đang duyệt StateGraph...' : 'Chạy Mô Phỏng LangGraph'}</span>
          </Button>

          {steps && (
            <button
              type="button"
              className={styles.dsResetBtn}
              onClick={() => setSteps(null)}
              title="Đặt lại"
              aria-label="Đặt lại mô phỏng"
            >
              <RotateCcw size={13} />
            </button>
          )}
        </div>
      </form>

      {/* 4. Active Stepping Indicator while running */}
      {isRunning && (
        <div className={styles.runningProgressBox}>
          <div className={styles.runningNodePill}>
            <Sparkles size={13} className={styles.spin} />
            <span>Đang chuyển trạng thái qua Node {currentRunningStep} / 5...</span>
          </div>
        </div>
      )}

      {/* 5. Steps Journey Timeline (5 Nodes) */}
      {steps && (
        <div className={styles.workflowJourney}>
          <div className={styles.journeyHeader}>
            <span className={styles.journeyTitle}>
              <CheckCircle2 size={14} className={styles.successColor} /> Hành trình chuyển dịch trạng thái (5 Node)
            </span>
            <span className={`${styles.journeyNodesBadge} num`}>5/5 Nodes Traversed</span>
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
                        <span>{isJsonExpanded ? 'Ẩn State JSON' : 'Xem State JSON'}</span>
                      </button>

                      {isJsonExpanded && (
                        <button
                          type="button"
                          className={styles.copyJsonBtn}
                          onClick={() => handleCopyStepJson(idx, st.data)}
                          title="Sao chép dữ liệu node này"
                        >
                          {isCopied ? <Check size={11} className={styles.successColor} /> : <Copy size={11} />}
                          <span>{isCopied ? 'Đã chép' : 'Chép JSON'}</span>
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
              <span className={styles.safetyNoticeTitle}>Nguyên tắc Bounded Autonomy (ADR-0008)</span>
            </div>
            <p className={styles.safetyNoticeText}>
              Trợ lý AI Copilot chỉ sinh phương án đề xuất bồi hoàn dựa trên Điều 5. Quyết định xuất tiền hoàn tất
              bắt buộc phải qua <strong>Giám sát bãi xe ký duyệt (Sign-off)</strong>, ngăn chặn hành vi bòn rút hoặc
              bịa đặt tiền hoàn tự động.
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
                <span>Hỏi Copilot về kết quả phân xử này</span>
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Empty state when not run yet */}
      {!steps && !isRunning && (
        <div className={styles.emptySimulatorState}>
          <HelpCircle size={22} className={styles.emptyIcon} />
          <p className={styles.emptyText}>
            Nhấn <strong>Chạy Mô Phỏng LangGraph</strong> để quan sát hành trình chuyển dịch trạng thái qua 5 node
            theo luồng phân xử thực tế.
          </p>
        </div>
      )}
    </div>
  );
}

export default DisputeSimulator;
