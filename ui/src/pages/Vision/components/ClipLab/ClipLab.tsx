import { useEffect, useRef, useState, type ChangeEvent } from 'react';
import { Film, Play } from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import { Stat } from '@/components/common/Ui/data-display/Stat';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { useI18n } from '@/i18n/I18nProvider';
import { recognizeClip } from '@/services/apiEndpoints/studio.endpoint';
import type { AnprClipResult } from '@/types/tool';
import { fmtInt, fmtPercent } from '@/utils/format';
import styles from './ClipLab.module.css';

const CLIP_TYPES = ['video/mp4', 'video/webm'];
type Mode = 'interval' | 'motion';

const fmtSeconds = (s: number) => `${s.toFixed(1)} s`;

/**
 * Đọc biển số từ clip (IPLMS REQ-021 A). Clip chỉ phát lại trong trình duyệt qua object URL;
 * server không lưu clip, mỗi sự kiện chỉ mang ảnh cắt biển của frame tốt nhất.
 */
export function ClipLab() {
  const { t } = useI18n();
  const x = t.vision.clip;
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [mode, setMode] = useState<Mode>('interval');
  const [result, setResult] = useState<AnprClipResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [running, setRunning] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files?.[0] ?? null;
    setResult(null);
    setDuration(null);
    if (picked && !CLIP_TYPES.includes(picked.type)) {
      setFile(null);
      setPreviewUrl(null);
      setError(new Error(x.wrongType));
      return;
    }
    setError(null);
    setFile(picked);
    setPreviewUrl(picked ? URL.createObjectURL(picked) : null);
  };

  const run = async () => {
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    form.append('mode', mode);
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await recognizeClip(form));
    } catch (err) {
      setError(err);
    } finally {
      setRunning(false);
    }
  };

  const seek = (s: number) => {
    if (videoRef.current) videoRef.current.currentTime = s;
  };

  // Trục thời gian theo độ dài clip trình duyệt đọc được; chưa có thì theo sự kiện cuối.
  const events = result?.events ?? [];
  const axis = Math.max(duration ?? 0, ...events.map((e) => e.end_time_s), 1);

  return (
    <section className={styles.lab} aria-labelledby="clip-title">
      <header>
        <h2 id="clip-title" className={styles.title}>{x.title}</h2>
        <p className={styles.note}>{x.desc}</p>
      </header>

      <div className={styles.controls}>
        <label className={styles.picker}>
          <Film size={18} aria-hidden />
          <span>{file ? file.name : x.pick}</span>
          <input type="file" accept={CLIP_TYPES.join(',')} onChange={onPick} aria-label={x.pick} />
        </label>
        <Segmented
          label={x.mode}
          value={mode}
          options={[
            { value: 'interval', label: x.modeInterval },
            { value: 'motion', label: x.modeMotion },
          ]}
          onChange={setMode}
        />
        <Button onClick={() => void run()} disabled={!file} loading={running}>
          {!running && <Play size={14} aria-hidden />}
          {running ? x.running : x.run}
        </Button>
      </div>
      {!file && <p className={styles.note}>{x.dropHint}</p>}

      {previewUrl && (
        <video
          ref={videoRef}
          className={styles.video}
          src={previewUrl}
          controls
          muted
          onLoadedMetadata={(e) => setDuration(Number.isFinite(e.currentTarget.duration) ? e.currentTarget.duration : null)}
        />
      )}

      {error != null && <ErrorBlock error={error} />}

      {result && (
        <>
          <dl className={styles.stats}>
            <Stat label={x.sampled} value={fmtInt(result.sampled_frames)} />
            <Stat label={x.reads} value={fmtInt(result.plate_reads)} />
            <Stat label={x.events} value={fmtInt(events.length)} />
            <Stat label={x.latency} value={fmtSeconds(result.latency_ms / 1000)} />
          </dl>

          {events.length === 0 ? (
            <EmptyState title={x.noEvents} />
          ) : (
            <>
              <h3 className={styles.subtitle}>{x.timeline}</h3>
              <div className={styles.track} role="group" aria-label={x.timeline}>
                {events.map((e, i) => (
                  <button
                    key={`${e.plate_number}-${e.start_time_s}`}
                    type="button"
                    className={styles.span}
                    style={{
                      left: `${(e.start_time_s / axis) * 100}%`,
                      width: `max(${((e.end_time_s - e.start_time_s) / axis) * 100}%, 6px)`,
                    }}
                    onClick={() => seek(e.best_time_s)}
                    aria-label={x.seek(e.plate_number, fmtSeconds(e.best_time_s))}
                    title={e.plate_number}
                  >
                    <span aria-hidden>{i + 1}</span>
                  </button>
                ))}
              </div>
              <div className={styles.axis} aria-hidden>
                <span>{fmtSeconds(0)}</span>
                <span>{fmtSeconds(axis)}</span>
              </div>

              <ol className={styles.events}>
                {events.map((e, i) => (
                  <li key={`${e.plate_number}-${e.start_time_s}`} className={styles.event}>
                    <span className={styles.index}>{i + 1}</span>
                    {e.crop_image ? (
                      <img className={styles.crop} src={e.crop_image} alt={x.bestFrame(e.plate_number)} />
                    ) : (
                      <span className={styles.crop} aria-hidden />
                    )}
                    <div className={styles.eventBody}>
                      <strong className={styles.plate}>{e.plate_number}</strong>
                      <button type="button" className={styles.time} onClick={() => seek(e.best_time_s)}>
                        {fmtSeconds(e.best_time_s)}
                      </button>
                      <span className={styles.meta}>
                        {x.span(fmtSeconds(e.start_time_s), fmtSeconds(e.end_time_s))} · {x.frames(e.frame_count)}
                      </span>
                    </div>
                    <span className={styles.conf}>
                      <span className={styles.meta}>{x.confidence}</span>
                      {fmtPercent(e.confidence)}
                    </span>
                  </li>
                ))}
              </ol>
            </>
          )}
        </>
      )}
    </section>
  );
}
