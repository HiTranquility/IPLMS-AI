import { PARKING_LOTS, resolveLotLabel } from '@/constants/parkingLots';
import { useState } from 'react';
import { Activity, BookOpen, Check, Copy, Cpu, Database, ExternalLink, GitBranch, MessageSquare, Sliders, Sparkles, X } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt, fmtMs } from '@/utils/format';
import { DisputeSimulator } from './DisputeSimulator';
import { KnowledgeExplorer } from './KnowledgeExplorer';
import {
  type ChatMessage,
  type InspectorTab,
  MODEL_PROFILES,
  type ModelProfilePreset,
  type PlaygroundParams,
  type RagSource,
  type SeedDocument,
} from './types';
import styles from './ChatStudio.module.css';

export interface InspectorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: InspectorTab;
  setActiveTab: (tab: InspectorTab) => void;
  activeMessage: ChatMessage | null;
  params: PlaygroundParams;
  setParams: React.Dispatch<React.SetStateAction<PlaygroundParams>>;
  selectedCitation: RagSource | null;
  onAskAboutDocument?: (doc: SeedDocument) => void;
  onAskAboutDispute?: (summary: string) => void;
  onSelectModelProfile?: (profile: ModelProfilePreset) => void;
  onViewFullDocument?: (docOrId: string) => void;
  onAskAboutCitation?: (source: RagSource) => void;
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
  onAskAboutDocument,
  onAskAboutDispute,
  onSelectModelProfile,
  onViewFullDocument,
  onAskAboutCitation,
}: InspectorDrawerProps) {
  const { t } = useI18n();
  const [copiedCitationId, setCopiedCitationId] = useState<string | null>(null);

  const handleCopySnippet = async (source: RagSource) => {
    const text = source.snippet || source.title;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedCitationId(source.chunkId || source.title);
      setTimeout(() => setCopiedCitationId(null), 2000);
    } catch {
      // Fallback
    }
  };

  const handleApplyProfile = (profile: ModelProfilePreset) => {
    setParams((prev) => ({
      ...prev,
      temperature: profile.params.temperature,
      topK: profile.params.topK,
      maxTokens: profile.params.maxTokens,
      minSimilarity: profile.params.minSimilarity,
      modelProfileId: profile.id,
    }));
    onSelectModelProfile?.(profile);
  };

  return (
    <aside
      className={`${styles.inspector} ${!isOpen ? styles.inspectorClosed : ''}`}
      aria-hidden={!isOpen}
    >
      {/* Tab Navigation (5 Tabs) */}
      <div className={styles.inspectorTabs}>
        <div className={styles.inspectorTabsScroll}>
          <button
            type="button"
            className={`${styles.inspectorTab} ${activeTab === 'citations' ? styles.inspectorTabActive : ''}`}
            onClick={() => setActiveTab('citations')}
            title={t.copilot.tabCitationsTitle}
          >
            <BookOpen size={13} aria-hidden />
            <span>{t.copilot.citationsTitle}</span>
          </button>

          <button
            type="button"
            className={`${styles.inspectorTab} ${activeTab === 'knowledge' ? styles.inspectorTabActive : ''}`}
            onClick={() => setActiveTab('knowledge')}
            title={t.copilot.tabKnowledgeTitle}
          >
            <Database size={13} aria-hidden />
            <span>{t.copilot.knowledgeTitle}</span>
          </button>

          <button
            type="button"
            className={`${styles.inspectorTab} ${activeTab === 'dispute' ? styles.inspectorTabActive : ''}`}
            onClick={() => setActiveTab('dispute')}
            title={t.copilot.tabDisputeTitle}
          >
            <GitBranch size={13} aria-hidden />
            <span>{t.copilot.disputeTitle}</span>
          </button>

          <button
            type="button"
            className={`${styles.inspectorTab} ${activeTab === 'telemetry' ? styles.inspectorTabActive : ''}`}
            onClick={() => setActiveTab('telemetry')}
            title={t.copilot.tabTelemetryTitle}
          >
            <Activity size={13} aria-hidden />
            <span>{t.copilot.telemetryTitle}</span>
          </button>

          <button
            type="button"
            className={`${styles.inspectorTab} ${activeTab === 'params' ? styles.inspectorTabActive : ''}`}
            onClick={() => setActiveTab('params')}
            title={t.copilot.tabParamsTitle}
          >
            <Sliders size={13} aria-hidden />
            <span>{t.copilot.paramsTitle}</span>
          </button>
        </div>

        <button
          type="button"
          className={styles.inspectorCloseBtn}
          onClick={onClose}
          aria-label={t.copilot.closeInspector}
          title={t.copilot.closeInspector}
        >
          <X size={14} />
        </button>
      </div>

      <div className={styles.inspectorContent}>
        {/* 1. Tab Trích Dẫn RAG */}
        {activeTab === 'citations' && (
          <div className={styles.citationsTab}>
            {activeMessage?.ragSources && activeMessage.ragSources.length > 0 ? (
              <div className={styles.citationList}>
                {activeMessage.ragSources.map((source, idx) => {
                  const isSelected =
                    selectedCitation?.chunkId === source.chunkId ||
                    selectedCitation?.title === source.title;
                  const scorePercent = source.score != null ? Math.round(source.score * 100) : null;
                  return (
                    <article
                      key={source.chunkId || idx}
                      className={`${styles.citationCard} ${isSelected ? styles.citationCardActive : ''}`}
                    >
                      <header className={styles.citationCardHeader}>
                        <div className={styles.citationCardTitleGroup}>
                          <BookOpen size={13} className={styles.citationBookIcon} />
                          <span className={styles.citationCardTitle}>{source.title}</span>
                        </div>
                        {scorePercent != null && (
                          <span
                            className={`${styles.citationCardScore} num`}
                            title={`${t.copilot.citationScoreLabel}: ${scorePercent}%`}
                          >
                            {scorePercent}%
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
                        <p className={styles.snippetEmpty}>{t.copilot.snippetInPrompt}</p>
                      )}

                      <footer className={styles.citationCardFooter}>
                        {onViewFullDocument && (
                          <button
                            type="button"
                            className={styles.citationActionBtn}
                            onClick={() => onViewFullDocument(source.documentId || source.title)}
                            title={t.copilot.viewFullDocTooltip}
                            aria-label={t.copilot.viewFull}
                          >
                            <ExternalLink size={12} />
                            <span>{t.copilot.viewFull}</span>
                          </button>
                        )}

                        <button
                          type="button"
                          className={styles.citationActionBtn}
                          onClick={() => handleCopySnippet(source)}
                          title={t.copilot.copySnippet}
                          aria-label={t.copilot.copySnippet}
                        >
                          {copiedCitationId === (source.chunkId || source.title) ? (
                            <>
                              <Check size={12} className={styles.successColor} />
                              <span>{t.copilot.copiedSnippet}</span>
                            </>
                          ) : (
                            <>
                              <Copy size={12} />
                              <span>{t.copilot.copySnippet}</span>
                            </>
                          )}
                        </button>

                        {onAskAboutCitation && (
                          <button
                            type="button"
                            className={`${styles.citationActionBtn} ${styles.citationAskBtn}`}
                            onClick={() => onAskAboutCitation(source)}
                            title={t.copilot.askAboutCitation}
                            aria-label={t.copilot.askAboutCitation}
                          >
                            <MessageSquare size={12} />
                            <span>{t.copilot.askAboutCitation}</span>
                          </button>
                        )}
                      </footer>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className={styles.emptyInspector}>
                <BookOpen size={24} className={styles.emptyIcon} />
                <p className={styles.inspectorHint}>{t.copilot.noCitations}</p>
              </div>
            )}
          </div>
        )}

        {/* 2. Tab Kho Tri Thức & Dictionary Explorer */}
        {activeTab === 'knowledge' && (
          <KnowledgeExplorer
            onAskAboutDocument={onAskAboutDocument}
            onViewFullDocument={onViewFullDocument ? (doc) => onViewFullDocument(doc.id || doc.title) : undefined}
            onOpenKnowledgePage={onViewFullDocument ? () => onViewFullDocument('') : undefined}
          />
        )}

        {/* 3. Tab Mô Phỏng Phân Xử LangGraph */}
        {activeTab === 'dispute' && (
          <DisputeSimulator onAskAboutDispute={onAskAboutDispute} />
        )}

        {/* 4. Tab Chỉ Số Thực Thi (Telemetry) */}
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
                  <span className={styles.metricLabel}>{t.copilot.tokenSpeed}</span>
                  <span className={`${styles.metricValue} num`}>
                    {activeMessage.speedTokPerSec != null ? `${activeMessage.speedTokPerSec} tok/s` : '—'}
                  </span>
                </div>

                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>{t.copilot.tokensInOut}</span>
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
                          (((activeMessage.inputTokens || 0) + (activeMessage.outputTokens || 0)) /
                            (activeMessage.contextLimit || 4096)) *
                            100,
                        )}%`,
                      }}
                    />
                  </div>
                  <span className={`${styles.contextSubText} num`}>
                    {`${fmtInt((activeMessage.inputTokens || 0) + (activeMessage.outputTokens || 0))} / ${fmtInt(activeMessage.contextLimit || 4096)} tokens`}
                  </span>
                </div>

                {activeMessage.promptVersion && (
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Prompt Revision</span>
                    <span className={`${styles.promptVersionText} num`}>
                      {activeMessage.promptVersion}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className={styles.emptyInspector}>
                <Activity size={24} className={styles.emptyIcon} />
                <p className={styles.inspectorHint}>{t.copilot.telemetryHint}</p>
              </div>
            )}
          </div>
        )}

        {/* 5. Tab Tham Số Thử Nghiệm & Model Profiles */}
        {activeTab === 'params' && (
          <div className={styles.paramsTab}>
            {/* Model Profile Presets Section */}
            <div className={styles.profileSection}>
              <div className={styles.profileSectionHeader}>
                <span className={styles.profileSectionTitle}>
                  <Sparkles size={13} className={styles.accentColor} />{' '}
                  {t.copilot.modelProfilesTitle}
                </span>
                <span className={styles.profileSectionHint}>1-click apply</span>
              </div>

              <div className={styles.profileCardsGrid}>
                {MODEL_PROFILES.map((pf) => {
                  const isCurrent =
                    params.modelProfileId === pf.id ||
                    (params.temperature === pf.params.temperature && params.topK === pf.params.topK);

                  return (
                    <button
                      key={pf.id}
                      type="button"
                      className={`${styles.profileCard} ${isCurrent ? styles.profileCardActive : ''}`}
                      onClick={() => handleApplyProfile(pf)}
                    >
                      <div className={styles.profileCardTop}>
                        <div className={styles.profileTitleRow}>
                          <Cpu size={13} />
                          <span className={styles.profileName}>{pf.name}</span>
                          <code className={styles.profileModelTag}>{pf.model}</code>
                        </div>
                        {isCurrent && <Check size={13} className={styles.successColor} />}
                      </div>

                      <p className={styles.profileDesc}>{pf.description}</p>

                      <div className={styles.profileMetaRow}>
                        <span className={`${styles.profileParamPill} num`}>
                          Temp: {pf.params.temperature}
                        </span>
                        <span className={`${styles.profileParamPill} num`}>
                          Top-K: {pf.params.topK}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Sliders */}
            <div className={styles.slidersDivider} />

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
                onChange={(e) =>
                  setParams((p) => ({ ...p, temperature: parseFloat(e.target.value), modelProfileId: undefined }))
                }
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
                min="0.20"
                max="0.95"
                step="0.01"
                value={params.minSimilarity}
                onChange={(e) =>
                  setParams((p) => ({ ...p, minSimilarity: parseFloat(e.target.value) }))
                }
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
                onChange={(e) =>
                  setParams((p) => ({ ...p, topK: parseInt(e.target.value, 10), modelProfileId: undefined }))
                }
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
                {PARKING_LOTS.map((lot) => (
                  <option key={lot.id} value={lot.id}>
                    {resolveLotLabel(lot, t)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

export default InspectorDrawer;
