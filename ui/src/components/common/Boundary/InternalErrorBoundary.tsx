import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ErrorFallback } from '../Fallback/ErrorFallback';

interface InternalErrorBoundaryProps {
  children: ReactNode;
  resetKeys?: unknown[];
  onReset?: () => void;
  fallbackRender?: (props: { error: unknown; resetErrorBoundary: () => void }) => ReactNode;
}

interface InternalErrorBoundaryState {
  hasError: boolean;
  error: unknown;
}

function keysChanged(a?: unknown[], b?: unknown[]) {
  if (!a || !b) return false;
  if (a.length !== b.length) return true;
  return a.some((item, idx) => !Object.is(item, b[idx]));
}

export class InternalErrorBoundary extends Component<InternalErrorBoundaryProps, InternalErrorBoundaryState> {
  override state: InternalErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: unknown): InternalErrorBoundaryState {
    return { hasError: true, error };
  }

  override componentDidUpdate(prevProps: InternalErrorBoundaryProps) {
    if (this.state.hasError && keysChanged(prevProps.resetKeys, this.props.resetKeys)) {
      this.resetErrorBoundary();
    }
  }

  override componentDidCatch(_error: Error, _info: ErrorInfo) {
    // Error handled via Fallback UI
  }

  resetErrorBoundary = () => {
    this.props.onReset?.();
    this.setState({ hasError: false, error: null });
  };

  override render() {
    if (this.state.hasError) {
      if (this.props.fallbackRender) {
        return this.props.fallbackRender({
          error: this.state.error,
          resetErrorBoundary: this.resetErrorBoundary,
        });
      }
      return <ErrorFallback error={this.state.error} resetErrorBoundary={this.resetErrorBoundary} />;
    }
    return this.props.children;
  }
}
