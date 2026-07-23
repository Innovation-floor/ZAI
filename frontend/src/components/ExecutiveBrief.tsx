import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { t, fmt } from '@/lib/i18n';
import type { BriefResponse, Language } from '@/types/api';

interface Props {
  lang: Language;
}

export function ExecutiveBrief({ lang }: Props) {
  const [brief, setBrief] = useState<BriefResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.brief().then(setBrief).catch((e) => setError(e.message));
  }, [lang]);

  if (error) return <div className="card"><p className="recommendation">{`Brief unavailable: ${error}`}</p></div>;
  if (!brief) return null;

  const top = brief.attention_list[0];
  const recText = top
    ? `Consider reviewing ${top.name} in ${top.country} — ${top.completion}% complete, ${top.risk.toLowerCase()} risk.`
    : 'No projects currently require executive attention.';

  return (
    <div className="card">
      <h2>{t('briefTitle', lang)}</h2>
      <ul className="brief">
        <li><span>{t('activeProjects', lang)}</span><b>{fmt(brief.active_projects, lang)}</b></li>
        <li><span>{t('attention', lang)}</span><b>{fmt(brief.projects_requiring_attention, lang)}</b></li>
        <li><span>{t('newUpdated', lang)}</span><b>{fmt(brief.new_or_updated, lang)}</b></li>
        <li><span>{t('recentCountries', lang)}</span><b>{brief.countries_with_recent_activity.slice(0, 3).join(', ')}</b></li>
      </ul>
      <p className="recommendation">{recText}</p>
    </div>
  );
}
