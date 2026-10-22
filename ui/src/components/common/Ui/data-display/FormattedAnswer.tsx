import type { ReactNode } from 'react';
import styles from './FormattedAnswer.module.css';

interface FormattedAnswerProps {
  content: string;
  isStreaming?: boolean;
}

const INLINE_REGEX = /(\*\*.*?\*\*|`.*?`|\[(?:Nguồn|Source):?\s*[^\]]+\]|\[[^\]]+\.(?:pdf|docx|txt|md|json)\])/g;

function renderInlineTokens(text: string): ReactNode[] {
  if (!text) return [];

  const pieces = text.split(INLINE_REGEX);
  return pieces.map((piece, idx) => {
    if (!piece) return null;

    // 1. Bold text: **example**
    if (piece.startsWith('**') && piece.endsWith('**') && piece.length >= 4) {
      return (
        <strong key={idx} className={styles.strong}>
          {piece.slice(2, -2)}
        </strong>
      );
    }

    // 2. Inline code: `example`
    if (piece.startsWith('`') && piece.endsWith('`') && piece.length >= 2) {
      return (
        <code key={idx} className={styles.inlineCode}>
          {piece.slice(1, -1)}
        </code>
      );
    }

    // 3. Citations: [Nguồn: file.pdf] or [file.docx]
    if (
      (piece.startsWith('[Nguồn:') ||
        piece.startsWith('[Source:') ||
        /\[[^\]]+\.(?:pdf|docx|txt|md|json)\]/.test(piece)) &&
      piece.endsWith(']')
    ) {
      const rawCitation = piece.slice(1, -1);
      const cleanName = rawCitation.replace(/^(?:Nguồn|Source):\s*/, '').trim();
      return (
        <span
          key={idx}
          className={styles.citation}
          title={`Trích dẫn từ tài liệu: ${cleanName}`}
        >
          📄 {cleanName}
        </span>
      );
    }

    // 4. Regular text
    return piece;
  });
}

export function FormattedAnswer({ content, isStreaming = false }: FormattedAnswerProps) {
  if (!content) return null;

  const lines = content.split('\n');
  const blocks: ReactNode[] = [];
  let currentListItems: ReactNode[] = [];
  let isNumberedList = false;

  const flushList = (key: string) => {
    if (currentListItems.length > 0) {
      if (isNumberedList) {
        blocks.push(
          <ol key={key} className={styles.list} style={{ listStyleType: 'decimal' }}>
            {currentListItems}
          </ol>
        );
      } else {
        blocks.push(
          <ul key={key} className={styles.list}>
            {currentListItems}
          </ul>
        );
      }
      currentListItems = [];
      isNumberedList = false;
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList(`list-before-blank-${idx}`);
      return;
    }

    const bulletMatch = /^[*-]\s+(.+)/.exec(trimmed);
    const numberedMatch = /^\d+\.\s+(.+)/.exec(trimmed);

    if (bulletMatch) {
      if (isNumberedList && currentListItems.length > 0) {
        flushList(`list-switch-${idx}`);
      }
      isNumberedList = false;
      const isLast = isStreaming && idx === lines.length - 1;
      currentListItems.push(
        <li key={`li-${idx}`} className={styles.listItem}>
          {renderInlineTokens(bulletMatch[1])}
          {isLast && <span className={styles.cursor}> ▋</span>}
        </li>
      );
    } else if (numberedMatch) {
      if (!isNumberedList && currentListItems.length > 0) {
        flushList(`list-switch-${idx}`);
      }
      isNumberedList = true;
      const isLast = isStreaming && idx === lines.length - 1;
      currentListItems.push(
        <li key={`li-${idx}`} className={styles.listItem}>
          {renderInlineTokens(numberedMatch[1])}
          {isLast && <span className={styles.cursor}> ▋</span>}
        </li>
      );
    } else {
      flushList(`list-before-p-${idx}`);
      const isLast = isStreaming && idx === lines.length - 1;
      blocks.push(
        <p key={`p-${idx}`} className={styles.paragraph}>
          {renderInlineTokens(trimmed)}
          {isLast && <span className={styles.cursor}> ▋</span>}
        </p>
      );
    }
  });

  flushList(`list-final`);

  return <div className={styles.container}>{blocks}</div>;
}

export default FormattedAnswer;
