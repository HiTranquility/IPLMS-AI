import { Suspense, type ReactNode } from 'react';
import { InternalErrorBoundary } from './InternalErrorBoundary';

export interface WidgetBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function WidgetBoundary({ children, fallback = null }: WidgetBoundaryProps) {
  return (
    <InternalErrorBoundary fallbackRender={() => null}>
      <Suspense fallback={fallback}>{children}</Suspense>
    </InternalErrorBoundary>
  );
}

export default WidgetBoundary;
