import { createContext, useContext, useState, type ReactNode } from 'react';
import { applyLang, currentLang, type Lang } from '@/utils/lang';
import { en } from './en';
import { vi, type Messages } from './vi';

const DICTS: Record<Lang, Messages> = { vi, en };

/** Từ điển của ngôn ngữ đang dùng, cho code ngoài React (client.ts). */
export const messages = (): Messages => DICTS[currentLang()];

interface I18n {
  lang: Lang;
  t: Messages;
  setLang: (lang: Lang) => void;
}

const I18nContext = createContext<I18n>({ lang: 'vi', t: vi, setLang: applyLang });

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setState] = useState<Lang>(currentLang);
  const setLang = (next: Lang) => {
    applyLang(next);
    setState(next);
  };
  return <I18nContext.Provider value={{ lang, t: DICTS[lang], setLang }}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);
