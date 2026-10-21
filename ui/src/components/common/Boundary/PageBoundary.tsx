import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { Suspense, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { LoadingFallback } from '../Fallback/LoadingFallback';
import { InternalErrorBoundary } from './InternalErrorBoundary';

export interface PageBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function PageBoundary({ children, fallback }: PageBoundaryProps) {
  const location = useLocation();

  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <InternalErrorBoundary onReset={reset} resetKeys={[location.pathname]}>
          <Suspense fallback={fallback ?? <LoadingFallback />}>
            {children}
          </Suspense>
        </InternalErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}

export default PageBoundary;
