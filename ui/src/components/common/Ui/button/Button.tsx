// Chép từ frontend@b4eaa5c packages/shared/src/components/Ui/button/Button.tsx (ADR-0048 §5):
// bỏ clsx và bóng màu/nhấc nút để đúng luật Hallmark "không glow" của console.
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Spinner } from '../feedback/Spinner';
import styles from './Button.module.css';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'accent' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md';
  loading?: boolean;
  children: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, disabled, children, className, type = 'button', ...rest }, ref) => (
    <button
      ref={ref}
      type={type}
      className={[styles.btn, styles[variant], styles[size], className].filter(Boolean).join(' ')}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <Spinner size={14} />}
      {children}
    </button>
  ),
);
Button.displayName = 'Button';
