import type { Summary, Language } from '@/types/api';
import { t, fmt } from '@/lib/i18n';

interface Props {
  summary: Summary;
  lang: Language;
}

export function KpiBar({ summary, lang }: Props) {
  const items = [
    { value: fmt(summary.projects, lang), label: t('projects', lang) },
    { value: fmt(summary.active, lang), label: t('active', lang) },
    { value: fmt(summary.countries, lang), label: t('countries', lang) },
    { value: fmt(summary.partners, lang), label: t('partners', lang) },
    { value: fmt(summary.beneficiaries, lang), label: t('beneficiaries', lang) },
    { value: `AED ${fmt(summary.investment_aed_m, lang)}M`, label: t('investment', lang) },
  ];

  return (
    <div className="kpis">
      {items.map((item, i) => (
        <div key={i} className="kpi">
          <div className="v">{item.value}</div>
          <div className="l">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
