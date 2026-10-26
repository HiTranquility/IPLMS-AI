import {
  Activity,
  Cpu,
  HardDrive,
  Layers,
  Lock,
  Play,
  RefreshCw,
  ShieldCheck,
  Sliders,
  Trash2,
  Zap,
} from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useStepUpMutation } from '@/hooks/mutations/useAuthMutations';
import {
  useEngineAction,
  useRevokeSession,
  useUpdateComputeSettings,
  useUpdatePolicySettings,
} from '@/hooks/mutations/useToolMutations';
import {
  useActiveSessions,
  useEvalCandidates,
  useRuntimeSettings,
} from '@/hooks/queries/useToolQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { DASH, fmtDateTime } from '@/utils/format';
import styles from './SettingsPage.module.css';

type SettingsTab = 'compute' | 'policy' | 'security';
const TABS: SettingsTab[] = ['compute', 'policy', 'security'];

export function SettingsPage() {
  const { t } = useI18n();
  const s = t.settings;

  const [tab, setTab] = useState<SettingsTab>('compute');
  const [savedCompute, setSavedCompute] = useState(false);
  const [savedPolicy, setSavedPolicy] = useState(false);
  const [engineMsg, setEngineMsg] = useState(false);

  const settingsQuery = useRuntimeSettings();
  const sessionsQuery = useActiveSessions();
  const evalCandidatesQuery = useEvalCandidates();

  const updateCompute = useUpdateComputeSettings();
  const updatePolicy = useUpdatePolicySettings();
  const engineAction = useEngineAction();
  const revokeSession = useRevokeSession();
  const stepUp = useStepUpMutation();

  const data = settingsQuery.data;
  const hw = data?.hardware;
  const comp = data?.compute;
  const pol = data?.policy;
  const eng = data?.engines;

  // Compute state
  const [visionDevice, setVisionDevice] = useState('auto');
  const [onnxEnabled, setOnnxEnabled] = useState(true);
  const [warmupOnStart, setWarmupOnStart] = useState(true);
  const [llmProvider, setLlmProvider] = useState('ollama');
  const [llmModel, setLlmModel] = useState('qwen2.5:0.5b');
  const [gpuLayers, setGpuLayers] = useState(33);
  const [cpuThreads, setCpuThreads] = useState(4);
  const [ctxSize, setCtxSize] = useState(4096);
  const [parallelSlots, setParallelSlots] = useState(1);

  // Policy state
  const [ragMinSim, setRagMinSim] = useState(0.35);
  const [ragTopK, setRagTopK] = useState(5);
  const [llmTimeout, setLlmTimeout] = useState(60);
  const [llmMaxTokens, setLlmMaxTokens] = useState(1200);
  const [vehicleConf, setVehicleConf] = useState(0.6);
  const [defaultLane, setDefaultLane] = useState('gate_in_01');
  const [telemetryEnabled, setTelemetryEnabled] = useState(true);
  const [telemetryRetention, setTelemetryRetention] = useState(30);
  const [visionRetention, setVisionRetention] = useState(30);

  useEffect(() => {
    if (comp) {
      setVisionDevice(comp.vision_device);
      setOnnxEnabled(comp.onnx_enabled);
      setWarmupOnStart(comp.vision_warmup_on_start);
      setLlmProvider(comp.llm_provider);
      if (comp.llm_model) setLlmModel(comp.llm_model);
      setGpuLayers(comp.local_llm_gpu_layers);
      setCpuThreads(comp.local_llm_threads);
      setCtxSize(comp.local_llm_ctx_size);
      setParallelSlots(comp.local_llm_parallel_slots);
    }
  }, [comp]);

  useEffect(() => {
    if (pol) {
      setRagMinSim(pol.rag_min_similarity);
      setRagTopK(pol.rag_top_k);
      setLlmTimeout(pol.llm_timeout_seconds);
      setLlmMaxTokens(pol.llm_max_output_tokens);
      setVehicleConf(pol.vehicle_min_confidence);
      setDefaultLane(pol.default_lane_id);
      setTelemetryEnabled(pol.telemetry_enabled);
      setTelemetryRetention(pol.telemetry_retention_days);
      setVisionRetention(pol.vision_retention_days);
    }
  }, [pol]);

  const applyPreset = (preset: 'safe_4gb' | 'cpu_eco' | 'gpu_full') => {
    setSavedCompute(false);
    updateCompute.mutate(
      { preset },
      {
        onSuccess: () => setSavedCompute(true),
      },
    );
  };

  const submitCompute = (e: FormEvent) => {
    e.preventDefault();
    setSavedCompute(false);
    updateCompute.mutate(
      {
        vision_device: visionDevice,
        onnx_enabled: onnxEnabled,
        vision_warmup_on_start: warmupOnStart,
        // OpenAI chỉ bật qua env; API chỉ nhận ollama/local (A-54).
        ...(llmProvider === 'ollama' || llmProvider === 'local' ? { llm_provider: llmProvider } : {}),
        llm_model: llmModel,
        local_llm_gpu_layers: gpuLayers,
        local_llm_threads: cpuThreads,
        local_llm_ctx_size: ctxSize,
        local_llm_parallel_slots: parallelSlots,
      },
      {
        onSuccess: () => setSavedCompute(true),
      },
    );
  };

  // ai:policy:threshold cần step-up (ADR-0048 §4): lưu qua ReasonAction để nhập lý do + TOTP tại chỗ.
  const submitPolicy = async (reason: string) => {
    setSavedPolicy(false);
    await updatePolicy.mutateAsync({
      reason,
      rag_min_similarity: ragMinSim,
      rag_top_k: ragTopK,
      llm_timeout_seconds: llmTimeout,
      llm_max_output_tokens: llmMaxTokens,
      vehicle_min_confidence: vehicleConf,
      default_lane_id: defaultLane,
      telemetry_enabled: telemetryEnabled,
      telemetry_retention_days: telemetryRetention,
      vision_retention_days: visionRetention,
    });
    setSavedPolicy(true);
  };

  const handleEngine = (action: 'warmup' | 'unload') => {
    setEngineMsg(false);
    engineAction.mutate(action, {
      onSuccess: () => setEngineMsg(true),
    });
  };

  const vramPct =
    hw?.vram_total_mb && hw?.vram_used_mb != null
      ? Math.min(100, Math.round((hw.vram_used_mb / hw.vram_total_mb) * 100))
      : 0;

  return (
    <div className={styles.page}>
      <PageHeader
        title={s.title}
        description={s.desc}
        actions={
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              void settingsQuery.refetch();
              void sessionsQuery.refetch();
              void evalCandidatesQuery.refetch();
            }}
          >
            <RefreshCw size={14} aria-hidden />
            {t.tools.refreshStatus}
          </Button>
        }
      />

      {/* Thanh chuyển Tab */}
      <div
        className={styles.tabsBar}
        role="tablist"
        onKeyDown={(e) => {
          // WAI-ARIA tabs: mũi tên trái/phải chuyển tab và chuyển focus theo.
          if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
          const step = e.key === 'ArrowRight' ? 1 : -1;
          const next = TABS[(TABS.indexOf(tab) + step + TABS.length) % TABS.length];
          setTab(next);
          document.getElementById(`settings-tab-${next}`)?.focus();
        }}
      >
        <button
          type="button"
          role="tab"
          id="settings-tab-compute"
          aria-controls="settings-panel-compute"
          aria-selected={tab === 'compute'}
          tabIndex={tab === 'compute' ? 0 : -1}
          className={`${styles.tabBtn} ${tab === 'compute' ? styles.tabBtnActive : ''}`}
          onClick={() => setTab('compute')}
        >
          <Cpu size={15} aria-hidden />
          <span>{s.tabCompute}</span>
        </button>
        <button
          type="button"
          role="tab"
          id="settings-tab-policy"
          aria-controls="settings-panel-policy"
          aria-selected={tab === 'policy'}
          tabIndex={tab === 'policy' ? 0 : -1}
          className={`${styles.tabBtn} ${tab === 'policy' ? styles.tabBtnActive : ''}`}
          onClick={() => setTab('policy')}
        >
          <Sliders size={15} aria-hidden />
          <span>{s.tabPolicy}</span>
        </button>
        <button
          type="button"
          role="tab"
          id="settings-tab-security"
          aria-controls="settings-panel-security"
          aria-selected={tab === 'security'}
          tabIndex={tab === 'security' ? 0 : -1}
          className={`${styles.tabBtn} ${tab === 'security' ? styles.tabBtnActive : ''}`}
          onClick={() => setTab('security')}
        >
          <ShieldCheck size={15} aria-hidden />
          <span>{s.tabSecurity}</span>
        </button>
      </div>

      {settingsQuery.isPending && <Loading />}
      {settingsQuery.error && (
        <ErrorBlock error={settingsQuery.error} onRetry={() => void settingsQuery.refetch()} />
      )}

      {/* TAB 1: PHẦN CỨNG GPU / CPU / VRAM & ENGINE */}
      {tab === 'compute' && data && (
        <div role="tabpanel" id="settings-panel-compute" aria-labelledby="settings-tab-compute">
          <section className={styles.sectionCard}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>
                  <Activity size={18} aria-hidden />
                  <span>{s.hwTelemetryTitle}</span>
                </h2>
                <p className={styles.sectionSub}>{s.hwTelemetrySub}</p>
              </div>
              {engineMsg && <span className={styles.okBanner}>{s.engineActionOk}</span>}
            </div>

            <div className={styles.telemetryGrid}>
              {/* GPU & VRAM */}
              <div className={styles.telemetryBox}>
                <div className={styles.telemetryTop}>
                  <span className={styles.telemetryLabel}>
                    <Zap size={14} aria-hidden /> {s.gpuCardTitle}
                  </span>
                  <Badge tone={hw?.cuda_available ? 'success' : 'neutral'}>
                    {hw?.cuda_available ? 'CUDA ACTIVE' : 'CPU MODE'}
                  </Badge>
                </div>
                <div className={styles.telemetryPrimary}>
                  {hw?.gpu_name || s.gpuNoCuda}
                </div>
                {hw?.vram_total_mb != null && hw?.vram_used_mb != null && hw?.vram_free_mb != null ? (
                  <>
                    <div className={styles.progressTrack}>
                      <div className={styles.progressFill} style={{ width: `${vramPct}%` }} />
                    </div>
                    <span className={styles.telemetryMeta}>
                      {s.vramUsage(hw.vram_used_mb, hw.vram_total_mb, hw.vram_free_mb)}
                    </span>
                  </>
                ) : (
                  <span className={styles.telemetryMeta}>{DASH}</span>
                )}
              </div>

              {/* CPU & System RAM */}
              <div className={styles.telemetryBox}>
                <div className={styles.telemetryTop}>
                  <span className={styles.telemetryLabel}>
                    <Cpu size={14} aria-hidden /> {s.cpuCardTitle}
                  </span>
                  <Badge tone="neutral">
                    {hw?.cpu_logical_cores ? s.cpuCores(hw.cpu_logical_cores) : DASH}
                  </Badge>
                </div>
                <div className={styles.telemetryPrimary}>
                  {hw?.ram_used_percent != null ? `${hw.ram_used_percent}% RAM` : DASH}
                </div>
                {hw?.ram_total_mb != null && hw?.ram_available_mb != null && hw?.ram_used_percent != null ? (
                  <>
                    <div className={styles.progressTrack}>
                      <div className={styles.progressFill} style={{ width: `${hw.ram_used_percent}%` }} />
                    </div>
                    <span className={styles.telemetryMeta}>
                      {s.ramUsage(hw.ram_available_mb, hw.ram_total_mb, String(hw.ram_used_percent))}
                    </span>
                  </>
                ) : (
                  <span className={styles.telemetryMeta}>{DASH}</span>
                )}
              </div>

              {/* Vision Engine Memory Lifecycle */}
              <div className={styles.telemetryBox}>
                <div className={styles.telemetryTop}>
                  <span className={styles.telemetryLabel}>
                    <HardDrive size={14} aria-hidden /> {s.engineCardTitle}
                  </span>
                  <Badge tone={eng?.ocr_loaded ? 'success' : 'neutral'}>
                    {eng?.ocr_loaded ? t.studio.engineLoaded : t.studio.engineNotLoaded}
                  </Badge>
                </div>
                <div className={styles.telemetryPrimary}>
                  YOLO: {eng?.yolo_loaded ? t.studio.engineLoaded : t.studio.engineNotLoaded} · OCR:{' '}
                  {eng?.ocr_loaded ? t.studio.engineLoaded : t.studio.engineNotLoaded}
                </div>
                <div className={styles.engineActions}>
                  <Button
                    type="button"
                    variant="primary"
                    loading={engineAction.isPending && engineAction.variables === 'warmup'}
                    onClick={() => handleEngine('warmup')}
                  >
                    <Play size={13} aria-hidden />
                    {s.engineWarmupBtn}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    loading={engineAction.isPending && engineAction.variables === 'unload'}
                    onClick={() => handleEngine('unload')}
                  >
                    <Trash2 size={13} aria-hidden />
                    {s.engineUnloadBtn}
                  </Button>
                </div>
              </div>
            </div>
          </section>

          {/* 3 Cấu hình mẫu (Presets) */}
          <section className={styles.sectionCard}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>
                  <Layers size={18} aria-hidden />
                  <span>{s.presetsTitle}</span>
                </h2>
                <p className={styles.sectionSub}>{s.presetsSub}</p>
              </div>
            </div>

            <div className={styles.presetsGrid}>
              <div className={`${styles.presetCard} ${comp?.profile === 'safe_4gb' ? styles.presetCardActive : ''}`}>
                <div>
                  <h3 className={styles.presetTitle}>{s.presetSafeTitle}</h3>
                  <p className={styles.presetDesc}>{s.presetSafeDesc}</p>
                </div>
                <Button
                  type="button"
                  variant={comp?.profile === 'safe_4gb' ? 'accent' : 'secondary'}
                  loading={updateCompute.isPending && updateCompute.variables?.preset === 'safe_4gb'}
                  disabled={updateCompute.isPending}
                  aria-label={comp?.profile === 'safe_4gb' ? s.activePresetFor(s.presetSafeTitle) : s.applyPresetFor(s.presetSafeTitle)}
                  onClick={() => applyPreset('safe_4gb')}
                >
                  {comp?.profile === 'safe_4gb' ? s.activePresetBadge : s.applyPresetBtn}
                </Button>
              </div>

              <div className={`${styles.presetCard} ${comp?.profile === 'gpu_full' ? styles.presetCardActive : ''}`}>
                <div>
                  <h3 className={styles.presetTitle}>{s.presetGpuTitle}</h3>
                  <p className={styles.presetDesc}>{s.presetGpuDesc}</p>
                </div>
                <Button
                  type="button"
                  variant={comp?.profile === 'gpu_full' ? 'accent' : 'secondary'}
                  loading={updateCompute.isPending && updateCompute.variables?.preset === 'gpu_full'}
                  disabled={updateCompute.isPending}
                  aria-label={comp?.profile === 'gpu_full' ? s.activePresetFor(s.presetGpuTitle) : s.applyPresetFor(s.presetGpuTitle)}
                  onClick={() => applyPreset('gpu_full')}
                >
                  {comp?.profile === 'gpu_full' ? s.activePresetBadge : s.applyPresetBtn}
                </Button>
              </div>

              <div className={`${styles.presetCard} ${comp?.profile === 'cpu_eco' ? styles.presetCardActive : ''}`}>
                <div>
                  <h3 className={styles.presetTitle}>{s.presetCpuTitle}</h3>
                  <p className={styles.presetDesc}>{s.presetCpuDesc}</p>
                </div>
                <Button
                  type="button"
                  variant={comp?.profile === 'cpu_eco' ? 'accent' : 'secondary'}
                  loading={updateCompute.isPending && updateCompute.variables?.preset === 'cpu_eco'}
                  disabled={updateCompute.isPending}
                  aria-label={comp?.profile === 'cpu_eco' ? s.activePresetFor(s.presetCpuTitle) : s.applyPresetFor(s.presetCpuTitle)}
                  onClick={() => applyPreset('cpu_eco')}
                >
                  {comp?.profile === 'cpu_eco' ? s.activePresetBadge : s.applyPresetBtn}
                </Button>
              </div>
            </div>
          </section>

          {/* Form tinh chỉnh chuyên sâu GPU / CPU */}
          <form className={styles.sectionCard} onSubmit={submitCompute}>
            <h2 className={styles.sectionTitle}>
              <Sliders size={18} aria-hidden />
              <span>{s.computeFormTitle}</span>
            </h2>

            <div className={styles.formGrid}>
              <div className={styles.fieldBlock}>
                <label className={styles.fieldLabel} htmlFor="vision-device-select">
                  {s.visionDeviceLabel}
                </label>
                <select
                  id="vision-device-select"
                  className={styles.selectInput}
                  value={visionDevice}
                  onChange={(e) => setVisionDevice(e.target.value)}
                >
                  <option value="auto">{s.deviceAuto}</option>
                  <option value="cuda">{s.deviceCuda}</option>
                  <option value="cpu">{s.deviceCpu}</option>
                </select>
                <label className={styles.checkboxRow}>
                  <input
                    type="checkbox"
                    checked={onnxEnabled}
                    onChange={(e) => setOnnxEnabled(e.target.checked)}
                  />
                  <span>{s.onnxLabel}</span>
                </label>
                <label className={styles.checkboxRow}>
                  <input
                    type="checkbox"
                    checked={warmupOnStart}
                    onChange={(e) => setWarmupOnStart(e.target.checked)}
                  />
                  <span>{s.warmupOnStartLabel}</span>
                </label>
              </div>

              <div className={styles.fieldBlock}>
                <label className={styles.fieldLabel} htmlFor="llm-provider-select">
                  {s.llmProviderLabel}
                </label>
                <select
                  id="llm-provider-select"
                  className={styles.selectInput}
                  value={llmProvider}
                  onChange={(e) => setLlmProvider(e.target.value)}
                >
                  <option value="ollama">Ollama Local (127.0.0.1:11434)</option>
                  <option value="local">Local llama-server (127.0.0.1:8005)</option>
                  <option value="openai" disabled>{s.providerOpenai}</option>
                </select>
                <p className={styles.fieldHint}>{s.providerOpenaiEnvOnly}</p>
              </div>

              <div className={styles.fieldBlock}>
                <label className={styles.fieldLabel} htmlFor="llm-model-input">
                  {s.llmModelLabel}
                </label>
                <input
                  id="llm-model-input"
                  type="text"
                  className={styles.selectInput}
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                  placeholder="vd: qwen2.5:0.5b, qwen3:4b, gpt-4o-mini"
                />
                <p className={styles.fieldHint}>
                  {s.llmModelRunning} <strong className={styles.mono}>{comp?.llm_model || DASH}</strong>
                </p>
              </div>

              <div className={styles.fieldBlock}>
                <label className={styles.fieldLabel} htmlFor="gpu-layers-range">
                  {s.gpuLayersLabel(gpuLayers)}
                </label>
                <input
                  id="gpu-layers-range"
                  type="range"
                  min={0}
                  max={35}
                  step={1}
                  value={gpuLayers}
                  onChange={(e) => setGpuLayers(Number(e.target.value))}
                  className={styles.rangeInput}
                />
                <p className={styles.fieldHint}>{s.gpuLayersHint}</p>
              </div>

              <div className={styles.fieldBlock}>
                <label className={styles.fieldLabel} htmlFor="cpu-threads-range">
                  {s.cpuThreadsLabel(cpuThreads)}
                </label>
                <input
                  id="cpu-threads-range"
                  type="range"
                  min={1}
                  max={hw?.cpu_logical_cores || 16}
                  step={1}
                  value={cpuThreads}
                  onChange={(e) => setCpuThreads(Number(e.target.value))}
                  className={styles.rangeInput}
                />
              </div>

              <div className={styles.fieldBlock}>
                <label className={styles.fieldLabel} htmlFor="ctx-size-select">
                  {s.ctxSizeLabel}
                </label>
                <select
                  id="ctx-size-select"
                  className={styles.selectInput}
                  value={ctxSize}
                  onChange={(e) => setCtxSize(Number(e.target.value))}
                >
                  <option value={2048}>2048 tokens (VRAM Saver)</option>
                  <option value={4096}>4096 tokens (4GB VRAM Standard)</option>
                  <option value={8192}>8192 tokens (&gt;= 6GB VRAM)</option>
                </select>
              </div>

              <div className={styles.fieldBlock}>
                <label className={styles.fieldLabel} htmlFor="parallel-slots-select">
                  {s.parallelSlotsLabel}
                </label>
                <select
                  id="parallel-slots-select"
                  className={styles.selectInput}
                  value={parallelSlots}
                  onChange={(e) => setParallelSlots(Number(e.target.value))}
                >
                  <option value={1}>1 slot (-np 1 · ~270MB KV Cache)</option>
                  <option value={2}>2 slots (-np 2 · ~540MB KV Cache)</option>
                  <option value={4}>4 slots (-np 4 · ~1.1GB KV Cache)</option>
                </select>
              </div>
            </div>

            {updateCompute.error && <ErrorBlock error={updateCompute.error} />}
            { engineAction.error && <ErrorBlock error={engineAction.error} />}

            <div className={styles.formFooter}>
              <Button type="submit" variant="primary" loading={updateCompute.isPending && !updateCompute.variables?.preset} disabled={updateCompute.isPending}>
                {s.saveComputeBtn}
              </Button>
              {savedCompute && <span className={styles.okBanner}>{s.savedComputeMsg}</span>}
            </div>
          </form>
        </div>
      )}

      {/* TAB 2: NGƯỠNG AI, RAG & CHÍNH SÁCH LƯU TRỮ */}
      {tab === 'policy' && data && (
        <div role="tabpanel" id="settings-panel-policy" aria-labelledby="settings-tab-policy">
        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>
                <Sliders size={18} aria-hidden />
                <span>{s.policyFormTitle}</span>
              </h2>
              <p className={styles.sectionSub}>{s.policyFormSub}</p>
            </div>
          </div>

          <div className={styles.formGrid}>
            <div className={styles.fieldBlock}>
              <label className={styles.fieldLabel} htmlFor="rag-sim-range">
                {s.ragMinSimLabel(ragMinSim.toFixed(2))}
              </label>
              <input
                id="rag-sim-range"
                type="range"
                min={0.1}
                max={0.85}
                step={0.05}
                value={ragMinSim}
                onChange={(e) => setRagMinSim(Number(e.target.value))}
                className={styles.rangeInput}
              />
              <p className={styles.fieldHint}>{s.ragMinSimHint}</p>
            </div>

            <div className={styles.fieldBlock}>
              <label className={styles.fieldLabel} htmlFor="vehicle-conf-range">
                {s.vehicleConfLabel(vehicleConf.toFixed(2))}
              </label>
              <input
                id="vehicle-conf-range"
                type="range"
                min={0.2}
                max={0.95}
                step={0.05}
                value={vehicleConf}
                onChange={(e) => setVehicleConf(Number(e.target.value))}
                className={styles.rangeInput}
              />
            </div>

            <div className={styles.fieldBlock}>
              <label className={styles.fieldLabel} htmlFor="rag-topk-input">
                {s.ragTopKLabel}
              </label>
              <input
                id="rag-topk-input"
                type="number"
                min={1}
                max={20}
                value={ragTopK}
                onChange={(e) => setRagTopK(Number(e.target.value))}
                className={styles.numberInput}
              />
            </div>

            <div className={styles.fieldBlock}>
              <label className={styles.fieldLabel} htmlFor="llm-max-tokens-input">
                {s.llmMaxTokensLabel}
              </label>
              <input
                id="llm-max-tokens-input"
                type="number"
                min={128}
                max={8192}
                step={64}
                value={llmMaxTokens}
                onChange={(e) => setLlmMaxTokens(Number(e.target.value))}
                className={styles.numberInput}
              />
            </div>

            <div className={styles.fieldBlock}>
              <label className={styles.fieldLabel} htmlFor="llm-timeout-input">
                {s.llmTimeoutLabel}
              </label>
              <input
                id="llm-timeout-input"
                type="number"
                min={5}
                max={300}
                value={llmTimeout}
                onChange={(e) => setLlmTimeout(Number(e.target.value))}
                className={styles.numberInput}
              />
            </div>

            <div className={styles.fieldBlock}>
              <label className={styles.fieldLabel} htmlFor="default-lane-input">
                {s.defaultLaneLabel}
              </label>
              <input
                id="default-lane-input"
                type="text"
                maxLength={64}
                value={defaultLane}
                onChange={(e) => setDefaultLane(e.target.value)}
                className={styles.numberInput}
              />
            </div>

            <div className={styles.fieldBlock}>
              <label className={styles.fieldLabel} htmlFor="telemetry-ret-input">
                {s.telemetryRetentionLabel}
              </label>
              <input
                id="telemetry-ret-input"
                type="number"
                min={1}
                max={365}
                value={telemetryRetention}
                onChange={(e) => setTelemetryRetention(Number(e.target.value))}
                className={styles.numberInput}
              />
              <label className={styles.checkboxRow}>
                <input
                  type="checkbox"
                  checked={telemetryEnabled}
                  onChange={(e) => setTelemetryEnabled(e.target.checked)}
                />
                <span>{s.telemetryEnabledLabel}</span>
              </label>
            </div>

            <div className={styles.fieldBlock}>
              <label className={styles.fieldLabel} htmlFor="vision-ret-input">
                {s.visionRetentionLabel}
              </label>
              <input
                id="vision-ret-input"
                type="number"
                min={1}
                max={365}
                value={visionRetention}
                onChange={(e) => setVisionRetention(Number(e.target.value))}
                className={styles.numberInput}
              />
            </div>
          </div>

          <div className={styles.formFooter}>
            <ReasonAction
              label={s.savePolicyBtn}
              variant="primary"
              onStepUp={(code, reason) => stepUp.mutateAsync({ code, reason })}
              onSubmit={submitPolicy}
            />
            {savedPolicy && <span className={styles.okBanner}>{s.savedPolicyMsg}</span>}
          </div>
        </section>
        </div>
      )}

      {/* TAB 3: PHIÊN ĐĂNG NHẬP ĐANG HOẠT ĐỘNG & BỘ EVAL HỒI QUY */}
      {tab === 'security' && (
        <div role="tabpanel" id="settings-panel-security" aria-labelledby="settings-tab-security">
          <section className={styles.sectionCard}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>
                  <Lock size={18} aria-hidden />
                  <span>{s.sessionsTitle}</span>
                </h2>
                <p className={styles.sectionSub}>{s.sessionsSub}</p>
              </div>
            </div>

            {sessionsQuery.isPending && <Loading />}
            {sessionsQuery.error && (
              <ErrorBlock error={sessionsQuery.error} onRetry={() => void sessionsQuery.refetch()} />
            )}

            {sessionsQuery.data && (
              <div className={styles.tableWrap}>
                <table className={styles.table} aria-label={s.sessionsTitle}>
                  <thead>
                    <tr>
                      <th>{s.colSessionUser}</th>
                      <th>{s.colSessionCreated}</th>
                      <th>{s.colSessionLastSeen}</th>
                      <th>{s.colSessionSecurity}</th>
                      <th>{s.colSessionAction}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessionsQuery.data.map((sess, i) => (
                      <tr key={sess.session_id}>
                        <td>
                          <strong>{sess.display_name}</strong> ({sess.email}){' '}
                          {sess.is_current && <Badge tone="accent">{s.currentSessionBadge}</Badge>}
                        </td>
                        <td className={styles.mono}>{sess.created_at ? fmtDateTime(sess.created_at) : DASH}</td>
                        <td className={styles.mono}>{sess.last_seen_at ? fmtDateTime(sess.last_seen_at) : DASH}</td>
                        <td>
                          <Badge tone={sess.mfa_verified ? 'success' : 'warning'}>
                            {sess.mfa_verified ? s.mfaVerifiedBadge : s.mfaPendingBadge}
                          </Badge>
                        </td>
                        <td>
                          {!sess.is_current && (
                            <Button
                              type="button"
                              variant="danger"
                              aria-label={s.revokeSessionFor(
                                i + 1,
                                sess.display_name,
                                sess.created_at ? fmtDateTime(sess.created_at) : DASH,
                              )}
                              loading={
                                revokeSession.isPending &&
                                revokeSession.variables?.sessionId === sess.session_id
                              }
                              onClick={() => {
                                if (window.confirm(s.revokeSessionConfirm)) {
                                  revokeSession.mutate({ sessionId: sess.session_id });
                                }
                              }}
                            >
                              {s.revokeSessionBtn}
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className={styles.sectionCard}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>
                  <ShieldCheck size={18} aria-hidden />
                  <span>{s.evalCandidatesTitle}</span>
                </h2>
                <p className={styles.sectionSub}>{s.evalCandidatesSub}</p>
              </div>
            </div>

            {evalCandidatesQuery.data && evalCandidatesQuery.data.length === 0 && (
              <p className={styles.sectionSub}>{s.evalEmpty}</p>
            )}

            {evalCandidatesQuery.data && evalCandidatesQuery.data.length > 0 && (
              <div className={styles.tableWrap}>
                <table className={styles.table} aria-label={s.evalCandidatesTitle}>
                  <thead>
                    <tr>
                      <th>{s.colEvalQuery}</th>
                      <th>{s.colEvalBehavior}</th>
                      <th>{s.colEvalCategory}</th>
                      <th>{s.colEvalAt}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evalCandidatesQuery.data.map((item, idx) => (
                      <tr key={String(item.turn_id ?? idx)}>
                        <td>{String(item.query ?? '')}</td>
                        <td>
                          <Badge tone={item.expected_behavior === 'REFUSE' ? 'warning' : 'success'}>
                            {String(item.expected_behavior ?? 'ANSWER')}
                          </Badge>
                        </td>
                        <td className={styles.mono}>{String(item.category ?? 'regulation')}</td>
                        <td className={styles.mono}>
                          {item.promoted_at ? fmtDateTime(String(item.promoted_at)) : DASH}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export default SettingsPage;
