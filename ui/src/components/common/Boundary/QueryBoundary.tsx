import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { Suspense, type ReactNode } from 'react';
import { LoadingFallback } from '../Fallback/LoadingFallback';
import { InternalErrorBoundary } from './InternalErrorBoundary';

export interface QueryBoundaryProps {
  children: ReactNode;
  pending?: ReactNode;
  onReset?: () => void;
}

export function QueryBoundary({ children, pending, onReset }: QueryBoundaryProps) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <InternalErrorBoundary
          onReset={() => {
            reset();
            onReset?.();
          }}
        >
          <Suspense fallback={pending ?? <LoadingFallback />}>
            {children}
          </Suspense>
        </InternalErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}

export default QueryBoundary;
