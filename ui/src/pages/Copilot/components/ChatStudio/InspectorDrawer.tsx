import { Activity, BookOpen, Sliders, X } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt, fmtMs } from '@/utils/format';
import type { ChatMessage, PlaygroundParams, RagSource } from './types';
import styles from './ChatStudio.module.css';

export interface InspectorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: 'citations' | 'telemetry' | 'params';
  setActiveTab: (tab: 'citations' | 'telemetry' | 'params') => void;
  activeMessage: ChatMessage | null;
  params: PlaygroundParams;
  setParams: React.Dispatch<React.SetStateAction<PlaygroundParams>>;
  selectedCitation: RagSource | null;
}

export function InspectorDrawer({
  isOpen,
  onClose,
  activeTab,
  setActiveTab,
  activeMessage,
  params,
  setParams,
  selectedCitation,
}: InspectorDrawerProps) {
  const { t } = useI18n();

  return (
    <aside className={`${styles.inspector} ${!isOpen ? styles.inspectorClosed : ''}`} aria-hidden={!isOpen}>
      <div className={styles.inspectorTabs}>
        <button
          type="button"
          className={`${styles.inspectorTab} ${activeTab === 'citations' ? styles.inspectorTabActive : ''}`}
          onClick={() => setActiveTab('citations')}
        >
          <BookOpen size={14} />
          <span>{t.copilot.citationsTitle}</span>
        </button>

        <button
          type="button"
          className={`${styles.inspectorTab} ${activeTab === 'telemetry' ? styles.inspectorTabActive : ''}`}
          onClick={() => setActiveTab('telemetry')}
        >
          <Activity size={14} />
          <span>{t.copilot.telemetryTitle}</span>
        </button>

        <button
          type="button"
          className={`${styles.inspectorTab} ${activeTab === 'params' ? styles.inspectorTabActive : ''}`}
          onClick={() => setActiveTab('params')}
        >
          <Sliders size={14} />
          <span>{t.copilot.paramsTitle}</span>
        </button>

        <button
          type="button"
          className={styles.inspectorCloseBtn}
          onClick={onClose}
          aria-label="Đóng bảng kiểm định"
        >
          <X size={14} />
        </button>
      </div>

      <div className={styles.inspectorContent}>
        {/* 1. Trích dẫn RAG */}
        {activeTab === 'citations' && (
          <div className={styles.citationsTab}>
            {activeMessage?.ragSources && activeMessage.ragSources.length > 0 ? (
              <div className={styles.citationList}>
                {activeMessage.ragSources.map((source, idx) => {
                  const isSelected = selectedCitation?.chunkId === source.chunkId || selectedCitation?.title === source.title;
                  return (
                    <article
                      key={source.chunkId || idx}
                      className={`${styles.citationCard} ${isSelected ? styles.citationCardActive : ''}`}
                    >
                      <header className={styles.citationCardHeader}>
                        <span className={styles.citationCardTitle}>{source.title}</span>
                        {source.score != null && (
                          <span className={`${styles.citationCardScore} num`}>
                            {(source.score * 100).toFixed(0)}%
                          </span>
                        )}
                      </header>

                      {source.chunkId && (
                        <div className={`${styles.chunkIdRow} num`}>
                          Chunk ID: <code>{source.chunkId}</code>
                        </div>
                      )}

                      {source.snippet ? (
                        <blockquote className={styles.citationSnippet}>{source.snippet}</blockquote>
                      ) : (
                        <p className={styles.snippetEmpty}>Nội dung đoạn trích đã nạp vào prompt ngữ cảnh.</p>
                      )}
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className={styles.emptyInspector}>
                <p className={styles.inspectorHint}>{t.copilot.noCitations}</p>
              </div>
            )}
          </div>
        )}

        {/* 2. Chỉ số thực thi (Telemetry) */}
        {activeTab === 'telemetry' && (
          <div className={styles.telemetryTab}>
            {activeMessage ? (
              <div className={styles.telemetryGrid}>
                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>{t.copilot.latency}</span>
                  <span className={`${styles.metricValue} num`}>
                    {activeMessage.latencyMs != null ? fmtMs(activeMessage.latencyMs) : '—'}
                  </span>
                </div>

                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>Tốc độ sinh token</span>
                  <span className={`${styles.metricValue} num`}>
                    {activeMessage.speedTokPerSec != null ? `${activeMessage.speedTokPerSec} t/s` : '—'}
                  </span>
                </div>

                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>Token đầu vào / ra</span>
                  <span className={`${styles.metricValue} num`}>
                    {activeMessage.inputTokens != null && activeMessage.outputTokens != null
                      ? `${fmtInt(activeMessage.inputTokens)} / ${fmtInt(activeMessage.outputTokens)}`
                      : '—'}
                  </span>
                </div>

                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>{t.copilot.contextWindow}</span>
                  <div className={styles.contextBar}>
                    <div
                      className={styles.contextBarFill}
                      style={{
                        width: `${Math.min(
                          100,
                          (((activeMessage.inputTokens || 0) + (activeMessage.outputTokens || 0)) / 4096) * 100,
                        )}%`,
                      }}
                    />
                  </div>
                  <span className={`${styles.contextSubText} num`}>
                    {fmtInt((activeMessage.inputTokens || 0) + (activeMessage.outputTokens || 0))} / 4,096 tokens
                  </span>
                </div>

                {activeMessage.promptVersion && (
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Prompt Revision</span>
                    <span className={`${styles.promptVersionText} num`}>{activeMessage.promptVersion}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className={styles.emptyInspector}>
                <p className={styles.inspectorHint}>Gửi câu hỏi để xem chỉ số viễn trắc chi tiết.</p>
              </div>
            )}
          </div>
        )}

        {/* 3. Tham số thử nghiệm (Playground Parameters) */}
        {activeTab === 'params' && (
          <div className={styles.paramsTab}>
            <div className={styles.sliderRow}>
              <div className={styles.sliderLabelRow}>
                <label htmlFor="param-temperature">{t.copilot.temperature}</label>
                <span className={`${styles.sliderValue} num`}>{params.temperature.toFixed(2)}</span>
              </div>
              <input
                id="param-temperature"
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={params.temperature}
                onChange={(e) => setParams((p) => ({ ...p, temperature: parseFloat(e.target.value) }))}
              />
            </div>

            <div className={styles.sliderRow}>
              <div className={styles.sliderLabelRow}>
                <label htmlFor="param-similarity">{t.copilot.minSimilarity}</label>
                <span className={`${styles.sliderValue} num`}>{params.minSimilarity.toFixed(2)}</span>
              </div>
              <input
                id="param-similarity"
                type="range"
                min="0.40"
                max="0.95"
                step="0.01"
                value={params.minSimilarity}
                onChange={(e) => setParams((p) => ({ ...p, minSimilarity: parseFloat(e.target.value) }))}
              />
            </div>

            <div className={styles.sliderRow}>
              <div className={styles.sliderLabelRow}>
                <label htmlFor="param-topk">{t.copilot.topK}</label>
                <span className={`${styles.sliderValue} num`}>{params.topK}</span>
              </div>
              <input
                id="param-topk"
                type="range"
                min="1"
                max="10"
                step="1"
                value={params.topK}
                onChange={(e) => setParams((p) => ({ ...p, topK: parseInt(e.target.value, 10) }))}
              />
            </div>

            <div className={styles.sliderRow}>
              <label htmlFor="param-lot">{t.copilot.lotScope}</label>
              <select
                id="param-lot"
                className={styles.selectInput}
                value={params.parkingLotId}
                onChange={(e) => setParams((p) => ({ ...p, parkingLotId: e.target.value }))}
              >
                <option value="">{t.copilot.allLots}</option>
                <option value="lot_central_01">Bãi đỗ Trung tâm (Central Lot 01)</option>
                <option value="lot_west_gate">Bãi đỗ Cổng Tây (West Gate)</option>
                <option value="lot_airport_longterm">Bãi đỗ Dài hạn Sân bay</option>
              </select>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
