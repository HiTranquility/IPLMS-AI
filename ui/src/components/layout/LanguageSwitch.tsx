import { Segmented } from '@/components/common/Ui/button/Segmented';
import { useI18n } from '@/i18n/I18nProvider';
import type { Lang } from '@/utils/lang';

const OPTIONS: { value: Lang; label: string }[] = [
  { value: 'vi', label: 'VI' },
  { value: 'en', label: 'EN' },
];

/** Nhãn nhóm viết cả hai thứ tiếng: người không đọc được ngôn ngữ đang hiện vẫn tìm ra nút đổi. */
export function LanguageSwitch() {
  const { lang, setLang } = useI18n();
  return <Segmented label="Ngôn ngữ · Language" value={lang} options={OPTIONS} onChange={setLang} />;
}
