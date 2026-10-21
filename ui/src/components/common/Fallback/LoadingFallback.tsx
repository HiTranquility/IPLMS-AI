import { Loading } from '../Ui/feedback/LoadState';

export interface LoadingFallbackProps {
  label?: string;
}

export function LoadingFallback({ label }: LoadingFallbackProps) {
  return <Loading label={label} />;
}

export default LoadingFallback;
