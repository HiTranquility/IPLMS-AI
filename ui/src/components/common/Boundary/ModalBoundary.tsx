import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { Suspense, type ReactNode } from 'react';
import { LoadingFallback } from '../Fallback/LoadingFallback';
import { InternalErrorBoundary } from './InternalErrorBoundary';

export interface ModalBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function ModalBoundary({ children, fallback }: ModalBoundaryProps) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <InternalErrorBoundary onReset={reset}>
          <Suspense fallback={fallback ?? <LoadingFallback />}>
            {children}
          </Suspense>
        </InternalErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}

export default ModalBoundary;
