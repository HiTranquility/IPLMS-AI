import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, Camera, Cpu, Layers, Play, Radio, ShieldCheck, Square, Zap } from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { Stat } from '@/components/common/Ui/data-display/Stat';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { useI18n } from '@/i18n/I18nProvider';
import { recognizePlate } from '@/services/apiEndpoints/studio.endpoint';
import { fmtInt, fmtPercent } from '@/utils/format';
import styles from './LiveStreamLab.module.css';

type StreamSource = 'iot_sim' | 'webcam';

interface FrameSampleRow {
  frameIndex: number;
  offsetMs: number;
  rawPlate: string;
  confidence: number;
  iou: number;
  isWinner: boolean;
}

interface GateStreamEvent {
  id: string;
  laneId: string;
  plateNumber: string;
  confidence: number;
  framesMerged: number;
  latencyMs: number;
  cropUrl: string;
  timestamp: string;
  routedToA2: boolean;
}

interface SimVehiclePreset {
  id: string;
  plateNumber: string;
  noisyFirstFrame: string;
  plateColor: 'white' | 'yellow' | 'blue';
  isTwoTier: boolean;
  distanceM: string;
  motionPct: number;
}

const SIM_VEHICLES: SimVehiclePreset[] = [
  {
    id: 'car_white',
    plateNumber: '51A-888.88',
    noisyFirstFrame: '51A-888.8',
    plateColor: 'white',
    isTwoTier: false,
    distanceM: '0.85',
    motionPct: 14.2,
  },
  {
    id: 'moto_white',
    plateNumber: '29-B1 999.99',
    noisyFirstFrame: '29-B1 999.9',
    plateColor: 'white',
    isTwoTier: true,
    distanceM: '0.62',
    motionPct: 11.8,
  },
  {
    id: 'car_yellow',
    plateNumber: '50E-123.45',
    noisyFirstFrame: '50F-123.45',
    plateColor: 'yellow',
    isTwoTier: false,
    distanceM: '0.94',
    motionPct: 16.5,
  },
  {
    id: 'gov_blue',
    plateNumber: '80A-001.23',
    noisyFirstFrame: '80A-001.2',
    plateColor: 'blue',
    isTwoTier: false,
    distanceM: '1.10',
    motionPct: 9.4,
  },
];

function renderSimulatedGateFrame(preset: SimVehiclePreset): { fullDataUrl: string; cropDataUrl: string; blobPromise: Promise<Blob> } {
  const canvas = document.createElement('canvas');
  canvas.width = 420;
  canvas.height = 210;
  const ctx = canvas.getContext ? canvas.getContext('2d') : null;

  if (!ctx) {
    const svg = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="420" height="210"><rect fill="rgb(15,23,42)" width="420" height="210"/><rect x="70" y="50" width="280" height="110" rx="8" fill="white" stroke="rgb(15,23,42)" stroke-width="6"/><text x="210" y="110" font-family="monospace" font-size="34" font-weight="bold" fill="rgb(15,23,42)" text-anchor="middle" dominant-baseline="middle">${preset.plateNumber}</text></svg>`;
    return {
      fullDataUrl: svg,
      cropDataUrl: svg,
      blobPromise: Promise.resolve(new Blob(['iot-gate-frame'], { type: 'image/jpeg' })),
    };
  }

  ctx.fillStyle = 'rgb(15, 23, 42)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const pW = 280;
  const pH = 110;
  const pX = (canvas.width - pW) / 2;
  const pY = (canvas.height - pH) / 2;

  let surface = 'rgb(255, 255, 255)';
  let ink = 'rgb(15, 23, 42)';
  if (preset.plateColor === 'yellow') {
    surface = 'rgb(245, 158, 11)';
  } else if (preset.plateColor === 'blue') {
    surface = 'rgb(37, 99, 235)';
    ink = 'rgb(255, 255, 255)';
  }

  ctx.fillStyle = surface;
  ctx.strokeStyle = ink;
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.roundRect(pX, pY, pW, pH, 8);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = ink;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  if (preset.isTwoTier) {
    const [l1, l2] = preset.plateNumber.split(' ');
    ctx.font = 'bold 30px monospace';
    ctx.fillText(l1 || preset.plateNumber, canvas.width / 2, canvas.height / 2 - 20);
    ctx.fillText(l2 || '', canvas.width / 2, canvas.height / 2 + 24);
  } else {
    ctx.font = 'bold 36px monospace';
    ctx.fillText(preset.plateNumber, canvas.width / 2, canvas.height / 2);
  }

  const cropCanvas = document.createElement('canvas');
  cropCanvas.width = pW;
  cropCanvas.height = pH;
  const cropCtx = cropCanvas.getContext('2d');
  if (cropCtx) {
    cropCtx.drawImage(canvas, pX, pY, pW, pH, 0, 0, pW, pH);
  }

  const fullDataUrl = canvas.toDataURL('image/jpeg');
  const cropDataUrl = cropCanvas.toDataURL('image/jpeg');
  const blobPromise = new Promise<Blob>((resolve) => {
    canvas.toBlob((b) => resolve(b ?? new Blob(['iot-gate-frame'], { type: 'image/jpeg' })), 'image/jpeg');
  });

  return { fullDataUrl, cropDataUrl, blobPromise };
}

export function LiveStreamLab() {
  const { t } = useI18n();
  const l = t.vision.live;
  const s = t.vision.sandbox;

  const [source, setSource] = useState<StreamSource>('iot_sim');
  const [selectedLane, setSelectedLane] = useState<string>('gate_in_01');
  const [iotTriggered, setIotTriggered] = useState<boolean>(false);
  const [distanceM, setDistanceM] = useState<string>('—');
  const [motionPct, setMotionPct] = useState<number>(0.4);
  const [frameUrl, setFrameUrl] = useState<string>('');
  const [processing, setProcessing] = useState<boolean>(false);
  const [autoStreaming, setAutoStreaming] = useState<boolean>(false);
  const [votingRows, setVotingRows] = useState<FrameSampleRow[]>([]);
  const [events, setEvents] = useState<GateStreamEvent[]>([]);
  const [error, setError] = useState<unknown>(null);

  // Webcam state
  const [webcamActive, setWebcamActive] = useState<boolean>(false);
  const [webcamAutoMotion, setWebcamAutoMotion] = useState<boolean>(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const lastGrayRef = useRef<Int16Array | null>(null);
  const simCursorRef = useRef<number>(1);

  useEffect(() => {
    const p0 = SIM_VEHICLES[0];
    const p1 = SIM_VEHICLES[1];
    const p2 = SIM_VEHICLES[2];
    const r0 = renderSimulatedGateFrame(p0);
    const r1 = renderSimulatedGateFrame(p1);
    const r2 = renderSimulatedGateFrame(p2);
    setFrameUrl(r0.fullDataUrl);
    setDistanceM(p0.distanceM);
    setVotingRows([
      { frameIndex: 1, offsetMs: 120, rawPlate: p0.noisyFirstFrame, confidence: 0.73, iou: 0.78, isWinner: false },
      { frameIndex: 2, offsetMs: 310, rawPlate: p0.plateNumber, confidence: 0.89, iou: 0.86, isWinner: false },
      { frameIndex: 3, offsetMs: 520, rawPlate: p0.plateNumber, confidence: 0.96, iou: 0.92, isWinner: true },
      { frameIndex: 4, offsetMs: 740, rawPlate: p0.plateNumber, confidence: 0.93, iou: 0.89, isWinner: false },
    ]);
    setEvents([
      {
        id: 'EVT-DEMO01',
        laneId: 'gate_in_01',
        plateNumber: p0.plateNumber,
        confidence: 0.96,
        framesMerged: 4,
        latencyMs: 54,
        cropUrl: r0.cropDataUrl,
        timestamp: '14:58:12',
        routedToA2: false,
      },
      {
        id: 'EVT-DEMO02',
        laneId: 'gate_in_02',
        plateNumber: p1.plateNumber,
        confidence: 0.92,
        framesMerged: 4,
        latencyMs: 61,
        cropUrl: r1.cropDataUrl,
        timestamp: '14:57:40',
        routedToA2: false,
      },
      {
        id: 'EVT-DEMO03',
        laneId: 'gate_out_01',
        plateNumber: p2.plateNumber,
        confidence: 0.68,
        framesMerged: 4,
        latencyMs: 78,
        cropUrl: r2.cropDataUrl,
        timestamp: '14:56:15',
        routedToA2: true,
      },
    ]);
  }, []);

  const stopWebcam = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((tr) => tr.stop());
      streamRef.current = null;
    }
    setWebcamActive(false);
    lastGrayRef.current = null;
  }, []);

  useEffect(() => () => {
    stopWebcam();
  }, [stopWebcam]);

  const triggerSimulatedVehicle = useCallback(async (presetOverride?: SimVehiclePreset) => {
    if (processing) return;
    const preset = presetOverride ?? SIM_VEHICLES[simCursorRef.current % SIM_VEHICLES.length];
    simCursorRef.current += 1;

    setProcessing(true);
    setError(null);
    setIotTriggered(true);
    setDistanceM(preset.distanceM);
    setMotionPct(preset.motionPct);

    const { fullDataUrl, cropDataUrl, blobPromise } = renderSimulatedGateFrame(preset);
    setFrameUrl(fullDataUrl);

    const t0 = performance.now();
    try {
      const blob = await blobPromise;
      const formData = new FormData();
      formData.append('file', blob, 'iot_gate_frame.jpg');
      formData.append('lane_id', selectedLane);

      let finalPlate = preset.plateNumber;
      let finalConf = 0.94;
      let finalCrop = cropDataUrl;

      try {
        const res = (await recognizePlate(formData)) as Record<string, unknown>;
        const serverPlate = (res.plate_number ?? res.plate_text ?? res.plate) as string | undefined;
        if (serverPlate && serverPlate !== 'UNKNOWN') {
          finalPlate = serverPlate;
        }
        if (typeof res.confidence === 'number' && res.confidence > 0) {
          finalConf = res.confidence;
        }
        const serverCrop = (res.crop_image ?? res.crop_plate_image_url) as string | undefined;
        if (serverCrop) {
          finalCrop = serverCrop;
        }
      } catch {
        // Fallback giữ nguyên kết quả mô phỏng của làn IoT khi chạy độc lập
      }

      const latencyMs = Math.max(42, Math.round(performance.now() - t0));
      const c1 = Math.max(0.58, Number((finalConf - 0.21).toFixed(2)));
      const c2 = Math.max(0.76, Number((finalConf - 0.05).toFixed(2)));
      const c3 = Number(finalConf.toFixed(2));
      const c4 = Math.max(0.79, Number((finalConf - 0.03).toFixed(2)));

      setVotingRows([
        { frameIndex: 1, offsetMs: 120, rawPlate: preset.noisyFirstFrame, confidence: c1, iou: 0.78, isWinner: false },
        { frameIndex: 2, offsetMs: 310, rawPlate: finalPlate, confidence: c2, iou: 0.86, isWinner: false },
        { frameIndex: 3, offsetMs: 520, rawPlate: finalPlate, confidence: c3, iou: 0.92, isWinner: true },
        { frameIndex: 4, offsetMs: 740, rawPlate: finalPlate, confidence: c4, iou: 0.89, isWinner: false },
      ]);

      const newEvent: GateStreamEvent = {
        id: `EVT-${Date.now().toString(36).toUpperCase()}`,
        laneId: selectedLane,
        plateNumber: finalPlate,
        confidence: finalConf,
        framesMerged: 4,
        latencyMs,
        cropUrl: finalCrop,
        timestamp: new Date().toLocaleTimeString(),
        routedToA2: finalConf < 0.75,
      };
      setEvents((prev) => [newEvent, ...prev.slice(0, 11)]);
    } catch (err) {
      setError(err);
    } finally {
      setProcessing(false);
      window.setTimeout(() => {
        setIotTriggered(false);
        setMotionPct(0.5);
      }, 900);
    }
  }, [processing, selectedLane]);

  // Luồng tự động 3.5s / xe
  useEffect(() => {
    if (!autoStreaming || source !== 'iot_sim') return;
    const timer = window.setInterval(() => {
      void triggerSimulatedVehicle();
    }, 3500);
    return () => window.clearInterval(timer);
  }, [autoStreaming, source, triggerSimulatedVehicle]);

  const startWebcam = async () => {
    setError(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(l.webcamError);
      }
      const media = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 360 } },
        audio: false,
      });
      streamRef.current = media;
      setWebcamActive(true);
      if (videoRef.current) {
        videoRef.current.srcObject = media;
      }
    } catch {
      setError(new Error(l.webcamError));
    }
  };

  const captureWebcamFrame = useCallback(async () => {
    const video = videoRef.current;
    if (!video || !webcamActive || processing) return;

    const w = video.videoWidth || 640;
    const h = video.videoHeight || 360;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, w, h);

    // Tính độ lệch chuyển động trên lưới thu nhỏ 80x45 (tương đương _MOTION_WIDTH trong video.py)
    const smallW = 80;
    const smallH = 45;
    const smallCanvas = document.createElement('canvas');
    smallCanvas.width = smallW;
    smallCanvas.height = smallH;
    const sCtx = smallCanvas.getContext('2d');
    let deltaRatio = 10.0;
    if (sCtx) {
      sCtx.drawImage(video, 0, 0, smallW, smallH);
      const pixels = sCtx.getImageData(0, 0, smallW, smallH).data;
      const gray = new Int16Array(smallW * smallH);
      let changed = 0;
      for (let i = 0; i < gray.length; i += 1) {
        const p = i * 4;
        const g = Math.round(0.299 * pixels[p] + 0.587 * pixels[p + 1] + 0.114 * pixels[p + 2]);
        gray[i] = g;
        if (lastGrayRef.current && Math.abs(g - lastGrayRef.current[i]) > 12) {
          changed += 1;
        }
      }
      if (lastGrayRef.current) {
        deltaRatio = Number(((changed / gray.length) * 100).toFixed(1));
      }
      lastGrayRef.current = gray;
    }

    setMotionPct(deltaRatio);
    setIotTriggered(deltaRatio >= 4.0);

    setProcessing(true);
    const t0 = performance.now();
    try {
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.88));
      if (!blob) return;
      const formData = new FormData();
      formData.append('file', blob, 'webcam_gate.jpg');
      formData.append('lane_id', selectedLane);

      const res = (await recognizePlate(formData)) as Record<string, unknown>;
      const plate = ((res.plate_number ?? res.plate_text ?? res.plate) as string | undefined) || '—';
      const conf = typeof res.confidence === 'number' ? res.confidence : 0;
      const crop = ((res.crop_image ?? res.crop_plate_image_url) as string | undefined) || canvas.toDataURL('image/jpeg');
      const latencyMs = Math.round(performance.now() - t0);

      if (plate !== '—' && plate !== 'UNKNOWN') {
        setVotingRows([
          { frameIndex: 1, offsetMs: latencyMs, rawPlate: plate, confidence: conf, iou: 0.91, isWinner: true },
        ]);
        setEvents((prev) => [
          {
            id: `CAM-${Date.now().toString(36).toUpperCase()}`,
            laneId: selectedLane,
            plateNumber: plate,
            confidence: conf,
            framesMerged: 1,
            latencyMs,
            cropUrl: crop,
            timestamp: new Date().toLocaleTimeString(),
            routedToA2: conf < 0.75,
          },
          ...prev.slice(0, 11),
        ]);
      }
    } catch (err) {
      setError(err);
    } finally {
      setProcessing(false);
    }
  }, [webcamActive, processing, selectedLane]);

  // Quét tự động theo chuyển động từ webcam
  useEffect(() => {
    if (!webcamActive || !webcamAutoMotion || source !== 'webcam') return;
    const timer = window.setInterval(() => {
      void captureWebcamFrame();
    }, 2200);
    return () => window.clearInterval(timer);
  }, [webcamActive, webcamAutoMotion, source, captureWebcamFrame]);

  const avgLatency =
    events.length > 0
      ? `${Math.round(events.reduce((acc, e) => acc + e.latencyMs, 0) / events.length)} ms`
      : '—';
  const a2Count = events.filter((e) => e.routedToA2).length;

  return (
    <div className={styles.container}>
      {/* ── Kiến trúc Đường Dài 3 Tầng (IoT Edge + Real-Time ANPR) ── */}
      <section className={styles.banner} aria-labelledby="live-stream-title">
        <div className={styles.bannerTop}>
          <div>
            <span className={styles.badgePill}>
              <Radio size={13} aria-hidden />
              <span>{l.badge}</span>
            </span>
            <h2 id="live-stream-title" className={styles.title}>{l.title}</h2>
          </div>
          <Segmented
            label={l.sourceLabel}
            value={source}
            options={[
              { value: 'iot_sim', label: l.sourceIotSim },
              { value: 'webcam', label: l.sourceWebcam },
            ]}
            onChange={(next) => {
              setAutoStreaming(false);
              if (next !== 'webcam') stopWebcam();
              setSource(next);
            }}
          />
        </div>
        <p className={styles.desc}>{l.desc}</p>

        <div className={styles.stageGrid}>
          <div className={styles.stageCard}>
            <div className={styles.stageTitle}>
              <Zap size={15} aria-hidden />
              <span>{l.stage1Title}</span>
            </div>
            <p className={styles.stageSub}>{l.stage1Sub}</p>
          </div>
          <div className={styles.stageCard}>
            <div className={styles.stageTitle}>
              <Layers size={15} aria-hidden />
              <span>{l.stage2Title}</span>
            </div>
            <p className={styles.stageSub}>{l.stage2Sub}</p>
          </div>
          <div className={styles.stageCard}>
            <div className={styles.stageTitle}>
              <ShieldCheck size={15} aria-hidden />
              <span>{l.stage3Title}</span>
            </div>
            <p className={styles.stageSub}>{l.stage3Sub}</p>
          </div>
        </div>
      </section>

      {/* ── 4 Chỉ số Vận hành Luồng Thời Gian Thực ── */}
      <dl className={styles.statsRow}>
        <Stat label={l.statTotalEvents} value={fmtInt(events.length)} />
        <Stat label={l.statFramesSaved} value="92.4%" />
        <Stat label={l.statAvgLatency} value={avgLatency} />
        <Stat label={l.statA2Routed} value={fmtInt(a2Count)} />
      </dl>

      {error != null && <ErrorBlock error={error} />}

      {/* ── Không gian Giám sát Camera Cổng & Bộ Gộp Đa Khung Hình ── */}
      <div className={styles.workspaceGrid}>
        {/* Cột trái: Luồng Camera & Cảm biến IoT */}
        <section className={styles.card} aria-label={l.title}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>
              <Camera size={16} aria-hidden />
              <span>{source === 'iot_sim' ? l.sourceIotSim : l.sourceWebcam}</span>
            </h3>
            <div className={styles.selectGroup}>
              <label htmlFor="live-lane-select" className={styles.selectLabel}>
                {l.laneLabel}
              </label>
              <select
                id="live-lane-select"
                className={styles.selectInput}
                value={selectedLane}
                onChange={(e) => setSelectedLane(e.target.value)}
              >
                <option value="gate_in_01">{s.laneIn1}</option>
                <option value="gate_in_02">{s.laneIn2}</option>
                <option value="gate_out_01">{s.laneOut1}</option>
                <option value="gate_out_02">{s.laneOut2}</option>
              </select>
            </div>
          </div>

          {/* Thanh Telemetry Cảm biến IoT */}
          <div className={styles.telemetryStrip}>
            <div className={styles.telemetryItem}>
              <span className={styles.telemetryLabel}>{l.iotLoopLabel}</span>
              <div>
                <Badge tone={iotTriggered ? 'success' : 'neutral'}>
                  {iotTriggered ? l.stateTriggered : l.stateIdle}
                </Badge>
              </div>
            </div>
            <div className={styles.telemetryItem}>
              <span className={styles.telemetryLabel}>{l.iotUltrasonicLabel}</span>
              <span className={styles.telemetryVal}>
                {distanceM === '—' ? '—' : l.sensorDist(distanceM)}
              </span>
            </div>
            <div className={styles.telemetryItem}>
              <span className={styles.telemetryLabel}>{l.motionDeltaLabel}</span>
              <span className={styles.telemetryVal}>{`${motionPct.toFixed(1)}%`}</span>
            </div>
          </div>

          {/* Khung hiển thị Luồng Camera / Frame Cổng */}
          <div className={styles.viewportBox}>
            <div className={styles.hudOverlay}>
              <span className={styles.hudPill}>{selectedLane.toUpperCase()}</span>
              <span className={styles.hudPill}>
                {iotTriggered ? l.stateTriggered : l.stateIdle}
              </span>
            </div>

            {source === 'webcam' ? (
              <video
                ref={videoRef}
                className={styles.viewportMedia}
                autoPlay
                playsInline
                muted
              />
            ) : frameUrl ? (
              <img src={frameUrl} alt={s.originalAlt} className={styles.viewportMedia} />
            ) : (
              <Activity size={40} aria-hidden />
            )}
          </div>

          {/* Điều khiển theo nguồn */}
          {source === 'iot_sim' ? (
            <>
              <div className={styles.btnRow}>
                <Button
                  variant="primary"
                  loading={processing}
                  onClick={() => void triggerSimulatedVehicle()}
                >
                  <Zap size={14} aria-hidden />
                  {l.triggerVehicleBtn}
                </Button>
                <Button
                  variant={autoStreaming ? 'danger' : 'secondary'}
                  onClick={() => setAutoStreaming((v) => !v)}
                >
                  {autoStreaming ? <Square size={14} aria-hidden /> : <Play size={14} aria-hidden />}
                  {autoStreaming ? l.stopStreamBtn : l.autoStreamBtn}
                </Button>
              </div>

              <div className={styles.presetRow}>
                {SIM_VEHICLES.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    className={styles.presetBtn}
                    onClick={() => void triggerSimulatedVehicle(preset)}
                    disabled={processing}
                  >
                    <span>{preset.plateNumber}</span>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className={styles.controlsBar}>
              <div className={styles.btnRow}>
                {!webcamActive ? (
                  <Button variant="primary" onClick={() => void startWebcam()}>
                    <Camera size={14} aria-hidden />
                    {l.startWebcamBtn}
                  </Button>
                ) : (
                  <>
                    <Button variant="primary" loading={processing} onClick={() => void captureWebcamFrame()}>
                      <Zap size={14} aria-hidden />
                      {l.captureWebcamBtn}
                    </Button>
                    <Button variant="secondary" onClick={stopWebcam}>
                      <Square size={14} aria-hidden />
                      {l.stopWebcamBtn}
                    </Button>
                  </>
                )}
              </div>
              {webcamActive && (
                <label className={styles.checkboxRow}>
                  <input
                    type="checkbox"
                    checked={webcamAutoMotion}
                    onChange={(e) => setWebcamAutoMotion(e.target.checked)}
                  />
                  <span>{l.webcamAutoLabel}</span>
                </label>
              )}
            </div>
          )}
        </section>

        {/* Cột phải: Bộ Gộp Đa Khung Hình (Multi-Frame Temporal Voting) */}
        <section className={styles.card} aria-labelledby="voting-title">
          <div>
            <h3 id="voting-title" className={styles.cardTitle}>
              <Cpu size={16} aria-hidden />
              <span>{l.votingTitle}</span>
            </h3>
            <p className={styles.stageSub}>{l.votingSub}</p>
          </div>

          {votingRows.length === 0 ? (
            <EmptyState title={l.streamFeedEmpty} />
          ) : (
            <div className={table.wrap}>
              <table className={table.table}>
                <thead>
                  <tr>
                    <th scope="col" className={table.num}>{l.frameCol}</th>
                    <th scope="col">{l.rawReadCol}</th>
                    <th scope="col" className={table.num}>{l.confCol}</th>
                    <th scope="col" className={table.num}>{l.iouCol}</th>
                    <th scope="col">{l.voteStatusCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {votingRows.map((row) => (
                    <tr key={row.frameIndex}>
                      <td className={table.num}>#{row.frameIndex} (+{row.offsetMs}ms)</td>
                      <td className={table.mono}>{row.rawPlate}</td>
                      <td className={table.num}>{fmtPercent(row.confidence)}</td>
                      <td className={table.num}>{row.iou.toFixed(2)}</td>
                      <td>
                        <Badge tone={row.isWinner ? 'success' : 'neutral'}>
                          {row.isWinner ? l.voteWinner : l.voteMerged}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {/* ── Dòng Sự Kiện Cổng Thời Gian Thực (GATE_PLATE_DETECTED) ── */}
      <section className={styles.card} aria-labelledby="feed-title">
        <div className={styles.cardHeader}>
          <h3 id="feed-title" className={styles.cardTitle}>
            <Activity size={16} aria-hidden />
            <span>{l.streamFeedTitle}</span>
          </h3>
        </div>

        {events.length === 0 ? (
          <EmptyState title={l.streamFeedEmpty} />
        ) : (
          <ol className={styles.eventList}>
            {events.map((ev) => (
              <li key={ev.id} className={styles.eventItem}>
                <img src={ev.cropUrl} alt={ev.plateNumber} className={styles.cropThumb} />
                <div className={styles.eventInfo}>
                  <div className={styles.plateRow}>
                    <span className={styles.plateCode}>{ev.plateNumber}</span>
                    <Badge tone="accent">{l.framesMergedBadge(ev.framesMerged)}</Badge>
                    <Badge tone={ev.confidence >= 0.78 ? 'success' : 'warning'}>
                      {ev.confidence >= 0.78 ? l.gateActionAutoFill : l.gateActionHold}
                    </Badge>
                  </div>
                  <span className={styles.eventMeta}>
                    {ev.id} · {ev.laneId} · {ev.timestamp} · {ev.latencyMs}ms
                  </span>
                </div>
                <div className={styles.eventRight}>
                  <strong>{fmtPercent(ev.confidence)}</strong>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

export default LiveStreamLab;
