import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    if (
      typeof window !== 'undefined' &&
      typeof window.scrollTo === 'function' &&
      typeof navigator !== 'undefined' &&
      !/jsdom/i.test(navigator.userAgent)
    ) {
      window.scrollTo(0, 0);
    }
  }, [pathname]);

  return null;
}

export default ScrollToTop;
