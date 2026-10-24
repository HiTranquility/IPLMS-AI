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

const SAMPLE_PRESETS: SamplePlatePreset[] = [
  {
    id: 'car_white',
    name: 'Mẫu Ô Tô (51A-888.88)',
    plateNumber: '51A-888.88',
    vehicleType: 'car_sedan',
    plateColor: 'white',
    isTwoTier: false,
  },
  {
    id: 'moto_white',
    name: 'Mẫu Xe Máy (29-B1 999.99)',
    plateNumber: '29-B1 999.99',
    vehicleType: 'motorbike',
    plateColor: 'white',
    isTwoTier: true,
  },
  {
    id: 'car_yellow',
    name: 'Mẫu Taxi Vàng (50E-123.45)',
    plateNumber: '50E-123.45',
    vehicleType: 'car_sedan',
    plateColor: 'yellow',
    isTwoTier: false,
  },
  {
    id: 'gov_blue',
    name: 'Mẫu Cơ Quan Xanh (80A-001.23)',
    plateNumber: '80A-001.23',
    vehicleType: 'car_suv',
    plateColor: 'blue',
    isTwoTier: false,
  },
];

const LANE_OPTIONS: LaneOption[] = [
  { id: 'gate_in_01', name: 'gate_in_01 (Cổng vào 1)' },
  { id: 'gate_in_02', name: 'gate_in_02 (Cổng vào 2)' },
  { id: 'gate_out_01', name: 'gate_out_01 (Cổng ra 1)' },
  { id: 'gate_out_02', name: 'gate_out_02 (Cổng ra 2)' },
];

const VEHICLE_OPTIONS: { value: VehicleType; label: string }[] = [
  { value: 'car_sedan', label: 'Ô tô Sedan (car_sedan)' },
  { value: 'car_suv', label: 'Ô tô SUV (car_suv)' },
  { value: 'motorbike', label: 'Xe máy (motorbike)' },
  { value: 'truck', label: 'Xe tải (truck)' },
];

function getPlateColorBadge(color: PlateColor): { label: string; tone: BadgeTone } {
  switch (color) {
    case 'yellow':
      return { label: 'Vàng (Kinh doanh)', tone: 'warning' };
    case 'blue':
      return { label: 'Xanh (Cơ quan)', tone: 'accent' };
    case 'red':
      return { label: 'Đỏ (Quân đội)', tone: 'danger' };
    case 'white':
    default:
      return { label: 'Trắng (Dân sự)', tone: 'neutral' };
  }
}

function getVehicleTypeBadge(type: string): { label: string; tone: BadgeTone } {
  switch (type) {
    case 'car_sedan':
      return { label: 'Sedan', tone: 'success' };
    case 'car_suv':
      return { label: 'SUV', tone: 'success' };
    case 'motorbike':
      return { label: 'Xe máy', tone: 'accent' };
    case 'truck':
      return { label: 'Xe tải', tone: 'warning' };
    default:
      return { label: type, tone: 'neutral' };
  }
}

/** Số từ server; thiếu thì "—", không điền số mặc định (ai bug-018). */
const pct = (value: number | null | undefined) =>
  typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—';

export function AnprSandbox() {
  const { t } = useI18n();
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
              Quy trình nhận diện 2 tầng: <strong>YOLOv8</strong> phát hiện và cắt vùng biển số xe $\rightarrow$ <strong>EasyOCR</strong> đa tầng (full, crop, CLAHE) giải mã ký tự biển số $\rightarrow$ <strong>CNN</strong> phân loại phương tiện kết hợp chốt chặn chống tráo xe lúc Check-out.
            </p>
          </div>
          <div className={styles.presetGroup}>
            {SAMPLE_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={`${styles.presetBtn} ${activePresetId === preset.id ? styles.presetBtnActive : ''}`}
                onClick={() => generatePlateCanvas(preset)}
                title={`Nhấn để tạo biển số ${preset.plateNumber}`}
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
                <span>Tải ảnh xe vào bãi</span>
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
              aria-label="Kéo thả ảnh hoặc bấm để chọn tệp"
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
                Kéo thả ảnh xe vào đây hoặc <span className={styles.dropzoneLink}>chọn từ máy</span>
              </p>
              <p className={styles.dropzoneHint}>Tự động căn chỉnh ROI và cắt vùng biển số YOLOv8</p>
            </div>

            {/* Parameters */}
            <div className={styles.paramGrid}>
              <div className={styles.paramField}>
                <label htmlFor="lane-select" className={styles.paramLabel}>
                  Mã Làn (Lane ID)
                </label>
                <select
                  id="lane-select"
                  className={styles.paramSelect}
                  value={selectedLane}
                  onChange={(e) => setSelectedLane(e.target.value)}
                >
                  {LANE_OPTIONS.map((lane) => (
                    <option key={lane.id} value={lane.id}>
                      {lane.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.paramField}>
                <span className={styles.paramLabel}>Trạng thái phân loại xe</span>
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
                  <span>Đang xử lý (YOLO + EasyOCR)...</span>
                </>
              ) : (
                <>
                  <Play size={16} />
                  <span>Thực Hiện Nhận Diện (Run ANPR)</span>
                </>
              )}
            </button>
          </div>

          {/* Quick Tip */}
          <div className={styles.tipBox}>
            <Info size={16} className={styles.tipIcon} />
            <span>
              Ảnh đã xử lý và ảnh crop biển số sẽ được hệ thống trích xuất đặc trưng hình ảnh tự động để đối chiếu chống tráo xe lúc check-out.
            </span>
          </div>
        </div>

        {/* ── Right Column: Recognition Results & Visuals ── */}
        <div className={styles.rightColumn}>
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h3 className={styles.cardTitle}>
                <CheckCircle2 size={16} />
                <span>Kết Quả Nhận Diện Biển Số</span>
              </h3>
              <span className="num">
                {recognitionResult?.latencyMs ? `${recognitionResult.latencyMs}ms` : 'Chờ xử lý...'}
              </span>
            </div>

            {recognitionError !== null && <ErrorBlock error={recognitionError} />}

            {!recognitionResult && !originalImgUrl ? (
              <div className={styles.emptyState}>
                <Scan size={44} className={styles.emptyIcon} />
                <p className={styles.emptyTitle}>Chưa có ảnh xe được nạp</p>
                <p className={styles.emptyDesc}>
                  Hãy chọn một mẫu biển số Việt Nam ở trên hoặc tải ảnh chụp từ camera cổng bãi xe.
                </p>
              </div>
            ) : (
              <div className={styles.resultContent}>
                {/* Large License Plate Display */}
                <div className={styles.plateHighlightCard}>
                  <div className={styles.plateNumberBlock}>
                    <span className={styles.plateLabel}>Biển số nhận diện được</span>
                    <div className={styles.vietnamPlatePlate}>
                      <span>{recognitionResult ? recognitionResult.plateNumber : 'Chờ quét...'}</span>
                    </div>
                  </div>

                  {recognitionResult && (
                    <div className={styles.metaBadgeList}>
                      <div className={styles.metaItem}>
                        <span>Độ tin cậy:</span>
                        <span className={styles.metaValueStrong}>
                          {pct(recognitionResult.confidence)}
                        </span>
                      </div>
                      <div className={styles.metaItem}>
                        <span>Màu biển:</span>
                        {recognitionResult.plateColor ? (
                          <Badge tone={getPlateColorBadge(recognitionResult.plateColor).tone}>
                            {getPlateColorBadge(recognitionResult.plateColor).label}
                          </Badge>
                        ) : (
                          <span>—</span>
                        )}
                      </div>
                      <div className={styles.metaItem}>
                        <span>Phân loại:</span>
                        <Badge tone={getVehicleTypeBadge(recognitionResult.vehicleType).tone}>
                          {getVehicleTypeBadge(recognitionResult.vehicleType).label}
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
                      <span>Ảnh Gốc (Camera Cổng)</span>
                    </span>
                    <div className={styles.visualMediaBox}>
                      {originalImgUrl ? (
                        <img src={originalImgUrl} alt="Ảnh gốc camera" className={styles.visualImg} />
                      ) : (
                        <ImageIcon size={32} className={styles.emptyIcon} />
                      )}
                    </div>
                  </div>

                  <div className={styles.visualCard}>
                    <span className={styles.visualTitle}>
                      <Crop size={14} />
                      <span>Vùng Biển Số Cắt (YOLO Crop)</span>
                    </span>
                    <div className={styles.visualMediaBox}>
                      {cropImgUrl ? (
                        <img src={cropImgUrl} alt="Vùng biển số crop" className={styles.visualImg} />
                      ) : (
                        <Scan size={32} className={styles.emptyIcon} />
                      )}
                    </div>
                  </div>
                </div>

                {recognitionResult && (
                  <div className={styles.metaFooter}>
                    <span>Sự kiện: {recognitionResult.eventId ?? '—'}</span>
                    <span>Thời gian: {recognitionResult.timestamp ?? '—'}</span>
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
              <span>Đối Chiếu Loại Xe Check-in vs Check-out (Anti-Fraud Gatekeeper)</span>
            </h3>
            <p className={styles.antiFraudDesc}>
              Công cụ đối chiếu ngăn chặn <strong>tráo xe lúc check-out</strong>: Tự động so sánh đặc trưng và phân loại xe giữa lúc vào bãi và lúc ra cổng quẹt thẻ.
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
            <span>Kịch bản 1: Tráo Sedan $\rightarrow$ Xe máy (Gian lận)</span>
          </button>
          <button
            type="button"
            className={styles.presetBtn}
            onClick={() => applyFraudScenario('car_suv', 'car_suv')}
          >
            <CheckCircle size={14} />
            <span>Kịch bản 2: Hợp lệ SUV $\rightarrow$ SUV (Cho phép ra)</span>
          </button>
          <button
            type="button"
            className={styles.presetBtn}
            onClick={() => applyFraudScenario('car_sedan', 'truck')}
          >
            <AlertOctagon size={14} />
            <span>Kịch bản 3: Tráo Sedan $\rightarrow$ Xe tải (Lệch loại xe)</span>
          </button>
        </div>

        {/* Match Select Inputs */}
        <div className={styles.fraudSelectGrid}>
          <div className={styles.fraudSelectBox}>
            <label htmlFor="fraud-in-select" className={styles.fraudSelectTitle}>
              Loại xe Check-in (Lúc Vào Bãi)
            </label>
            <select
              id="fraud-in-select"
              className={styles.paramSelect}
              value={fraudInType}
              onChange={(e) => setFraudInType(e.target.value as VehicleType)}
            >
              {VEHICLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.fraudSelectBox}>
            <label htmlFor="fraud-out-select" className={styles.fraudSelectTitle}>
              Loại xe Check-out (Lúc Ra Cổng)
            </label>
            <select
              id="fraud-out-select"
              className={styles.paramSelect}
              value={fraudOutType}
              onChange={(e) => setFraudOutType(e.target.value as VehicleType)}
            >
              {VEHICLE_OPTIONS.map((opt) => (
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
              <span>Đang đối chiếu dữ liệu thị giác...</span>
            </>
          ) : (
            <>
              <SearchCheck size={16} />
              <span>Thực Hiện Đối Chiếu Loại Xe</span>
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
                  <span>HỢP LỆ — ĐỒNG NHẤT LOẠI XE</span>
                </>
              ) : (
                <>
                  <AlertOctagon size={18} />
                  <span>CẢNH BÁO GIAN LẬN: LỆCH LOẠI PHƯƠNG TIỆN ({fraudResult.mismatchReason})</span>
                </>
              )}
            </div>

            <p>
              {fraudResult.isMatched
                ? `Loại xe lúc vào và lúc ra trùng khớp (${fraudResult.expectedType}). Kiểm tra an toàn đạt yêu cầu — Barie tự động mở cho xe xuất bãi.`
                : `Xe vào đăng ký là "${fraudResult.expectedType}" nhưng xe ra cổng được phát hiện là "${fraudResult.currentType}". Khóa barie và kích hoạt cảnh báo nhân viên giám sát!`}
            </p>

            {!fraudResult.isMatched && (
              <p>
                <strong>Hành động can thiệp:</strong> Barie cổng bị cưỡng chế đóng, tự động trích xuất chuỗi hình ảnh chụp cổng vào / cổng ra gửi về luồng kiểm duyệt khiếu nại LangGraph.
              </p>
            )}

            <div className={styles.fraudMetricsRow}>
              <span>Độ tương đồng: {pct(fraudResult.similarityScore)}</span>
              <span>Barie: {fraudResult.isMatched ? 'MỞ CHO QUA' : 'KHÓA CHẶT (LOCKDOWN)'}</span>
              <span>Thời điểm kiểm tra: {fraudResult.verifiedAt}</span>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
