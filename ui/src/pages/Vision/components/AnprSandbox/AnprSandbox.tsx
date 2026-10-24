import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import {
  AlertOctagon,
  Bike,
  Camera,
  CheckCircle,
  CheckCircle2,
  Crop,
  Image as ImageIcon,
  ImagePlus,
  Info,
  Play,
  Scan,
  SearchCheck,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from 'lucide-react';
import { Badge, type BadgeTone } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { Spinner } from '@/components/common/Ui/feedback/Spinner';
import { useI18n } from '@/i18n/I18nProvider';
import type { Messages } from '@/i18n/vi';
import { recognizePlate, verifyMatch } from '@/services/apiEndpoints/studio.endpoint';
import type {
  AnprResult,
  AntiFraudVerification,
  LaneOption,
  PlateColor,
  SamplePlatePreset,
  VehicleType,
} from './types';
import styles from './AnprSandbox.module.css';

type SandboxText = Messages['vision']['sandbox'];

function getPlateColorBadge(color: PlateColor, x: SandboxText): { label: string; tone: BadgeTone } {
  switch (color) {
    case 'yellow':
      return { label: x.colorYellow, tone: 'warning' };
    case 'blue':
      return { label: x.colorBlue, tone: 'accent' };
    case 'red':
      return { label: x.colorRed, tone: 'danger' };
    case 'white':
    default:
      return { label: x.colorWhite, tone: 'neutral' };
  }
}

function getVehicleTypeBadge(type: string, x: SandboxText): { label: string; tone: BadgeTone } {
  switch (type) {
    case 'car_sedan':
      return { label: 'Sedan', tone: 'success' };
    case 'car_suv':
      return { label: 'SUV', tone: 'success' };
    case 'motorbike':
      return { label: x.typeMoto, tone: 'accent' };
    case 'truck':
      return { label: x.typeTruck, tone: 'warning' };
    default:
      return { label: type, tone: 'neutral' };
  }
}

/** Số từ server; thiếu thì "—", không điền số mặc định (ai bug-018). */
const pct = (value: number | null | undefined) =>
  typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—';

export function AnprSandbox() {
  const { t } = useI18n();
  const x = t.vision.sandbox;
  const samplePresets: SamplePlatePreset[] = [
    { id: 'car_white', name: x.presetCar, plateNumber: '51A-888.88', vehicleType: 'car_sedan', plateColor: 'white', isTwoTier: false },
    { id: 'moto_white', name: x.presetMoto, plateNumber: '29-B1 999.99', vehicleType: 'motorbike', plateColor: 'white', isTwoTier: true },
    { id: 'car_yellow', name: x.presetTaxi, plateNumber: '50E-123.45', vehicleType: 'car_sedan', plateColor: 'yellow', isTwoTier: false },
    { id: 'gov_blue', name: x.presetGov, plateNumber: '80A-001.23', vehicleType: 'car_suv', plateColor: 'blue', isTwoTier: false },
  ];
  const laneOptions: LaneOption[] = [
    { id: 'gate_in_01', name: x.laneIn1 },
    { id: 'gate_in_02', name: x.laneIn2 },
    { id: 'gate_out_01', name: x.laneOut1 },
    { id: 'gate_out_02', name: x.laneOut2 },
  ];
  const vehicleOptions: { value: VehicleType; label: string }[] = [
    { value: 'car_sedan', label: x.vehSedan },
    { value: 'car_suv', label: x.vehSuv },
    { value: 'motorbike', label: x.vehMoto },
    { value: 'truck', label: x.vehTruck },
  ];
  const [currentBlob, setCurrentBlob] = useState<Blob | null>(null);
  const [originalImgUrl, setOriginalImgUrl] = useState<string>('');
  const [cropImgUrl, setCropImgUrl] = useState<string>('');
  const [selectedLane, setSelectedLane] = useState<string>('gate_in_01');
  const [activePresetId, setActivePresetId] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [isRecognizing, setIsRecognizing] = useState<boolean>(false);
  const [recognitionResult, setRecognitionResult] = useState<AnprResult | null>(null);
  const [recognitionError, setRecognitionError] = useState<unknown>(null);

  // Anti-fraud state
  const [fraudInType, setFraudInType] = useState<VehicleType>('car_sedan');
  const [fraudOutType, setFraudOutType] = useState<VehicleType>('motorbike');
  const [isVerifyingMatch, setIsVerifyingMatch] = useState<boolean>(false);
  const [fraudResult, setFraudResult] = useState<AntiFraudVerification | null>(null);
  const [fraudError, setFraudError] = useState<unknown>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Canvas license plate generator
  const generatePlateCanvas = useCallback((preset: SamplePlatePreset) => {
    const canvas = document.createElement('canvas');
    canvas.width = 400;
    canvas.height = 200;
    const ctx = canvas.getContext ? canvas.getContext('2d') : null;

    if (!ctx) {
      // jsdom environment fallback (allows headless tests to pass without node-canvas)
      const mockBlob = new Blob(['mock-plate'], { type: 'image/jpeg' });
      setCurrentBlob(mockBlob);
      const svgOriginal = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><rect fill="rgb(30,41,59)" width="400" height="200"/><rect x="60" y="45" width="280" height="110" rx="8" fill="white" stroke="rgb(15,23,42)" stroke-width="6"/><text x="200" y="105" font-family="monospace" font-size="34" font-weight="bold" fill="rgb(15,23,42)" text-anchor="middle" dominant-baseline="middle">${preset.plateNumber}</text></svg>`;
      const svgCrop = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="280" height="110"><rect width="280" height="110" rx="8" fill="white" stroke="rgb(15,23,42)" stroke-width="6"/><text x="140" y="60" font-family="monospace" font-size="34" font-weight="bold" fill="rgb(15,23,42)" text-anchor="middle" dominant-baseline="middle">${preset.plateNumber}</text></svg>`;
      setOriginalImgUrl(svgOriginal);
      setCropImgUrl(svgCrop);
      setActivePresetId(preset.id);
      setRecognitionResult(null);
      return;
    }

    // Vehicle bumper background (dark slate without hex)
    ctx.fillStyle = 'rgb(30, 41, 59)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Plate Dimensions
    const pW = 280;
    const pH = 110;
    const pX = (canvas.width - pW) / 2;
    const pY = (canvas.height - pH) / 2;

    // Plate surface color
    let surfaceColor = 'rgb(255, 255, 255)';
    let textColor = 'rgb(15, 23, 42)';
    if (preset.plateColor === 'yellow') {
      surfaceColor = 'rgb(245, 158, 11)';
      textColor = 'rgb(15, 23, 42)';
    } else if (preset.plateColor === 'blue') {
      surfaceColor = 'rgb(37, 99, 235)';
      textColor = 'rgb(255, 255, 255)';
    } else if (preset.plateColor === 'red') {
      surfaceColor = 'rgb(220, 38, 38)';
      textColor = 'rgb(255, 255, 255)';
    }

    // Plate rounded base
    ctx.fillStyle = surfaceColor;
    ctx.strokeStyle = textColor;
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.roundRect(pX, pY, pW, pH, 8);
    ctx.fill();
    ctx.stroke();

    // Inner thin border
    ctx.strokeStyle = 'rgb(71, 85, 105)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(pX + 5, pY + 5, pW - 10, pH - 10, 6);
    ctx.stroke();

    // Screw holes / registration rivets
    ctx.fillStyle = 'rgb(51, 65, 85)';
    ctx.beginPath();
    ctx.arc(pX + 16, pY + pH / 2, 3, 0, Math.PI * 2);
    ctx.arc(pX + pW - 16, pY + pH / 2, 3, 0, Math.PI * 2);
    ctx.fill();

    // Plate Text
    ctx.fillStyle = textColor;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    if (preset.isTwoTier) {
      const parts = preset.plateNumber.split(' ');
      const line1 = parts[0] || preset.plateNumber;
      const line2 = parts[1] || '';
      ctx.font = 'bold 30px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace';
      ctx.fillText(line1, canvas.width / 2, canvas.height / 2 - 20);
      ctx.fillText(line2, canvas.width / 2, canvas.height / 2 + 25);
    } else {
      ctx.font = 'bold 36px "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace';
      ctx.fillText(preset.plateNumber, canvas.width / 2, canvas.height / 2);
    }

    // Cropped plate canvas for simulated YOLO crop
    const cropCanvas = document.createElement('canvas');
    cropCanvas.width = pW;
    cropCanvas.height = pH;
    const cropCtx = cropCanvas.getContext('2d');
    if (cropCtx) {
      cropCtx.drawImage(canvas, pX, pY, pW, pH, 0, 0, pW, pH);
    }

    canvas.toBlob((blob) => {
      if (!blob) return;
      setCurrentBlob(blob);
      const url = URL.createObjectURL(blob);
      setOriginalImgUrl(url);
      setCropImgUrl(cropCanvas.toDataURL('image/jpeg'));
      setActivePresetId(preset.id);
      setRecognitionResult(null);
    }, 'image/jpeg');
  }, []);

  // Handle file select from input
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    loadLocalFile(file);
  };

  // Load selected or dropped file
  const loadLocalFile = (file: File) => {
    setCurrentBlob(file);
    setActivePresetId(null);
    setRecognitionResult(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      setOriginalImgUrl(dataUrl);

      // Create simulated crop from center
      const img = new Image();
      img.onload = () => {
        const cropCanvas = document.createElement('canvas');
        const cW = Math.round(img.width * 0.5);
        const cH = Math.round(img.height * 0.35);
        const cX = Math.round((img.width - cW) / 2);
        const cY = Math.round((img.height - cH) / 2);
        cropCanvas.width = cW;
        cropCanvas.height = cH;
        const cropCtx = cropCanvas.getContext('2d');
        if (cropCtx) {
          cropCtx.drawImage(img, cX, cY, cW, cH, 0, 0, cW, cH);
          setCropImgUrl(cropCanvas.toDataURL('image/jpeg'));
        }
      };
      img.src = dataUrl;
    };
    reader.readAsDataURL(file);
  };

  // Drag and drop handlers
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('image/')) {
      loadLocalFile(file);
    }
  };

  // Nhận diện: chỉ hiện kết quả server trả; lỗi/404 thì báo lỗi, không dựng biển số từ preset.
  const handleRunAnpr = async () => {
    if (!currentBlob) return;

    setIsRecognizing(true);
    setRecognitionResult(null);
    setRecognitionError(null);
    const startTime = performance.now();

    try {
      const formData = new FormData();
      formData.append('file', currentBlob, 'plate_input.jpg');
      if (selectedLane) {
        formData.append('lane_id', selectedLane);
      }
      const item = (await recognizePlate(formData)) as Record<string, unknown>;
      const plate = (item.plate_number ?? item.plate_text ?? item.plate) as string | undefined;
      setRecognitionResult({
        plateNumber: plate || '—',
        confidence: typeof item.confidence === 'number' ? item.confidence : undefined,
        plateColor: typeof item.plate_color === 'string' ? (item.plate_color.toLowerCase() as PlateColor) : undefined,
        vehicleType: typeof item.vehicle_type === 'string' ? item.vehicle_type : 'unknown',
        cropPlateImageUrl: (item.crop_plate_image_url as string | undefined) || cropImgUrl,
        originalImageUrl: originalImgUrl,
        eventId: item.event_id as string | undefined,
        timestamp: item.timestamp as string | undefined,
        latencyMs: Math.round(performance.now() - startTime),
      });
    } catch (err) {
      setRecognitionError(err);
    } finally {
      setIsRecognizing(false);
    }
  };

  // Đối chiếu chống tráo xe: chỉ hiện kết luận server trả; không tự so hai ô chọn rồi gán độ tương đồng.
  const handleVerifyAntiFraud = async () => {
    setIsVerifyingMatch(true);
    setFraudResult(null);
    setFraudError(null);

    try {
      const res = await verifyMatch({
        expected_vehicle_type: fraudInType,
        current_vehicle_type: fraudOutType,
      });
      setFraudResult({
        isMatched: res.is_matched,
        similarityScore: typeof res.similarity_score === 'number' ? res.similarity_score : undefined,
        mismatchReason: res.mismatch_reason || '—',
        expectedType: fraudInType,
        currentType: fraudOutType,
        verifiedAt: new Date().toISOString(),
      });
    } catch (err) {
      setFraudError(err);
    } finally {
      setIsVerifyingMatch(false);
    }
  };

  // Quick preset setup for fraud scenarios
  const applyFraudScenario = (inType: VehicleType, outType: VehicleType) => {
    setFraudInType(inType);
    setFraudOutType(outType);
    setFraudResult(null);
  };

  return (
    <div className={styles.sandboxContainer}>
      {/* ── Banner Introduction ── */}
      <section className={styles.introBanner} aria-label="ANPR Studio Introduction">
        <div className={styles.introHeader}>
          <div>
            <span className={styles.introCategory}>Computer Vision Studio · Pipeline 1</span>
            <h2 className={styles.introTitle}>Automatic Number Plate Recognition (ANPR) & Anti-Fraud Gatekeeper</h2>
            <p className={styles.introDesc}>
              {x.introDesc}
            </p>
          </div>
          <div className={styles.presetGroup}>
            {samplePresets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={`${styles.presetBtn} ${activePresetId === preset.id ? styles.presetBtnActive : ''}`}
                onClick={() => generatePlateCanvas(preset)}
                title={x.presetTitle(preset.plateNumber)}
              >
                {preset.vehicleType === 'motorbike' ? <Bike size={14} /> : <Sparkles size={14} />}
                <span>{preset.name}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ── Main Studio Grid ── */}
      <div className={styles.studioGrid}>
        {/* ── Left Column: Upload & Parameters ── */}
        <div className={styles.leftColumn}>
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h3 className={styles.cardTitle}>
                <UploadCloud size={16} />
                <span>{x.upload}</span>
              </h3>
              <span className={styles.cardSubtitle}>JPG, PNG, WEBP</span>
            </div>

            {/* Dropzone */}
            <div
              className={`${styles.dropzone} ${isDragOver ? styles.dropzoneDragOver : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  fileInputRef.current?.click();
                }
              }}
              aria-label={x.dropAria}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="visually-hidden"
                onChange={handleFileChange}
              />
              <ImagePlus size={36} className={styles.dropzoneIcon} />
              <p className={styles.dropzonePrompt}>
                {x.dropPrompt} <span className={styles.dropzoneLink}>{x.dropLink}</span>
              </p>
              <p className={styles.dropzoneHint}>{x.dropHint}</p>
            </div>

            {/* Parameters */}
            <div className={styles.paramGrid}>
              <div className={styles.paramField}>
                <label htmlFor="lane-select" className={styles.paramLabel}>
                  {x.laneId}
                </label>
                <select
                  id="lane-select"
                  className={styles.paramSelect}
                  value={selectedLane}
                  onChange={(e) => setSelectedLane(e.target.value)}
                >
                  {laneOptions.map((lane) => (
                    <option key={lane.id} value={lane.id}>
                      {lane.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.paramField}>
                <span className={styles.paramLabel}>{x.classifyStatus}</span>
                <div className={styles.paramBadgeStatus}>
                  <span className={styles.statusIndicatorDot} />
                  <span>{t.simulated.notReported}</span>
                </div>
              </div>
            </div>

            {/* Run Button */}
            <button
              type="button"
              className={styles.runBtn}
              onClick={handleRunAnpr}
              disabled={!currentBlob || isRecognizing}
            >
              {isRecognizing ? (
                <>
                  <Spinner size={16} />
                  <span>{x.processing}</span>
                </>
              ) : (
                <>
                  <Play size={16} />
                  <span>{x.run}</span>
                </>
              )}
            </button>
          </div>

          {/* Quick Tip */}
          <div className={styles.tipBox}>
            <Info size={16} className={styles.tipIcon} />
            <span>
              {x.tip}
            </span>
          </div>
        </div>

        {/* ── Right Column: Recognition Results & Visuals ── */}
        <div className={styles.rightColumn}>
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h3 className={styles.cardTitle}>
                <CheckCircle2 size={16} />
                <span>{x.resultTitle}</span>
              </h3>
              <span className="num">
                {recognitionResult?.latencyMs ? `${recognitionResult.latencyMs}ms` : x.waiting}
              </span>
            </div>

            {recognitionError !== null && <ErrorBlock error={recognitionError} />}

            {!recognitionResult && !originalImgUrl ? (
              <div className={styles.emptyState}>
                <Scan size={44} className={styles.emptyIcon} />
                <p className={styles.emptyTitle}>{x.emptyTitle}</p>
                <p className={styles.emptyDesc}>
                  {x.emptyDesc}
                </p>
              </div>
            ) : (
              <div className={styles.resultContent}>
                {/* Large License Plate Display */}
                <div className={styles.plateHighlightCard}>
                  <div className={styles.plateNumberBlock}>
                    <span className={styles.plateLabel}>{x.plateLabel}</span>
                    <div className={styles.vietnamPlatePlate}>
                      <span>{recognitionResult ? recognitionResult.plateNumber : x.scanning}</span>
                    </div>
                  </div>

                  {recognitionResult && (
                    <div className={styles.metaBadgeList}>
                      <div className={styles.metaItem}>
                        <span>{x.confidence}</span>
                        <span className={styles.metaValueStrong}>
                          {pct(recognitionResult.confidence)}
                        </span>
                      </div>
                      <div className={styles.metaItem}>
                        <span>{x.plateColor}</span>
                        {recognitionResult.plateColor ? (
                          <Badge tone={getPlateColorBadge(recognitionResult.plateColor, x).tone}>
                            {getPlateColorBadge(recognitionResult.plateColor, x).label}
                          </Badge>
                        ) : (
                          <span>—</span>
                        )}
                      </div>
                      <div className={styles.metaItem}>
                        <span>{x.classification}</span>
                        <Badge tone={getVehicleTypeBadge(recognitionResult.vehicleType, x).tone}>
                          {getVehicleTypeBadge(recognitionResult.vehicleType, x).label}
                        </Badge>
                      </div>
                    </div>
                  )}
                </div>

                {/* Dual Visuals */}
                <div className={styles.visualGrid}>
                  <div className={styles.visualCard}>
                    <span className={styles.visualTitle}>
                      <Camera size={14} />
                      <span>{x.original}</span>
                    </span>
                    <div className={styles.visualMediaBox}>
                      {originalImgUrl ? (
                        <img src={originalImgUrl} alt={x.originalAlt} className={styles.visualImg} />
                      ) : (
                        <ImageIcon size={32} className={styles.emptyIcon} />
                      )}
                    </div>
                  </div>

                  <div className={styles.visualCard}>
                    <span className={styles.visualTitle}>
                      <Crop size={14} />
                      <span>{x.crop}</span>
                    </span>
                    <div className={styles.visualMediaBox}>
                      {cropImgUrl ? (
                        <img src={cropImgUrl} alt={x.cropAlt} className={styles.visualImg} />
                      ) : (
                        <Scan size={32} className={styles.emptyIcon} />
                      )}
                    </div>
                  </div>
                </div>

                {recognitionResult && (
                  <div className={styles.metaFooter}>
                    <span>{x.event(recognitionResult.eventId ?? '—')}</span>
                    <span>{x.time(recognitionResult.timestamp ?? '—')}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Anti-Fraud Gatekeeper & Vehicle Matcher ── */}
      <section className={styles.antiFraudCard} aria-labelledby="antifraud-title">
        <div className={styles.antiFraudHeader}>
          <div>
            <h3 id="antifraud-title" className={styles.antiFraudTitle}>
              <ShieldCheck size={18} />
              <span>{x.fraudTitle}</span>
            </h3>
            <p className={styles.antiFraudDesc}>
              {x.fraudDescBefore} <strong>{x.fraudDescStrong}</strong>
              {x.fraudDescAfter}
            </p>
          </div>
          <Badge tone="danger">Anti-Fraud</Badge>
        </div>

        {/* Quick Scenarios */}
        <div className={styles.presetGroup}>
          <button
            type="button"
            className={styles.presetBtn}
            onClick={() => applyFraudScenario('car_sedan', 'motorbike')}
          >
            <ShieldAlert size={14} />
            <span>{x.scenario1}</span>
          </button>
          <button
            type="button"
            className={styles.presetBtn}
            onClick={() => applyFraudScenario('car_suv', 'car_suv')}
          >
            <CheckCircle size={14} />
            <span>{x.scenario2}</span>
          </button>
          <button
            type="button"
            className={styles.presetBtn}
            onClick={() => applyFraudScenario('car_sedan', 'truck')}
          >
            <AlertOctagon size={14} />
            <span>{x.scenario3}</span>
          </button>
        </div>

        {/* Match Select Inputs */}
        <div className={styles.fraudSelectGrid}>
          <div className={styles.fraudSelectBox}>
            <label htmlFor="fraud-in-select" className={styles.fraudSelectTitle}>
              {x.checkinType}
            </label>
            <select
              id="fraud-in-select"
              className={styles.paramSelect}
              value={fraudInType}
              onChange={(e) => setFraudInType(e.target.value as VehicleType)}
            >
              {vehicleOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.fraudSelectBox}>
            <label htmlFor="fraud-out-select" className={styles.fraudSelectTitle}>
              {x.checkoutType}
            </label>
            <select
              id="fraud-out-select"
              className={styles.paramSelect}
              value={fraudOutType}
              onChange={(e) => setFraudOutType(e.target.value as VehicleType)}
            >
              {vehicleOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Verification Button */}
        <button
          type="button"
          className={styles.verifyBtn}
          onClick={handleVerifyAntiFraud}
          disabled={isVerifyingMatch}
        >
          {isVerifyingMatch ? (
            <>
              <Spinner size={16} />
              <span>{x.matching}</span>
            </>
          ) : (
            <>
              <SearchCheck size={16} />
              <span>{x.runMatch}</span>
            </>
          )}
        </button>

        {fraudError !== null && <ErrorBlock error={fraudError} />}

        {/* Verification Result Box */}
        {fraudResult && (
          <div
            className={`${styles.fraudResultBox} ${
              fraudResult.isMatched ? styles.fraudResultSuccess : styles.fraudResultDanger
            }`}
          >
            <div
              className={`${styles.fraudResultHeader} ${
                fraudResult.isMatched
                  ? styles.fraudResultHeaderSuccess
                  : styles.fraudResultHeaderDanger
              }`}
            >
              {fraudResult.isMatched ? (
                <>
                  <CheckCircle size={18} />
                  <span>{x.matchOk}</span>
                </>
              ) : (
                <>
                  <AlertOctagon size={18} />
                  <span>{x.matchFraud(fraudResult.mismatchReason)}</span>
                </>
              )}
            </div>

            <p>
              {fraudResult.isMatched
                ? x.matchOkText(fraudResult.expectedType)
                : x.matchFraudText(fraudResult.expectedType, fraudResult.currentType)}
            </p>

            {!fraudResult.isMatched && (
              <p>
                <strong>{x.interventionTitle}</strong> {x.intervention}
              </p>
            )}

            <div className={styles.fraudMetricsRow}>
              <span>{x.similarity(pct(fraudResult.similarityScore))}</span>
              <span>{x.barrier(fraudResult.isMatched ? x.barrierOpen : x.barrierLocked)}</span>
              <span>{x.verifiedAt(fraudResult.verifiedAt)}</span>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
