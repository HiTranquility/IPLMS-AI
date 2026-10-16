import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import styles from './Field.module.css';

interface FieldShellProps {
  label: string;
  hint?: string;
  children: (id: string, hintId?: string) => ReactNode;
}

function FieldShell({ label, hint, children }: FieldShellProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      {children(id, hintId)}
      {hint && <p id={hintId} className={styles.hint}>{hint}</p>}
    </div>
  );
}

type Labeled = { label: string; hint?: string };

export function TextField({ label, hint, ...rest }: Labeled & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <FieldShell label={label} hint={hint}>
      {(id, hintId) => <input id={id} aria-describedby={hintId} className={styles.control} {...rest} />}
    </FieldShell>
  );
}

export function TextArea({ label, hint, ...rest }: Labeled & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <FieldShell label={label} hint={hint}>
      {(id, hintId) => <textarea id={id} aria-describedby={hintId} className={`${styles.control} ${styles.area}`} {...rest} />}
    </FieldShell>
  );
}

export function SelectField({ label, hint, children, ...rest }: Labeled & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <FieldShell label={label} hint={hint}>
      {(id, hintId) => (
        <select id={id} aria-describedby={hintId} className={styles.control} {...rest}>
          {children}
        </select>
      )}
    </FieldShell>
  );
}
