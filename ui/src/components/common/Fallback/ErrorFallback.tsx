import { ErrorBlock } from '../Ui/feedback/LoadState';

export interface ErrorFallbackProps {
  error: unknown;
  resetErrorBoundary?: () => void;
}

export function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  return <ErrorBlock error={error} onRetry={resetErrorBoundary} />;
}

export default ErrorFallback;
